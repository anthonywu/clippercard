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
import re

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
    return Profile(
        name=values[0],
        email=values[1],
        address=' '.join(values[2:5]),
        phone=values[5]
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
        section_products.append(products)
    return section_products


def parse_cards(account_page_content):
    """
    Parse card metadata and product balances from /ClipperCard/dashboard.jsf
    """
    begin = account_page_content.index('<!--YOUR CLIPPER CARDS-->')
    end = account_page_content.index('<!--END YOUR CLIPPER CARDS-->')
    card_soup = bs4.BeautifulSoup(account_page_content[begin:end], "html.parser")
    serial_numbers = find_values(card_soup, 'Serial Number:', get_next_sibling_text)
    nicknames = find_values(card_soup, 'Card Nickname:', get_inner_display_text)
    types = find_values(card_soup, 'Type:', get_next_sibling_text)
    statuses = find_values(card_soup, 'Status:', get_next_sibling_text)
    products = parse_card_products(card_soup)
    cards = []
    for sn, nn, tp, st, pd in itertools.izip(serial_numbers, nicknames, types, statuses, products):
        cards.append(Card(serial_number=sn, nickname=nn, type=tp, status=st, products=pd))
    return cards
