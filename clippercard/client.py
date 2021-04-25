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

import bs4
import requests
import clippercard.parser as parser


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

    LOGIN_URL = "https://www.clippercard.com/ClipperWeb/account"
    BALANCE_URL = "https://www.clippercard.com/ClipperWeb/account.html"
    HEADERS = {
        "FAKE_USER_AGENT": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.85 Safari/537.36"
        )
    }

    def __init__(self, username=None, password=None):
        requests.Session.__init__(self)
        self.headers.update(self.HEADERS)
        self._account_resp_soup = None
        if username and password:
            self.login(username, password)

    def login(self, username, password):
        """
        Mimicks user login form submission
        """
        login_landing_resp = self.get(self.LOGIN_URL)

        if login_landing_resp.ok:
            req_data = {
                "_csrf": parser.parse_login_form_csrf(login_landing_resp.text),
                "email": username,
                "password": password,
            }
        else:
            raise ClipperCardError(
                "ClipperCard.com site may be down right now. Try again later."
            )

        login_resp = self.post(self.LOGIN_URL, data=req_data)
        if not login_resp.ok:
            raise ClipperCardError(
                "ClipperCard.com site may be down right now. Try again later."
            )

        resp_soup = bs4.BeautifulSoup(login_resp.text, "html.parser")
        possible_error_msg = resp_soup.find(
            "div", attrs={"class": "form-error-message"}
        )
        if possible_error_msg is not None:
            raise ClipperCardAuthError(
                parser.cleanup_whitespace(possible_error_msg.get_text())
            )

        # assume account page is reachable now
        self._account_resp_soup = resp_soup
        return login_resp

    @property
    def profile_info(self):
        """
        Returns *Profile* namedtuples associated with logged in user
        """
        if not self._account_resp_soup:
            raise ClipperCardError("Must login first")
        return parser.parse_profile_info(self._account_resp_soup)

    @property
    def cards(self):
        """
        Returns list of *Card* namedtuples associated with logged in user
        """
        if not self._account_resp_soup:
            raise ClipperCardError("Must login first")
        return parser.parse_cards(self._account_resp_soup)

    def print_summary(self):
        """return a text summary of the account"""
        print(self.profile_info)
        print("=" * 80)
        for card in sorted(self.cards, key=lambda card: card.serial_number):
            print(card)
            print("-" * 80)
