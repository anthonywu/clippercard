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

import collections
import itertools
import logging
import re
import bs4


logger = logging.getLogger(__name__)


# === Simple Objects for ClipperCard data ===

_profile_fields = [
    "name",
    "email",
    "mailing_address",
    "phone",
    "alt_phone",
    "primary_payment",
    "backup_payment",
]


class Profile(collections.namedtuple("Profile", _profile_fields)):
    """a simple class to represent a user profile"""

    def __str__(self):
        return "\n".join(
            [
                "Name: {name}",
                "Email: {email}",
                "Address: {mailing_address}",
                "Primary Phone Number: {phone}",
                "Alternate Phone Number: {alt_phone}",
                "Primary Payment: {primary_payment}",
                "Backup Payment: {backup_payment}",
            ]
        ).format(**self._asdict())


_product_fields = ["name", "value"]  # e.g. Cash value, BART HVD 60/64


class CardFeature(collections.namedtuple("CardFeature", _product_fields)):
    """a simple class to represent a card feature e.g. reload plan"""

    def __str__(self):
        return "{name}: {value}".format(**self._asdict())


class CardProduct(collections.namedtuple("CardProduct", _product_fields)):
    """a simple class to represent a card product e.g. cash value or pass"""

    def __str__(self):
        return "{name}: {value}".format(**self._asdict())


_card_fields = [
    "serial_number",
    "nickname",
    "type",  # Adult, Senior, Youth, Disabled Discount
    "status",  # Active, Inactive
    "features",  # a list of annotated properties of the card (e.g. auto-load)
    "products",  # a list of CardProduct, e.g. Cash value, Train Pass
]


class Card(collections.namedtuple("Card", _card_fields)):
    """a simple class to represent an instance of Clipper Card"""

    def __str__(self):
        lines = [
            '{serial_number} "{nickname}" ({type} - {status})'.format(**self._asdict())
        ]
        for prod in self.products:
            lines.append(f"  - {prod}")
        for feat in self.features:
            lines.append(f"  - {feat}")
        return "\n".join(lines)


# === Helpers ===

REGEX_WHITESPACE = re.compile(r"\s+")  # noqa


def cleanup_whitespace(text_content):
    """clean up junk whitespace that comes with every table cell"""
    return re.sub(REGEX_WHITESPACE, " ", text_content.strip())


# === Section Parsers ===


def parse_login_form_csrf(login_page_content):
    """Parse the login form the _csrf arg for login submission"""
    soup = bs4.BeautifulSoup(login_page_content, "html.parser")
    login_form = soup.find("form", id="login-form")
    csrf_value = login_form.find("input", attrs={"name": "_csrf"}).attrs["value"]
    return csrf_value


def parse_cards(account_page_soup):
    """Parse the list of Clipper Cards registered to the profile"""
    card_info_divs = account_page_soup.find_all(
        "div", attrs={"class": "clipper-card-info", "data-parent": "#clipper-cards"}
    )
    card_names = []
    card_name_headers = account_page_soup.find_all(
        "h2", attrs={"class": "clipper-card-name"}
    )
    for card_name_h2 in card_name_headers:
        card_names.append(
            card_name_h2.find("span", attrs={"class": "sr-only"}).get_text()
        )
    cards = []
    for i, info_div in enumerate(card_info_divs):
        card_id = info_div.attrs["id"].replace("clipper-card-info-", "")
        big_money_value = info_div.find(
            "p",
            attrs={
                "class": "big-money",
            },
        )
        products = [
            CardProduct(
                name="Cash Value", value=big_money_value.get_text().replace(" ", "")
            )
        ]
        features = []
        feature_bullets = info_div.find("ul", attrs={"class": "bullets"})
        if feature_bullets is not None:
            for bullet_item in feature_bullets.find_all("li"):
                features.append(
                    CardFeature(name="Reload", value=bullet_item.get_text())
                )
        current_passes_div = info_div.find(
            "div", attrs={"class": "current-passes-section"}
        )
        card_type = None
        card_status = None
        all_pass_info = current_passes_div.find_all("p") or []
        for pass_info in all_pass_info:
            try:
                if "Current Passes" in pass_info.get_text():
                    products.append(
                        CardProduct(
                            name="Current Passes",
                            value=cleanup_whitespace(
                                pass_info.find_next_sibling().get_text()
                            ),
                        )
                    )
                elif "Pending Passes" in pass_info.get_text():
                    products.append(
                        CardProduct(
                            name="Pending Passes",
                            value=cleanup_whitespace(
                                pass_info.find_next_sibling().get_text()
                            ),
                        )
                    )
                elif "Card Type" in pass_info.get_text():
                    card_type = cleanup_whitespace(
                        pass_info.find_all("span")[-1].get_text()
                    )
                elif "Card Status" in pass_info.get_text():
                    card_status = cleanup_whitespace(
                        pass_info.find_all("span")[-1].get_text()
                    )
            except Exception as err:  # noqa
                logger.error("Parse error on pass_info: {%s}\n{%s}", err, pass_info)

        cards.append(
            Card(
                serial_number=card_id,
                nickname=card_names[i],
                type=card_type,
                status=card_status,
                features=features,
                products=products,
            )
        )
    return cards


def parse_profile_info(account_soup):
    """Parse the attributes of the logged in user"""
    profile_info_div = account_soup.find("div", attrs={"id": "profile-info"})
    expected_data_items = [
        "name",
        "email",
        "_",  # ignore, email_updates_enabled
        "mailing_address",
        "_",  # ignore, primary_phone_label
        "phone",
        "_",  # ignore, alt_phone_label
        "alt_phone",
    ]
    profile_data_spans = profile_info_div.find_all("span")
    profile_info = {}
    for data_item, data_span in itertools.zip_longest(
        expected_data_items, profile_data_spans
    ):
        if data_item != "mailing_address":
            profile_info[data_item] = cleanup_whitespace(data_span.get_text())
        else:
            profile_info[data_item] = cleanup_whitespace(
                data_span.find_parent().get_text().replace("Mailing Address", "")
            )
    profile_info.pop("_")
    profile_info["primary_payment"] = (
        account_soup.find("div", attrs={"id": "payment-info"})
        .find_all("span")[-1]
        .get_text()
    )
    profile_info["backup_payment"] = (
        account_soup.find("div", attrs={"id": "backup-payment-info"})
        .find_all("span")[-1]
        .get_text()
    )
    return Profile(**profile_info)
