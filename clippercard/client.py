"""
Copyright (c) 2012-2017 (https://github.com/clippercard/clippercard-python)

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
import clippercard.parser as parser
import requests


# === Error Classes ===

class ClipperCardError(Exception):
    # base error for client
    pass


class ClipperCardAuthError(ClipperCardError):
    # unable to login with credentials
    pass


class ClipperCardContentError(ClipperCardError):
    # unable to recognize web content
    pass


# === ClipperCardWebSession ===

def soupify(method, *method_pargs, **method_kwargs):
    # helper: makes the method call, puts content in BeautifulSoup
    resp = method(*method_pargs, **method_kwargs)
    soup = bs4.BeautifulSoup(resp.content, "html.parser")
    return resp, soup


class ClipperCardWebSession(requests.Session):
    """
    A stateful session for clippercard.com
    """
    LOGIN_URL = 'https://www.clippercard.com/ClipperCard/loginFrame.jsf'
    BALANCE_URL = 'https://www.clippercard.com/ClipperWeb/cardValue.do?cardNumber=%s'
    HEADERS = {
        'FAKE_USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
        }

    def __init__(self, username=None, password=None):
        requests.Session.__init__(self)
        self.headers.update(self.HEADERS)
        self._dashboard_content = None
        if username and password:
            self.login(username, password)

    def login(self, username, password):
        """
        Mimicks user login via /ClipperCard/loginFrame.jsf
        """
        resp_login, soup_login = soupify(self.get, self.LOGIN_URL)
        form_login = soup_login.find('form')
        if not form_login:
            raise ClipperCardContentError('Cannot find login form on login page')
        login_inputs = form_login.find_all('input')

        post_data = {
            'javax.faces.source': 'j_idt13:submitLogin',
            'javax.faces.partial.event': 'click',
            'javax.faces.partial.execute ': ':submitLogin j_idt13:username j_idt13:password',
            'javax.faces.partial.render': 'j_idt13:err',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.ajax': 'true'
        }

        # gather the dynamic post-data from the form, but replace the username/password pair
        for each in login_inputs:
            name, value = (each.get('name'), each.get('value'))
            if name.endswith('username'):
                value = username
            elif name.endswith('password'):
                value = password
            post_data[name] = value

        resp, soup = soupify(self.post, self.LOGIN_URL, data=post_data)
        invalid_creds_span = soup.find('span', text='Invalid Credentials')
        if invalid_creds_span:
            raise ClipperCardAuthError('Invalid login info for %s' % username)
        else:
            self._dashboard_content = resp.content
        return resp

    @property
    def user_profile(self):
        """
        Returns *Profile* namedtuples associated with logged in user
        """
        if not self._dashboard_content:
            raise ClipperCardError('Must login first')
        return parser.parse_profile_data(self._dashboard_content)

    @property
    def cards(self):
        """
        Returns list of *Card* namedtuples associated with logged in user
        """
        if not self._dashboard_content:
            raise ClipperCardError('Must login first')
        return parser.parse_cards(self._dashboard_content)

    def get_summary(self):
        lines = [str(self.user_profile), '-' * 40]
        for index, card in enumerate(self.cards, 1):
            lines.append('Card {0}: {1}'.format(index, str(card)))
        return '\n'.join(lines)
