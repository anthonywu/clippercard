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

import clippercard.parser as parser
import os.path
import unittest


class TestParser(unittest.TestCase):

    def setUp(self):
        test_file_1 = os.path.join(os.path.dirname(__file__), '../tests/data/dashboard_user_1.html')
        with open(test_file_1, 'rb') as f:
            self.test_content_1 = f.read()
        test_file_2 = os.path.join(os.path.dirname(__file__), '../tests/data/dashboard_user_2.html')
        with open(test_file_2, 'rb') as f:
            self.test_content_2 = f.read()

    def test_profile_1(self):
        profile = parser.parse_profile_data(self.test_content_1)
        self.assertEqual('John Smith', profile.name)
        self.assertEqual('jsmith@example.org', profile.email)
        self.assertEqual('1 Main St SAN FRANCISCO, CA 94103', profile.address)
        self.assertEqual('415-555-5555', profile.phone)

    def test_profile_2(self):
        profile = parser.parse_profile_data(self.test_content_2)
        self.assertEqual('Mr. FIRSTNAME LASTNAME', profile.name)
        self.assertEqual('EMAIL@FOO.BAR', profile.email)
        self.assertEqual('123, Whatever street Apt 1234 San Francisco, CA 94103', profile.address)
        self.assertEqual('415-555-5555', profile.phone)

    def test_cards_1(self):
        card1, card2 = parser.parse_cards(self.test_content_1)
        self.assertEqual('111', card1.serial_number)
        self.assertEqual('Golden Gate Bridge Limited Edition', card1.nickname)
        self.assertEqual('ADULT', card1.type)
        self.assertEqual('Active', card1.status)
        self.assertEqual('222', card2.serial_number)
        self.assertEqual('Bay Bridge Limited Edition', card2.nickname)
        self.assertEqual('YOUTH', card2.type)
        self.assertEqual('Active', card2.status)
        bart_hvd, cash1 = card1.products
        self.assertEqual('BART HVD 60/64', bart_hvd.name)
        self.assertEqual('$47.55', bart_hvd.value)
        self.assertEqual('Cash value', cash1.name)
        self.assertEqual('$51.40', cash1.value)
        cash2 = card2.products[0]
        self.assertEqual('Cash value', cash2.name)
        self.assertEqual('$2.35', cash2.value)
