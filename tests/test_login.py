from pathlib import Path
from unittest.mock import patch

from requests.cookies import cookiejar_from_dict, create_cookie

from clippercard.client import ClipperCardWebSession


class DummyResponse:
    def __init__(self, text, url, status_code=200, headers=None, cookies=None):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self.headers = headers or {"Content-Type": "text/html;charset=UTF-8"}
        self.cookies = cookiejar_from_dict(cookies or {})


def test_login_posts_form_fields_as_mapping(tmp_path):
    login_html = (Path(__file__).parent / "data" / "login.html").read_text()
    observed = {}
    cookie_jar_path = tmp_path / "clippercard.cookies"

    def fake_get(self, url):
        return DummyResponse(login_html, url, cookies={"JSESSIONID": "test-session"})

    def fake_post(self, url, data=None, headers=None, allow_redirects=True):
        observed["url"] = url
        observed["data"] = data
        observed["headers"] = headers
        observed["allow_redirects"] = allow_redirects
        return DummyResponse("<html><body>dashboard</body></html>", url)

    session = ClipperCardWebSession(cookie_jar_path=cookie_jar_path)
    with (
        patch.object(ClipperCardWebSession, "get", new=fake_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        session.login("person@example.com", "supersecret")

    assert isinstance(observed["data"], dict)
    assert observed["data"]["username"] == "person@example.com"
    assert observed["data"]["password"] == "supersecret"
    assert observed["data"]["authFailCount"] == "0"
    assert observed["data"]["postLoginUrl"] == ""
    assert observed["headers"] == {"Referer": ClipperCardWebSession.LOGIN_URL}
    assert observed["allow_redirects"] is True


def test_login_accepts_dashboard_response_with_generic_form_errors(tmp_path):
    login_html = (Path(__file__).parent / "data" / "login.html").read_text()
    dashboard_html = (Path(__file__).parent / "data" / "dashboard.html").read_text()
    cookie_jar_path = tmp_path / "clippercard.cookies"

    def fake_get(self, url):
        return DummyResponse(login_html, url, cookies={"JSESSIONID": "test-session"})

    def fake_post(self, url, data=None, headers=None, allow_redirects=True):
        return DummyResponse(dashboard_html, url)

    session = ClipperCardWebSession(cookie_jar_path=cookie_jar_path)
    with (
        patch.object(ClipperCardWebSession, "get", new=fake_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        resp = session.login("person@example.com", "supersecret")

    assert resp.url == ClipperCardWebSession.DASHBOARD_URL
    assert session._dashboard_resp_text == dashboard_html
    assert len(session.cards) == 8


def test_login_reuses_saved_cookies_when_dashboard_loads(tmp_path):
    dashboard_html = (Path(__file__).parent / "data" / "dashboard.html").read_text()
    cookie_jar_path = tmp_path / "clippercard.cookies"

    seed_session = ClipperCardWebSession(cookie_jar_path=cookie_jar_path)
    seed_session.cookies.set_cookie(
        create_cookie("JSESSIONID", "saved-session", domain="www.clippercard.com", path="/")
    )
    seed_session._save_cookie_jar()

    observed = {"urls": []}

    def fake_get(self, url):
        observed["urls"].append(url)
        return DummyResponse(dashboard_html, url)

    def fake_post(self, url, data=None, headers=None, allow_redirects=True):
        raise AssertionError("POST should not be used when saved cookies are valid")

    with (
        patch.object(ClipperCardWebSession, "get", new=fake_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        session = ClipperCardWebSession(
            "person@example.com",
            "supersecret",
            cookie_jar_path=cookie_jar_path,
        )

    assert observed["urls"] == [ClipperCardWebSession.DASHBOARD_URL]
    assert session.reused_cookies is True
    assert len(session.cards) == 8


def test_login_saves_cookie_jar_after_successful_login(tmp_path):
    login_html = (Path(__file__).parent / "data" / "login.html").read_text()
    dashboard_html = (Path(__file__).parent / "data" / "dashboard.html").read_text()
    cookie_jar_path = tmp_path / "clippercard.cookies"

    def fake_get(self, url):
        if url == ClipperCardWebSession.LOGIN_URL:
            return DummyResponse(login_html, url)
        raise AssertionError(f"Unexpected GET {url}")

    def fake_post(self, url, data=None, headers=None, allow_redirects=True):
        self.cookies.set_cookie(create_cookie("JSESSIONID", "fresh-session", domain="www.clippercard.com", path="/"))
        return DummyResponse(dashboard_html, url)

    session = ClipperCardWebSession(cookie_jar_path=cookie_jar_path)
    with (
        patch.object(ClipperCardWebSession, "get", new=fake_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        session.login("person@example.com", "supersecret")

    assert cookie_jar_path.exists()
    assert cookie_jar_path.stat().st_mode & 0o777 == 0o600

    reused_urls = []

    def reuse_get(self, url):
        reused_urls.append(url)
        return DummyResponse(dashboard_html, url)

    with (
        patch.object(ClipperCardWebSession, "get", new=reuse_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        reused_session = ClipperCardWebSession(
            "person@example.com",
            "supersecret",
            cookie_jar_path=cookie_jar_path,
        )

    assert reused_urls == [ClipperCardWebSession.DASHBOARD_URL]
    assert reused_session.reused_cookies is True


def test_profile_info_fetches_and_parses_profile_page(tmp_path):
    login_html = (Path(__file__).parent / "data" / "login.html").read_text()
    dashboard_html = (Path(__file__).parent / "data" / "dashboard.html").read_text()
    profile_html = (Path(__file__).parent / "data" / "profile.html").read_text()
    cookie_jar_path = tmp_path / "clippercard.cookies"

    observed_urls = []

    def fake_get(self, url):
        observed_urls.append(url)
        if url == ClipperCardWebSession.LOGIN_URL:
            return DummyResponse(login_html, url)
        if url == ClipperCardWebSession.PROFILE_URL:
            return DummyResponse(profile_html, url)
        raise AssertionError(f"Unexpected GET {url}")

    def fake_post(self, url, data=None, headers=None, allow_redirects=True):
        return DummyResponse(dashboard_html, url)

    session = ClipperCardWebSession(cookie_jar_path=cookie_jar_path)
    with (
        patch.object(ClipperCardWebSession, "get", new=fake_get),
        patch.object(ClipperCardWebSession, "post", new=fake_post),
    ):
        session.login("person@example.com", "supersecret")
        profile = session.profile_info

    assert observed_urls == [ClipperCardWebSession.LOGIN_URL, ClipperCardWebSession.PROFILE_URL]
    assert profile.name == "EXAMPLE RIDER"
    assert profile.email == "rider@example.com"
