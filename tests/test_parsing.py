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

import os.path
import unittest
import bs4
import clippercard.parser as parser


class TestParser(unittest.TestCase):
    def setUp(self):
        with open(
            os.path.join(os.path.dirname(__file__), "../tests/data/login.html")
        ) as login_page_file:
            self.login_page_content = login_page_file.read()
        with open(
            os.path.join(os.path.dirname(__file__), "../tests/data/account.html")
        ) as login_page_file:
            self.account_page_soup = bs4.BeautifulSoup(
                login_page_file.read(), "html.parser"
            )

    def test_csrf(self):
        expected = "293b3e29-8080-4dee-a373-e383d4321a35"
        self.assertEqual(
            expected, parser.parse_login_form_csrf(self.login_page_content)
        )

    def test_profile(self):
        parsed_profile = parser.parse_profile_info(self.account_page_soup)
        self.assertEqual("Golden Gate", parsed_profile.name)
        self.assertEqual("goldengate88@example.com", parsed_profile.email)
        self.assertEqual(
            "1 Main St SAN FRANCISCO, CA 94105", parsed_profile.mailing_address
        )
        self.assertEqual("415-555-5555", parsed_profile.phone)
        self.assertEqual("650-555-5555", parsed_profile.alt_phone)
        self.assertEqual("Mastercard ending in 8888", parsed_profile.primary_payment)
        self.assertEqual("Amex ending in 1234", parsed_profile.backup_payment)

    def test_cards(self):
        parsed_cards = parser.parse_cards(self.account_page_soup)
        self.assertEqual(9, len(parsed_cards))
