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

import bs4
import collections
import itertools
import logging
import os
import re
import tempfile


logger = logging.getLogger(__name__)


# === Simple Objects for ClipperCard data ===

_profile_fields = [
    'name',
    'email',
    'address',
    'phone'
    ]


class Profile(collections.namedtuple('Profile', _profile_fields)):
    def __str__(self):
        return '\n'.join([
            'Name: {name}',
            'Email: {email}',
            'Phone: {phone}',
            'Address: {address}'
            ]).format(**self._asdict())


_product_fields = [
    'name',  # e.g. Cash value, BART HVD 60/64
    'value'
    ]


class CardProduct(collections.namedtuple('CardProduct', _product_fields)):
    def __str__(self):
        return '{name}: {value}'.format(**self._asdict())


_card_fields = [
    'serial_number',
    'nickname',
    'type',  # Adult, Senior, Youth, Disabled Discount
    'status',  # Active, Inactive
    'products'  # a list of CardProduct
    ]


class Card(collections.namedtuple('Card', _card_fields)):
    def __str__(self):
        lines = ['{serial_number} "{nickname}" ({type} - {status})'.format(**self._asdict())]
        for p in self.products:
            lines.append('  - {0}'.format(str(p)))
        return '\n'.join(lines)

# === Helpers ===

REGEX_BLING = re.compile('^\$')
REGEX_WHITESPACE = re.compile('\s+')


def cleanup_whitespace(text_content):
    """clean up junk whitespace that comes with every table cell"""
    return re.sub(REGEX_WHITESPACE, ' ', text_content.strip())


def get_next_sibling_text(element):
    return list(element.next_siblings)[1].get_text()


def get_inner_display_text(element):
    return list(element.next_siblings)[1].find(
        'span',
        attrs={'class': 'displayName'}
        ).get_text()


def find_values(soup, label_text, value_getter):
    values = []
    for label_elem in soup.find_all('div', text=label_text):
        values.append(value_getter(label_elem))
    return values


# === Section Parsers ===

def parse_profile_data(account_page_content):
    """
    Parse user profile from /ClipperCard/dashboard.jsf
    """
    soup = bs4.BeautifulSoup(account_page_content, "html.parser")
    profile_data = soup.find('div', attrs={'class': 'profileData'})
    fields = profile_data.find_all('div', attrs={'class': 'fieldData'})
    values = [cleanup_whitespace(f.get_text()) for f in fields]

    for ignorable in ['Yes', 'No', 'Edit My Profile Information']:
        if ignorable in values:        
            values.remove(ignorable)  # the value for "Email Updates" option

    try:
        name, email, addr1, addr2, city_state, zipcode, phone = values
        addr_fields = [addr1, addr2, city_state, zipcode]
    except ValueError:
        # try to unpack a 6-tuple of values, probably without addr2
        name, email, addr1, city_state, zipcode, phone = values
        addr_fields = [addr1, city_state, zipcode]

    return Profile(
        name=name.strip(),
        email=email.strip(),
        address=' '.join((x.strip() for x in addr_fields)),
        phone=phone.strip()
        )


def parse_card_products(card_soup):
    """
    Parse card product names and balances from /ClipperCard/dashboard.jsf
    """
    section_products = []
    for card_section in card_soup.find_all('div', attrs={'class': 'whiteGreyCardBox'}):
        products = []
        blings = card_section.find_all('div', text=REGEX_BLING)
        for value_node in blings:
            name = list(value_node.previous_siblings)[1].get_text().strip(':')
            products.append(CardProduct(name=name, value=value_node.get_text()))
        caltrain = card_section.find_all('div', text=re.compile('^Valid till'))
        for value_train in caltrain:
            name = list(value_train.previous_siblings)[1].get_text().strip(':')
            value_time = value_train.get_text()
            products.append(CardProduct(name=name, value=value_time))
        section_products.append(products)
    return section_products


def parse_cards(account_page_content, debug_mode=('CLIPPERCARD_DEBUG' in os.environ)):
    """
    Parse card metadata and product balances from /ClipperCard/dashboard.jsf
    """
    if debug_mode:
        dump_file = '{}/most_recent_account_page.html'.format(tempfile.gettempdir())
        with open(dump_file, 'wb') as temp_dump:
            temp_dump.write(account_page_content)
            print("CLIPPERCARD_DEBUG - account page HTML saved in {}".format(dump_file))

    begin = account_page_content.index(b'<!--YOUR CLIPPER CARDS-->')
    end = account_page_content.index(b'<!--END YOUR CLIPPER CARDS-->')
    card_soup = bs4.BeautifulSoup(account_page_content[begin:end], "html.parser")
    serial_numbers = find_values(card_soup, 'Serial Number:', get_next_sibling_text)
    nicknames = find_values(card_soup, 'Card Nickname:', get_inner_display_text)
    types = find_values(card_soup, 'Type:', get_next_sibling_text)
    statuses = find_values(card_soup, 'Status:', get_next_sibling_text)
    products = parse_card_products(card_soup)
    cards = []
    for sn, nn, tp, st, pd in zip(serial_numbers, nicknames, types, statuses, products):
        cards.append(Card(serial_number=sn, nickname=nn, type=tp, status=st, products=pd))
    return cards
