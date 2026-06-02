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
import re
from io import StringIO

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

_CONSOLE_WIDTH = 1000


def _render_table(table):
    buffer = StringIO()
    console = Console(
        file=buffer,
        force_terminal=False,
        color_system=None,
        width=_CONSOLE_WIDTH,
    )
    console.print(table)
    return buffer.getvalue().rstrip()


def _redact_private_info(label, value):
    if value is None:
        return value
    match label.lower():
        case "name":
            return " ".join([part[:2] + "***" for part in value.split()])
        case "email":
            local, domain = value.split("@")
            return local[0] + "***@" + domain
        case "mailing_address":
            return "***"
        case "phone" | "alt_phone":
            re_match = re.match(r"(\+?\d{1,3})?([-.\s]?)[0-9-.\s]+(\d{2}-?\d{2})", value)
            if re_match:
                groups = re_match.groups()
                redacted = f"{groups[0] + groups[1] if groups[0] else ''}***-***-{groups[2]}"
                return redacted
        case "serial_number":
            return ("*" * (len(value) - 4)) + value[-4:]
    return value


def _asdict(value):
    if value is None:
        return None
    if hasattr(value, "_asdict"):
        return value._asdict()
    if isinstance(value, dict):
        return value
    return vars(value)


def _product_to_json(product):
    data = _asdict(product)
    return {
        "name": data.get("name"),
        "value": data.get("value"),
    }


def summary_json_output(user_profile, cards, show_private=False):
    """
    Serializes a user profile and its associated cards and products as JSON.
    """
    profile = _asdict(user_profile)
    if profile is not None:
        profile = {
            label: (_redact_private_info(label, value) if not show_private else value)
            for label, value in profile.items()
            if value not in (None, "")
        }

    card_items = None
    if cards is not None:
        card_items = []
        for card in cards:
            card_data = _asdict(card)
            serial_number = card_data.get("serial_number")
            if not show_private:
                serial_number = _redact_private_info("serial_number", serial_number)
            card_items.append(
                {
                    "serial_number": serial_number,
                    "nickname": card_data.get("nickname"),
                    "type": card_data.get("type"),
                    "status": card_data.get("status"),
                    "products": [_product_to_json(product) for product in card_data.get("products", [])],
                    "features": [_product_to_json(feature) for feature in card_data.get("features", [])],
                }
            )

    return json.dumps({"profile": profile, "cards": card_items}, indent=2)


def tabular_output(user_profile, cards, show_private=False):
    """
    Pretty prints a user profile and its associated cards and products.
    """
    output_parts = []

    if user_profile:
        profile_table = Table(show_header=False, box=box.ASCII)
        profile_table.add_column("name", justify="right", no_wrap=True)
        profile_table.add_column("value", justify="left", no_wrap=True)
        for label, value in user_profile._asdict().items():
            if value in (None, ""):
                continue
            if not show_private:
                value = _redact_private_info(label, value)
            profile_table.add_row(Text(str(label)), Text(str(value)))
        if profile_table.row_count:
            output_parts.append(_render_table(profile_table))

    if cards:
        card_table = Table(box=box.ASCII)
        card_table.add_column("#", justify="left", no_wrap=True)
        card_table.add_column("Name", justify="left", no_wrap=True)
        card_table.add_column("Serial", justify="left", no_wrap=True)
        card_table.add_column("Type", justify="left", no_wrap=True)
        card_table.add_column("Status", justify="left", no_wrap=True)
        card_table.add_column("Products", justify="left", no_wrap=True)
        for i, card in enumerate(cards, 1):
            serial = card.serial_number
            if not show_private:
                serial = _redact_private_info("serial_number", serial)
            card_table.add_row(
                str(i),
                Text(str(card.nickname)),
                Text(str(serial)),
                Text(str(card.type)),
                Text(str(card.status)),
                Text("\n".join(str(_) for _ in card.products + card.features)),
            )
        output_parts.append(_render_table(card_table))
    elif cards is not None:
        output_parts.append("No cards registered")

    return "\n".join(output_parts)
