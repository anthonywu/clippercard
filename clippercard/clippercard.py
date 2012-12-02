"""
Copyright (c) 2012 Anthony Wu (@anthonywu)

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

import re
from collections import namedtuple

# === third-party libs ===

import requests
from pyquery import PyQuery # requires lxml

# a fake user agent to make the access sessions look human-driven
FAKE_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11'

# === Text Utilities ===

WHITESPACE = re.compile('\s+')
NOT_DIGITS = re.compile('\D')

def cleanup_whitespace(text_content):
    """clean up junk whitespace that comes with every table cell"""
    return re.sub(WHITESPACE, ' ', text_content.strip())

def cleanup_card_serial_number(card_num_content):
    """clean up junk content that comes from the web site's card serial number table cell"""
    return re.sub(NOT_DIGITS, '', card_num_content)


# === Simple objects for Clipper Card logic ===

# a card has a serial number, a type of {Adult, Senior, Youth, Disabled Discount} and status of {Active, Inactive}
Card = namedtuple('Card', ['serial_number', 'type', 'status'])

# an account has a dict of personal detail key-value pairs, and can be associated with multiple cards
Account = namedtuple('Account', ['personal_details', 'cards'])

# a cash card as a 'valid_for' float value, a pass has an 'expires_on' date
Balance = namedtuple('Balance', ['product', 'valid_for', 'expires_on', 'autoload_options'])


# === Parsers for Clipper Card web site content

def parse_acct_content(acct_html_content):
    """Parse https://www.clippercard.com/ClipperWeb/accountManagement.do for cardholder details and card list"""
    query_acct = PyQuery(acct_html_content)
    # the first table on the page contains personal details, the second contains card details
    personal_detail_table, card_table = query_acct('table')[:2]

    personal_details = {}
    for row in personal_detail_table.findall('tr'):
        label_content, data_content = [str(c.text_content()).strip() for c in row.findall('td')[:2]]
        if label_content:
            personal_details[label_content.strip(':')] = cleanup_whitespace(data_content)

    # TODO: currently, card parsing logic assumes existence of only one card in this account
    card_data = {}
    for row in card_table.findall('tr'):
        # Note: strangely, card data is provided in unicode
        label_content, data_content = [unicode(c.text_content()).strip() for c in row.findall('td')[:2]]
        if label_content:
            # Parse 'Serial Number:', 'Type:', 'Status:' label texts into Card namedtuple keys
            attr = label_content.strip(':').lower().replace(' ', '_')
            val = cleanup_whitespace(data_content)
            if attr == 'serial_number':
                val = str(cleanup_card_serial_number(val))
            card_data[attr] = val

    return Account(
        personal_details=personal_details,
        cards=[Card(**card_data)]
        )

def parse_card_balance(balance_html_content):
    """Parse https://www.clippercard.com/ClipperWeb/cardValue.do response page for a list of balances for one card"""
    query_balance = PyQuery(balance_html_content)
    value_table = query_balance('table')[0]
    data_rows = value_table.findall('tr')[1:] # discard the header row
    balances = []
    for row in data_rows:
        product, val, autoload_options = [str(c.text_content().strip()) for c in row.findall('td')[:3]]
        if val.startswith('$'):
            valid_for = float(val[1:])
            expires_on = None
        else:
            expires_on = val
            valid_for = None
        if autoload_options == '-':
            autoload_options = None
        balances.append(
            Balance(
                product=product,
                valid_for=valid_for,
                expires_on=expires_on,
                autoload_options=autoload_options
                )
            )
    return balances

# === ClipperCardWebSession ===

class ClipperCardWebSession(requests.Session):
    LOGIN_URL = 'https://www.clippercard.com/ClipperWeb/login.do'
    BALANCE_URL = 'https://www.clippercard.com/ClipperWeb/cardValue.do?cardNumber=%s'

    class InvalidLogin(Exception):
        pass

    def __init__(self):
        requests.Session.__init__(self, headers={
                'User-Agent': FAKE_USER_AGENT
                })

    def login(self, username, password):
        form_data = {
            'username': username,
            'password': password
            }
        resp = self.post(self.LOGIN_URL, data=form_data)
        if not 'Account Management' in resp.content:
            raise self.InvalidLogin('Invalid login info for %s' % username)
        return resp

    def check_balance(self, card_num):
        resp = self.post(self.BALANCE_URL % card_num)
        return resp


# === Utils for human-readable display  ===

ACCT_PRINT_TEMPLATE = '''Cardholder: %(Cardholder)s
Email: %(Email)s
Address: %(Address)s
Phone: %(Phone)s
'''

def print_acct_info(acct_data, balance_lookup):
    print ACCT_PRINT_TEMPLATE % acct_data.personal_details
    for card in acct_data.cards:
        balances = balance_lookup[card.serial_number]
        print 'Card: %s - %s (%s)' % (card.serial_number, card.type.title(), card.status)
        for b in balances:
            autoload_text = b.autoload_options or 'n/a'
            if b.expires_on:
                print '- %s: Expires on %s, Autoload: %s' % (b.product, b.expires_on, autoload_text)
            if b.valid_for:
                print '- %s: Valid for $%s, Autoload: %s' % (b.product, b.valid_for, autoload_text)


# === Main ===

if __name__ == '__main__':
    import os, getpass
    try:
        auth = {
            'username': os.environ.get('CLIPPER_USERNAME', None) or raw_input('Clipper Card username > '),
            'password': os.environ.get('CLIPPER_PASSWORD', None) or getpass.unix_getpass('Clipper Card password > ')
        }
        session = ClipperCardWebSession()
        login_resp = session.login(**auth)
        acct = parse_acct_content(login_resp.content)
        balance_lookup = {} # a map of serial_number --> list of balances
        for c in acct.cards:
            resp = session.check_balance(c.serial_number)
            balance_lookup[c.serial_number] = parse_card_balance(resp.content)
        print_acct_info(acct, balance_lookup)
    except Exception, e:
        print e.message
