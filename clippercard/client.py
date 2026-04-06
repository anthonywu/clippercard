"""
Copyright (c) 2012-2021 (https://github.com/clippercard/clippercard-python)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# === imports ===

import logging
from http.cookiejar import LoadError, MozillaCookieJar
from pathlib import Path

import bs4
import requests

import clippercard.parser as parser

logger = logging.getLogger(__name__)

# === Error Classes ===


class ClipperCardError(Exception):
    """base error for client"""


class ClipperCardAuthError(ClipperCardError):
    """unable to login with provided credentials"""


class ClipperCardContentError(ClipperCardError):
    """unable to recognize and parse web content"""


# === ClipperCardWebSession ===


class ClipperCardWebSession(requests.Session):
    """
    A stateful session for clippercard.com
    """

    LOGIN_URL = "https://www.clippercard.com/web-login"
    DASHBOARD_URL = "https://www.clippercard.com/dashboard"
    PROFILE_URL = "https://www.clippercard.com/profile"
    COOKIE_JAR_PATH = Path("~/.config/clippercard/auth.cookies").expanduser()
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
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self, username=None, password=None, cookie_jar_path=None):
        requests.Session.__init__(self)
        self.headers.update(self.HEADERS)
        self._cookie_jar_path = Path(cookie_jar_path).expanduser() if cookie_jar_path else self.COOKIE_JAR_PATH
        self.cookies = MozillaCookieJar(str(self._cookie_jar_path))
        self._dashboard_resp_text = None
        self._profile_info = None
        self._profile_loaded = False
        self._reused_cookies = False
        if username and password:
            self.login(username, password)

    @property
    def reused_cookies(self):
        return self._reused_cookies

    @property
    def cookie_jar_path(self):
        return self._cookie_jar_path

    def _load_cookie_jar(self):
        if not self._cookie_jar_path.exists():
            return False
        try:
            self.cookies.load(ignore_discard=True, ignore_expires=True)
        except LoadError:
            logger.warning(f"Cookie jar at {self._cookie_jar_path} is unreadable; ignoring it")
            return False
        loaded_cookies = list(self.cookies)
        logger.debug(f"Loaded {len(loaded_cookies)} cookies from {self._cookie_jar_path}")
        return bool(loaded_cookies)

    def _save_cookie_jar(self):
        self._cookie_jar_path.parent.mkdir(parents=True, exist_ok=True)
        self.cookies.save(ignore_discard=True, ignore_expires=True)
        self._cookie_jar_path.chmod(0o600)
        logger.debug(f"Saved cookies to {self._cookie_jar_path}")

    def _clear_cookie_jar(self):
        self.cookies.clear()
        if self._cookie_jar_path.exists():
            self._cookie_jar_path.unlink()
            logger.debug(f"Removed stale cookie jar at {self._cookie_jar_path}")

    @staticmethod
    def _response_has_dashboard_data(response_text):
        return "patronDetails" in response_text

    def _fetch_dashboard_with_cookies(self):
        if not self._load_cookie_jar():
            return None

        logger.debug(f"Trying saved cookies from {self._cookie_jar_path}")
        dashboard_resp = self.get(self.DASHBOARD_URL)
        logger.debug(f"Dashboard-with-cookies response: {dashboard_resp.status_code}")
        logger.debug(f"Final URL after cookie reuse: {dashboard_resp.url}")

        if dashboard_resp.ok and self._response_has_dashboard_data(dashboard_resp.text):
            self._dashboard_resp_text = dashboard_resp.text
            self._reused_cookies = True
            self._save_cookie_jar()
            logger.debug("Saved cookies are still valid")
            return dashboard_resp

        logger.debug("Saved cookies did not yield a valid dashboard; falling back to login")
        self._dashboard_resp_text = None
        self._reused_cookies = False
        self._clear_cookie_jar()
        return None

    def login(self, username, password):
        """
        Authenticate user and fetch dashboard page.
        1. Try saved cookies against /dashboard
        2. GET /web-login to get CSRF token
        3. POST to /dashboard with credentials + CSRF
        """
        logger.debug(f"Logging in as {username}")

        reused_resp = self._fetch_dashboard_with_cookies()
        if reused_resp is not None:
            return reused_resp

        # Get login page to extract CSRF token
        logger.debug(f"Fetching login page: {self.LOGIN_URL}")
        login_landing_resp = self.get(self.LOGIN_URL)
        if not login_landing_resp.ok:
            logger.error(f"Failed to get login page: {login_landing_resp.status_code}")
            raise ClipperCardError(
                "Unable to reach ClipperCard.com login page. "
                "Please visit https://www.clippercard.com/ to ensure you can login."
            )
        logger.debug(f"Login page fetched: {login_landing_resp.status_code}")

        # Extract CSRF token from login page
        try:
            req_data = parser.parse_login_form_fields(login_landing_resp.text)
            csrf_token = req_data["_csrf"]
            logger.debug(f"CSRF token extracted: {csrf_token}")
        except (ValueError, AttributeError) as err:
            logger.error(f"Failed to extract CSRF token: {err}")
            raise ClipperCardError(f"Unable to extract CSRF token from login page: {err}") from err

        # Use the current form defaults from the login page, then override the
        # credential fields with the supplied values.
        req_data["username"] = username
        req_data["password"] = password
        # Log without password for security
        log_data = {k: v if k != "password" else "***" for k, v in req_data.items()}
        logger.debug(f"Posting to {self.DASHBOARD_URL} with data: {log_data}")
        logger.debug(f"Full POST data keys: {list(req_data.keys())}")
        logger.debug(f"CSRF token: {csrf_token[:20]}...")

        # Build curl-like command for debugging
        curl_data = "&".join([f"{k}={v}" if k != "password" else f"{k}=***" for k, v in req_data.items()])
        logger.debug(f"Equivalent curl: curl -X POST {self.DASHBOARD_URL} -d '{curl_data}'")

        # Set Referer header for POST request
        post_headers = {"Referer": self.LOGIN_URL}

        dashboard_resp = self.post(self.DASHBOARD_URL, data=req_data, headers=post_headers, allow_redirects=True)
        logger.debug(f"Dashboard response: {dashboard_resp.status_code}")
        logger.debug(f"Final URL after redirect: {dashboard_resp.url}")

        # Log response headers for debugging
        logger.debug(f"Response headers: Content-Type={dashboard_resp.headers.get('Content-Type')}")
        logger.debug(f"Response cookies: {dict(dashboard_resp.cookies)}")

        if not dashboard_resp.ok:
            logger.error(f"Failed to post login: {dashboard_resp.status_code}")
            logger.error(f"Response text (first 500 chars): {dashboard_resp.text[:500]}")
            raise ClipperCardError(
                "Unable to authenticate with ClipperCard.com. Please verify your credentials and try again."
            )

        parsed_cards = parser.parse_dashboard_cards(dashboard_resp.text)
        resp_soup = bs4.BeautifulSoup(dashboard_resp.text, "html.parser")
        if parsed_cards or "patronDetails" in dashboard_resp.text:
            logger.debug(f"Login successful, dashboard page received with {len(parsed_cards)} parsed cards")
            self._dashboard_resp_text = dashboard_resp.text
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
                logger.error(f"Auth error from server: {error_text}")
                error_list = resp_soup.find("ul", id="defaultValidationErrorMessageList")
                if error_list:
                    for li in error_list.find_all("li"):
                        logger.debug(f"  - {li.get_text()}")
                raise ClipperCardAuthError(error_text)
            raise ClipperCardAuthError("Authentication failed - credentials were rejected")

        logger.debug("Login response did not include patronDetails; keeping page for downstream parsing")
        self._dashboard_resp_text = dashboard_resp.text
        return dashboard_resp

    @property
    def profile_info(self):
        """
        Returns *Profile* namedtuples associated with logged in user.
        """
        if not self._dashboard_resp_text:
            raise ClipperCardError("Must login first")
        if self._profile_loaded:
            return self._profile_info

        logger.debug(f"Fetching profile page: {self.PROFILE_URL}")
        profile_resp = self.get(self.PROFILE_URL)
        if not profile_resp.ok:
            logger.warning(f"Failed to fetch profile page: {profile_resp.status_code}")
            self._profile_loaded = True
            self._profile_info = None
            return self._profile_info

        try:
            self._profile_info = parser.parse_profile_page(profile_resp.text)
        except ValueError as err:
            logger.warning(f"Failed to parse profile page: {err}")
            self._profile_info = None
        else:
            self._save_cookie_jar()

        self._profile_loaded = True
        return self._profile_info

    @property
    def cards(self):
        """
        Returns list of *Card* namedtuples associated with logged in user
        """
        if not self._dashboard_resp_text:
            raise ClipperCardError("Must login first")
        logger.debug("Parsing cards from dashboard")
        cards = parser.parse_dashboard_cards(self._dashboard_resp_text)
        logger.debug(f"Found {len(cards)} cards")
        return cards

    def print_summary(self):
        """return a text summary of the account"""
        print(self.profile_info)
        print("=" * 80)
        for card in sorted(self.cards, key=lambda card: card.serial_number):
            print(card)
            print("-" * 80)
