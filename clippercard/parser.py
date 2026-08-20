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

import json
import logging
import re
from datetime import datetime
from typing import NamedTuple

import bs4

logger = logging.getLogger(__name__)


# === Simple Objects for ClipperCard data ===


class Profile(NamedTuple):
    """a simple class to represent a user profile"""

    name: str
    email: str
    mailing_address: str
    phone: str
    alt_phone: str
    primary_payment: str
    backup_payment: str

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


class CardFeature(NamedTuple):
    """a simple class to represent a card feature e.g. reload plan"""

    name: str
    value: str

    def __str__(self):
        return "{name}: {value}".format(**self._asdict())


class CardProduct(NamedTuple):
    """a simple class to represent a card product e.g. cash value or pass"""

    name: str
    value: str

    def __str__(self):
        return "{name}: {value}".format(**self._asdict())


class Card(NamedTuple):
    """a simple class to represent an instance of Clipper Card"""

    serial_number: str
    nickname: str
    type: str | None  # Adult, Senior, Youth, Disabled Discount
    status: str  # Active, Inactive
    features: list[CardFeature]  # annotated properties of the card (e.g. auto-load)
    products: list[CardProduct]  # e.g. Cash Value, Train Pass

    def __str__(self):
        lines = ['{serial_number} "{nickname}" ({type} - {status})'.format(**self._asdict())]
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
    # Find the form that posts to /dashboard (new login form)
    login_form = soup.find("form", attrs={"action": "/dashboard"})
    if not login_form:
        # Fallback to old form structure
        login_form = soup.find("form", id="login-form")
    if not login_form:
        raise ValueError("Could not find login form")
    csrf_input = login_form.find("input", attrs={"name": "_csrf"})
    if not csrf_input:
        raise ValueError("Could not find CSRF token in login form")
    csrf_value = csrf_input.attrs["value"]
    return csrf_value


def parse_login_form_fields(login_page_content):
    """Parse default field values from the login form."""
    soup = bs4.BeautifulSoup(login_page_content, "html.parser")
    login_form = soup.find("form", attrs={"action": "/dashboard"})
    if not login_form:
        login_form = soup.find("form", id="login-form")
    if not login_form:
        raise ValueError("Could not find login form")

    fields = {}
    for field in login_form.find_all(["input", "textarea", "select"]):
        name = field.get("name")
        if not name:
            continue

        if field.name == "input":
            field_type = field.get("type", "").lower()
            if field_type in {"submit", "button", "image", "file", "reset"}:
                continue
            fields[name] = field.get("value", "")
        elif field.name == "textarea":
            fields[name] = field.text or ""
        elif field.name == "select":
            selected = field.find("option", selected=True)
            fields[name] = selected.get("value", "") if selected else ""

    return fields


def parse_profile_page(profile_html_content):
    """Parse the modern /profile page."""
    soup = bs4.BeautifulSoup(profile_html_content, "html.parser")

    email_el = soup.find(id="email-text")
    profile_card = soup.find("div", id="profile-div")
    if email_el is None or profile_card is None:
        raise ValueError("Could not find expected profile fields in /profile page")

    card_body = profile_card.find("div", class_="card-body")
    if card_body is None:
        raise ValueError("Could not find profile card body in /profile page")

    values = {}
    for heading in card_body.find_all("h4"):
        label = cleanup_whitespace(heading.get_text())
        value_el = heading.find_next_sibling("p")
        if value_el is None:
            continue
        values[label] = cleanup_whitespace(value_el.get_text(" ", strip=True))

    return Profile(
        name=values.get("Name", ""),
        email=cleanup_whitespace(email_el.get_text()),
        mailing_address=values.get("Shipping Address", ""),
        phone=values.get("Phone", ""),
        alt_phone=values.get("Alternate Phone", ""),
        primary_payment="",
        backup_payment="",
    )


def _cents_to_dollars(cents):
    """Convert cents (int) to formatted dollar string"""
    if cents is None:
        return None
    dollars = cents / 100.0
    return f"${dollars:.2f}"


def _purse_display_name(purse):
    if purse.get("purseRestriction") == "Unrestricted":
        return "Cash Value"
    for candidate in (purse.get("description"), purse.get("purseName")):
        if candidate:
            return re.sub(r"\s+HVD Purse$", "", candidate).strip() or candidate
    return "Purse"


def _product_from_purse(purse):
    if not purse or purse.get("balance") is None:
        return None
    return CardProduct(name=_purse_display_name(purse), value=_cents_to_dollars(purse["balance"]))


def _products_from_purses(account):
    """Operator-restricted purses (BART, Muni, ...) live in purseList, not bartPurse-only."""
    purse_list = account.get("purseList")
    if purse_list:
        return [product for purse in purse_list if (product := _product_from_purse(purse))]

    products = []
    cash_purse = account.get("cashPurse")
    if cash_purse and cash_purse.get("balance") is not None:
        products.append(CardProduct(name="Cash Value", value=_cents_to_dollars(cash_purse["balance"])))
    bart_purse = account.get("bartPurse")
    if bart_purse and bart_purse.get("balance") is not None:
        products.append(CardProduct(name="BART", value=_cents_to_dollars(bart_purse["balance"])))
    return products


def parse_dashboard_cards(dashboard_html_content):
    """Parse card data from dashboard page (contains JSON object with card info)

    The dashboard page embeds a JavaScript variable with patron account details
    containing card nicknames, cash values, and agency purse balances.
    """
    soup = bs4.BeautifulSoup(dashboard_html_content, "html.parser")

    # Find the script tag containing patronDetails JavaScript object
    scripts = soup.find_all("script")
    patron_details = None

    for script in scripts:
        if script.string and "patronDetails" in script.string:
            # Extract the JavaScript object
            script_content = script.string
            # Find the var patronDetails = { ... }; section
            start = script_content.find("var patronDetails = {")
            if start != -1:
                json_str = _extract_js_object_str(script_content, start)
                if json_str is None:
                    logger.warning("Could not extract patronDetails JS object")
                    continue
                try:
                    patron_details = _parse_js_object(json_str)
                    break
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse patron details JSON: %s", e)
                    continue

    if not patron_details:
        logger.warning("Could not find patronDetails in dashboard HTML")
        return []

    cards = []
    # Cards are in primaryCustomer.displayCardList
    primary_customer = patron_details.get("primaryCustomer", {})
    card_accounts = primary_customer.get("displayCardList", [])

    for account in card_accounts:
        nickname = account.get("nickname", "Unknown")
        serial_number = account.get("subsystemAccountReference", "")

        products = _products_from_purses(account)

        pass_list = account.get("passList", [])
        for pass_info in pass_list:
            logger.debug("Parsing pass info: %s", pass_info.keys())
            pass_name = pass_info.get("passDescription", "Unknown Pass")
            # NB: expirationDateTime is likely card validity, not pass expiration
            # empirically it is ~100 years after pass activation
            end_date_time = pass_info.get("endDateTime")
            expiration = datetime.fromisoformat(end_date_time).date() if end_date_time else None
            value = f"{pass_name}\n  - Expires {expiration}" if expiration else pass_name
            products.append(CardProduct(name="Pass", value=value))

        # Card features (currently empty, can extend later)
        features = []

        card = Card(
            serial_number=serial_number,
            nickname=nickname,
            type=account.get("riderClassDescription"),
            status=account.get("accountTokenVO", {}).get("status", "Unknown"),
            features=features,
            products=products,
        )
        cards.append(card)

    return cards


def _extract_string_literals(js_str):
    """Replace JS string literals with placeholder tokens to protect them from regex."""
    placeholders = {}
    result = []
    i = 0
    counter = 0

    while i < len(js_str):
        ch = js_str[i]
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            while j < len(js_str):
                if js_str[j] == "\\":
                    j += 2
                    continue
                if js_str[j] == quote:
                    j += 1
                    break
                j += 1
            placeholder = f"\x00STR{counter}\x00"
            placeholders[placeholder] = js_str[i:j]
            result.append(placeholder)
            counter += 1
            i = j
        else:
            result.append(ch)
            i += 1

    return "".join(result), placeholders


def _restore_string_literals(text, placeholders):
    for placeholder, original in placeholders.items():
        text = text.replace(placeholder, original)
    return text


def _extract_js_object_str(script_content, start):
    """Extract a JS object from script_content starting at *start*, handling braces inside strings."""
    start_brace = script_content.find("{", start)
    if start_brace == -1:
        return None

    i = start_brace
    brace_count = 0
    in_string = None
    escape = False

    while i < len(script_content):
        ch = script_content[i]

        if escape:
            escape = False
            i += 1
            continue

        if ch == "\\" and in_string:
            escape = True
            i += 1
            continue

        if in_string:
            if ch == in_string:
                in_string = None
        else:
            if ch in ('"', "'"):
                in_string = ch
            elif ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    return script_content[start_brace : i + 1]

        i += 1

    return None


def _parse_js_object(js_str):
    """Parse JavaScript object notation to Python dict

    Handles JS quirks like unquoted keys, trailing commas, etc.
    String literals are protected from corruption during transformation.
    """
    protected, placeholders = _extract_string_literals(js_str)

    protected = re.sub(r"([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)(\s*:)", r'\1"\2"\3', protected)
    protected = re.sub(r",(\s*[}\]])", r"\1", protected)
    protected = re.sub(r"\bundefined\b", "null", protected)

    json_str = _restore_string_literals(protected, placeholders)
    return json.loads(json_str)
