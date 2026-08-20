"""Authenticated HTTP session for clippercard.com."""

# === imports ===

import json
import logging
import subprocess
import sys
from http.cookiejar import Cookie, LoadError, MozillaCookieJar
from pathlib import Path

import bs4
import httpx

import clippercard.parser as parser

logger = logging.getLogger(__name__)

# === Error Classes ===


class ClipperCardError(Exception):
    """base error for client"""


class ClipperCardAuthError(ClipperCardError):
    """unable to login with provided credentials"""


def _run_keychain(*args: str) -> subprocess.CompletedProcess[str]:
    if sys.platform != "darwin":
        raise ClipperCardError("macOS Keychain storage is only supported on macOS")
    return subprocess.run(
        ["security", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


# === ClipperCardWebSession ===


class ClipperCardWebSession(httpx.Client):
    """
    A stateful session for clippercard.com
    """

    LOGIN_URL = "https://www.clippercard.com/web-login"
    DASHBOARD_URL = "https://www.clippercard.com/dashboard"
    PROFILE_URL = "https://www.clippercard.com/profile"
    COOKIE_JAR_PATH = Path("~/.config/clippercard/auth.cookies").expanduser()
    COOKIE_STORE_SERVICE = "clippercard.cookies"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        cookie_jar_path: str | Path | None = None,
        cookie_store: str = "file",
        keychain_account: str | None = None,
    ) -> None:
        # Follow redirects and bound every request: callers expect final-page
        # responses, and hanging forever is worse than a generous timeout.
        super().__init__(follow_redirects=True, timeout=30.0)
        self.headers.update(self.HEADERS)
        self._cookie_jar_path = Path(cookie_jar_path).expanduser() if cookie_jar_path else self.COOKIE_JAR_PATH
        self._cookie_store = cookie_store
        self._keychain_account = keychain_account or "default"
        # httpx wraps a stdlib CookieJar in httpx.Cookies without copying it,
        # so load()/save()/set_cookie() go through our MozillaCookieJar handle.
        self._cookie_jar = MozillaCookieJar(str(self._cookie_jar_path))
        self.cookies = self._cookie_jar
        self._dashboard_resp_text = None
        self._cards = None
        self._profile_info = None
        self._profile_loaded = False
        self._reused_cookies = False
        try:
            if username and password:
                self.login(username, password)
        except BaseException:
            self.close()
            raise

    @property
    def reused_cookies(self) -> bool:
        return self._reused_cookies

    @property
    def cookie_jar_path(self) -> Path:
        return self._cookie_jar_path

    @property
    def cookie_storage_label(self) -> str:
        if self._cookie_store == "keychain":
            return f"macOS Keychain item {self.COOKIE_STORE_SERVICE}:{self._keychain_account}"
        return str(self._cookie_jar_path)

    @staticmethod
    def _cookie_to_dict(cookie):
        return {
            "version": cookie.version,
            "name": cookie.name,
            "value": cookie.value,
            "port": cookie.port,
            "port_specified": cookie.port_specified,
            "domain": cookie.domain,
            "domain_specified": cookie.domain_specified,
            "domain_initial_dot": cookie.domain_initial_dot,
            "path": cookie.path,
            "path_specified": cookie.path_specified,
            "secure": cookie.secure,
            "expires": cookie.expires,
            "discard": cookie.discard,
            "comment": cookie.comment,
            "comment_url": cookie.comment_url,
            "rest": cookie._rest,
            "rfc2109": cookie.rfc2109,
        }

    @staticmethod
    def _cookie_from_dict(data):
        return Cookie(
            version=data["version"],
            name=data["name"],
            value=data["value"],
            port=data["port"],
            port_specified=data["port_specified"],
            domain=data["domain"],
            domain_specified=data["domain_specified"],
            domain_initial_dot=data["domain_initial_dot"],
            path=data["path"],
            path_specified=data["path_specified"],
            secure=data["secure"],
            expires=data["expires"],
            discard=data["discard"],
            comment=data["comment"],
            comment_url=data["comment_url"],
            rest=data.get("rest") or {},
            rfc2109=data["rfc2109"],
        )

    def _serialize_cookies(self):
        return json.dumps({"cookies": [self._cookie_to_dict(cookie) for cookie in self._cookie_jar]})

    def _load_serialized_cookies(self, cookie_data):
        self._cookie_jar.clear()
        for cookie in json.loads(cookie_data).get("cookies", []):
            self._cookie_jar.set_cookie(self._cookie_from_dict(cookie))

    def _load_keychain_cookies(self):
        result = _run_keychain(
            "find-generic-password",
            "-s",
            self.COOKIE_STORE_SERVICE,
            "-a",
            self._keychain_account,
            "-w",
        )
        if result.returncode != 0:
            logger.debug("No saved cookies found in macOS Keychain for %s", self._keychain_account)
            return False
        try:
            self._load_serialized_cookies(result.stdout)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Keychain cookies for %s are unreadable; ignoring them", self._keychain_account)
            return False
        loaded_cookies = list(self._cookie_jar)
        logger.debug("Loaded %d cookies from macOS Keychain", len(loaded_cookies))
        return bool(loaded_cookies)

    def _save_keychain_cookies(self):
        result = _run_keychain(
            "add-generic-password",
            "-U",
            "-s",
            self.COOKIE_STORE_SERVICE,
            "-a",
            self._keychain_account,
            "-w",
            self._serialize_cookies(),
        )
        if result.returncode != 0:
            raise ClipperCardError(f"Unable to save cookies to macOS Keychain: {result.stderr.strip()}")
        logger.debug("Saved cookies to macOS Keychain for %s", self._keychain_account)

    def _clear_keychain_cookies(self):
        self._cookie_jar.clear()
        result = _run_keychain(
            "delete-generic-password",
            "-s",
            self.COOKIE_STORE_SERVICE,
            "-a",
            self._keychain_account,
        )
        if result.returncode == 0:
            logger.debug("Removed stale cookies from macOS Keychain for %s", self._keychain_account)

    def _load_file_cookie_jar(self):
        if not self._cookie_jar_path.exists():
            return False
        try:
            self._cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except LoadError:
            logger.warning("Cookie jar at %s is unreadable; ignoring it", self._cookie_jar_path)
            return False
        loaded_cookies = list(self._cookie_jar)
        logger.debug("Loaded %d cookies from %s", len(loaded_cookies), self._cookie_jar_path)
        return bool(loaded_cookies)

    def _migrate_file_cookies_to_keychain(self):
        if not self._load_file_cookie_jar():
            return False
        self._save_keychain_cookies()
        logger.debug("Migrated file cookies from %s to macOS Keychain", self._cookie_jar_path)
        return True

    def _load_cookie_jar(self):
        if self._cookie_store == "keychain":
            return self._load_keychain_cookies() or self._migrate_file_cookies_to_keychain()

        return self._load_file_cookie_jar()

    def _save_cookie_jar(self):
        if self._cookie_store == "keychain":
            self._save_keychain_cookies()
            return

        self._cookie_jar_path.parent.mkdir(parents=True, exist_ok=True)
        self._cookie_jar.save(ignore_discard=True, ignore_expires=True)
        self._cookie_jar_path.chmod(0o600)
        logger.debug("Saved cookies to %s", self._cookie_jar_path)

    def _clear_cookie_jar(self):
        if self._cookie_store == "keychain":
            self._clear_keychain_cookies()
            return

        self._cookie_jar.clear()
        if self._cookie_jar_path.exists():
            self._cookie_jar_path.unlink()
            logger.debug("Removed stale cookie jar at %s", self._cookie_jar_path)

    @staticmethod
    def _response_has_dashboard_data(response_text):
        return "patronDetails" in response_text

    def _fetch_dashboard_with_cookies(self):
        if not self._load_cookie_jar():
            return None

        logger.debug("Trying saved cookies from %s", self._cookie_jar_path)
        dashboard_resp = self.get(self.DASHBOARD_URL)
        logger.debug("Dashboard-with-cookies response: %s", dashboard_resp.status_code)
        logger.debug("Final URL after cookie reuse: %s", dashboard_resp.url)

        if not dashboard_resp.is_error and self._response_has_dashboard_data(dashboard_resp.text):
            self._dashboard_resp_text = dashboard_resp.text
            self._cards = None
            self._reused_cookies = True
            self._save_cookie_jar()
            logger.debug("Saved cookies are still valid")
            return dashboard_resp

        logger.debug("Saved cookies did not yield a valid dashboard; falling back to login")
        self._dashboard_resp_text = None
        self._cards = None
        self._reused_cookies = False
        self._clear_cookie_jar()
        return None

    def login(self, username: str, password: str) -> httpx.Response:
        """
        Authenticate user and fetch dashboard page.
        1. Try saved cookies against /dashboard
        2. GET /web-login to get CSRF token
        3. POST to /dashboard with credentials + CSRF
        """
        logger.debug("Logging in as %s", username)

        reused_resp = self._fetch_dashboard_with_cookies()
        if reused_resp is not None:
            return reused_resp

        # Get login page to extract CSRF token
        logger.debug("Fetching login page: %s", self.LOGIN_URL)
        login_landing_resp = self.get(self.LOGIN_URL)
        if login_landing_resp.is_error:
            logger.error("Failed to get login page: %s", login_landing_resp.status_code)
            raise ClipperCardError(
                "Unable to reach ClipperCard.com login page. "
                "Please visit https://www.clippercard.com/ to ensure you can login."
            )
        logger.debug("Login page fetched: %s", login_landing_resp.status_code)

        # Extract CSRF token from login page
        try:
            req_data = parser.parse_login_form_fields(login_landing_resp.text)
            csrf_token = req_data["_csrf"]
            logger.debug("CSRF token extracted: %s", csrf_token)
        except (ValueError, AttributeError) as err:
            logger.error("Failed to extract CSRF token: %s", err)
            raise ClipperCardError(f"Unable to extract CSRF token from login page: {err}") from err

        # Use the current form defaults from the login page, then override the
        # credential fields with the supplied values.
        req_data["username"] = username
        req_data["password"] = password
        # Log without password for security
        log_data = {k: v if k != "password" else "***" for k, v in req_data.items()}
        logger.debug("Posting to %s with data: %s", self.DASHBOARD_URL, log_data)
        logger.debug("Full POST data keys: %s", list(req_data.keys()))
        logger.debug("CSRF token: %s...", csrf_token[:20])

        # Build curl-like command for debugging
        curl_data = "&".join([f"{k}={v}" if k != "password" else f"{k}=***" for k, v in req_data.items()])
        logger.debug("Equivalent curl: curl -X POST %s -d '%s'", self.DASHBOARD_URL, curl_data)

        # Set Referer header for POST request
        post_headers = {"Referer": self.LOGIN_URL}

        dashboard_resp = self.post(self.DASHBOARD_URL, data=req_data, headers=post_headers)
        logger.debug("Dashboard response: %s", dashboard_resp.status_code)
        logger.debug("Final URL after redirect: %s", dashboard_resp.url)

        # Log response headers for debugging
        logger.debug("Response headers: Content-Type=%s", dashboard_resp.headers.get("Content-Type"))
        logger.debug("Response cookies: %s", dict(dashboard_resp.cookies))

        if dashboard_resp.is_error:
            logger.error("Failed to post login: %s", dashboard_resp.status_code)
            logger.error("Response text (first 500 chars): %s", dashboard_resp.text[:500])
            raise ClipperCardError(
                "Unable to authenticate with ClipperCard.com. Please verify your credentials and try again."
            )

        parsed_cards = parser.parse_dashboard_cards(dashboard_resp.text)
        resp_soup = bs4.BeautifulSoup(dashboard_resp.text, "html.parser")
        if parsed_cards or "patronDetails" in dashboard_resp.text:
            logger.debug("Login successful, dashboard page received with %d parsed cards", len(parsed_cards))
            self._dashboard_resp_text = dashboard_resp.text
            self._cards = None
            self._reused_cookies = False
            self._save_cookie_jar()
            return dashboard_resp

        # Check if we got the login page back instead of the dashboard.
        if "validate-login-form" in dashboard_resp.text:
            logger.error("Got login form back in response - authentication failed")
            logger.debug("Response contains login form")
            possible_error_msg = resp_soup.find("div", attrs={"class": "form-error-message"})
            if possible_error_msg is not None:
                error_text = parser.cleanup_whitespace(possible_error_msg.get_text())
                logger.error("Auth error from server: %s", error_text)
                error_list = resp_soup.find("ul", id="defaultValidationErrorMessageList")
                if error_list:
                    for li in error_list.find_all("li"):
                        logger.debug("  - %s", li.get_text())
                raise ClipperCardAuthError(error_text)
            raise ClipperCardAuthError("Authentication failed - credentials were rejected")

        logger.debug("Login response did not include patronDetails; keeping page for downstream parsing")
        self._dashboard_resp_text = dashboard_resp.text
        self._cards = None
        return dashboard_resp

    @property
    def profile_info(self) -> parser.Profile | None:
        """
        Returns *Profile* namedtuples associated with logged in user.
        """
        if not self._dashboard_resp_text:
            raise ClipperCardError("Must login first")
        if self._profile_loaded:
            return self._profile_info

        logger.debug("Fetching profile page: %s", self.PROFILE_URL)
        profile_resp = self.get(self.PROFILE_URL)
        if profile_resp.is_error:
            logger.warning("Failed to fetch profile page: %s", profile_resp.status_code)
            self._profile_loaded = True
            self._profile_info = None
            return self._profile_info

        try:
            self._profile_info = parser.parse_profile_page(profile_resp.text)
        except ValueError as err:
            logger.warning("Failed to parse profile page: %s", err)
            self._profile_info = None
        else:
            self._save_cookie_jar()

        self._profile_loaded = True
        return self._profile_info

    @property
    def cards(self) -> list[parser.Card]:
        """
        Returns list of *Card* namedtuples associated with logged in user
        """
        if not self._dashboard_resp_text:
            raise ClipperCardError("Must login first")
        if self._cards is None:
            logger.debug("Parsing cards from dashboard")
            self._cards = parser.parse_dashboard_cards(self._dashboard_resp_text)
            logger.debug("Found %d cards", len(self._cards))
        return self._cards
