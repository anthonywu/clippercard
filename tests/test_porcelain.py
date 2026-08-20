import json
from collections import namedtuple
from types import SimpleNamespace

from rich.ansi import AnsiDecoder
from rich.style import Style

from clippercard.porcelain import (
    _HEADER_STYLE,
    _ROW_HEADER_STYLE,
    _column_style,
    summary_json_output,
    tabular_output,
)


def test_tabular_output_renders_profile_and_cards_as_ascii_tables():
    profile = namedtuple("Profile", "name email alt_phone")(
        name="Golden Gate Hacker",
        email="goldengate88@systemfu.com",
        alt_phone="",
    )
    cards = [
        SimpleNamespace(
            nickname="Primary, card #2021234134",
            serial_number="2021234134",
            type="ADULT",
            status="Active",
            products=["Cash Value: $195.00", "Current Passes: None"],
            features=["Reload: $255 - Autoload"],
        )
    ]

    output = tabular_output(profile, cards, show_private=True)

    assert (
        output
        == """+-----------------------------------+
|  name | Golden Gate Hacker        |
| email | goldengate88@systemfu.com |
+-----------------------------------+
+-------------------------------------------------------------------------------------------------------------+
| # | Name                      | Serial     | Type  | Status | Cash Value | Current Passes | Reload          |
|---+---------------------------+------------+-------+--------+------------+----------------+-----------------|
| 1 | Primary, card #2021234134 | 2021234134 | ADULT | Active |    $195.00 | None           | $255 - Autoload |
+-------------------------------------------------------------------------------------------------------------+"""
    )


def test_tabular_output_renders_profile_and_cards_as_ascii_tables_without_private_info():
    profile = namedtuple("Profile", "name email alt_phone")(
        name="Golden Gate Hacker",
        email="goldengate88@systemfu.com",
        alt_phone="",
    )
    cards = [
        SimpleNamespace(
            nickname="Primary, card ending in 4134",
            serial_number="2021234134",
            type="ADULT",
            status="Active",
            products=["Cash Value: $195.00", "Current Passes: None"],
            features=["Reload: $255 - Autoload"],
        )
    ]

    output = tabular_output(profile, cards, show_private=False)

    assert (
        output
        == """+---------------------------+
|  name | Go*** Ga*** Ha*** |
| email | g***@systemfu.com |
+---------------------------+
+----------------------------------------------------------------------------------------------------------------+
| # | Name                         | Serial     | Type  | Status | Cash Value | Current Passes | Reload          |
|---+------------------------------+------------+-------+--------+------------+----------------+-----------------|
| 1 | Primary, card ending in 4134 | ******4134 | ADULT | Active |    $195.00 | None           | $255 - Autoload |
+----------------------------------------------------------------------------------------------------------------+"""
    )


def test_tabular_output_redacts_malformed_email_without_crashing():
    profile = namedtuple("Profile", "email")(email="not-an-email")

    output = tabular_output(profile, None, show_private=False)

    assert "not-an-email" not in output
    assert "***" in output


def test_tabular_output_masks_short_serial_numbers():
    cards = [
        SimpleNamespace(
            nickname="Tiny",
            serial_number="12",
            type="Adult",
            status="Active",
            products=[],
            features=[],
        )
    ]

    output = tabular_output(None, cards, show_private=False)

    assert "12" not in output
    assert "**" in output


def test_tabular_output_redacts_alternate_phone_without_private_info():
    profile = namedtuple("Profile", "alt_phone")(
        alt_phone="+1 510-555-0199",
    )

    output = tabular_output(profile, None, show_private=False)

    assert "+1 510-555-0199" not in output
    assert "+1 ***-***-0199" in output


def test_tabular_output_reports_missing_cards():
    assert tabular_output(None, []) == "No cards registered"


def test_tabular_output_puts_each_product_on_one_row_with_own_column():
    cards = [
        SimpleNamespace(
            nickname="Bridge SF Cute",
            serial_number="123456788846",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$40.00")],
            features=[],
        ),
        SimpleNamespace(
            nickname="Phone 12 Blue",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[
                SimpleNamespace(name="Cash Value", value="$244.55"),
                SimpleNamespace(name="BART", value="$1.10"),
            ],
            features=[],
        ),
        SimpleNamespace(
            nickname="Phone 15",
            serial_number="123456788937",
            type="Adult",
            status="Active",
            products=[
                SimpleNamespace(name="Cash Value", value="$237.99"),
                SimpleNamespace(name="BART", value="$52.15"),
            ],
            features=[],
        ),
    ]

    output = tabular_output(None, cards, show_private=False)

    assert (
        output
        == """+--------------------------------------------------------------------------+
| # | Name           | Serial       | Type  | Status | Cash Value | BART   |
|---+----------------+--------------+-------+--------+------------+--------|
| 1 | Phone 12 Blue  | ********8820 | Adult | Active |    $244.55 |  $1.10 |
| 2 | Phone 15       | ********8937 | Adult | Active |    $237.99 | $52.15 |
| 3 | Bridge SF Cute | ********8846 | Adult | Active |     $40.00 |        |
+--------------------------------------------------------------------------+"""
    )


def test_tabular_output_adds_a_money_column_for_each_agency_purse():
    cards = [
        SimpleNamespace(
            nickname="Phone 12 Blue",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[
                SimpleNamespace(name="Cash Value", value="$244.55"),
                SimpleNamespace(name="BART", value="$1.10"),
            ],
            features=[],
        ),
        SimpleNamespace(
            nickname="MuniTrain",
            serial_number="123456788929",
            type="Adult",
            status="Active",
            products=[
                SimpleNamespace(name="Cash Value", value="$299.60"),
                SimpleNamespace(name="Muni", value="$12.00"),
            ],
            features=[],
        ),
    ]

    output = tabular_output(None, cards, show_private=False)

    assert (
        output
        == """+---------------------------------------------------------------------------------+
| # | Name          | Serial       | Type  | Status | Cash Value | BART  | Muni   |
|---+---------------+--------------+-------+--------+------------+-------+--------|
| 1 | MuniTrain     | ********8929 | Adult | Active |    $299.60 |       | $12.00 |
| 2 | Phone 12 Blue | ********8820 | Adult | Active |    $244.55 | $1.10 |        |
+---------------------------------------------------------------------------------+"""
    )


def test_tabular_output_sorts_cards_by_cash_value_descending():
    def card(nickname, serial, cash, bart=None):
        products = [SimpleNamespace(name="Cash Value", value=cash)]
        if bart is not None:
            products.append(SimpleNamespace(name="BART", value=bart))
        return SimpleNamespace(
            nickname=nickname,
            serial_number=serial,
            type="Adult",
            status="Active",
            products=products,
            features=[],
        )

    cards = [
        card("Bridge SF Cute", "123456788846", "$40.00"),
        card("Phone 12 Blue", "123456788820", "$244.55", "$1.10"),
        card("Watch 9", "123456788838", "$165.40", "$1.40"),
        card("Ubuntu", "123456788887", "$295.00", "$1.90"),
        card("MuniTrain", "123456788929", "$299.60"),
        card("Phone 15", "123456788937", "$237.99", "$52.15"),
        card("Watch 6 Red", "123456788945", "$163.10"),
        card("Watch 5 Ti", "123456788952", "$294.75"),
    ]

    output = tabular_output(None, cards, show_private=False)
    names = [line.split("|")[2].strip() for line in output.splitlines() if line.startswith("| ") and "Name" not in line]
    assert names == [
        "MuniTrain",
        "Ubuntu",
        "Watch 5 Ti",
        "Phone 12 Blue",
        "Phone 15",
        "Watch 9",
        "Watch 6 Red",
        "Bridge SF Cute",
    ]


def test_tabular_output_keeps_missing_cash_last_and_preserves_ties():
    cards = [
        SimpleNamespace(
            nickname="Low",
            serial_number="1",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$10.00")],
            features=[],
        ),
        SimpleNamespace(
            nickname="Tied First",
            serial_number="2",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$50.00")],
            features=[],
        ),
        SimpleNamespace(
            nickname="No Cash",
            serial_number="3",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Pass", value="Muni Monthly")],
            features=[],
        ),
        SimpleNamespace(
            nickname="Tied Second",
            serial_number="4",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$50.00")],
            features=[],
        ),
    ]

    output = tabular_output(None, cards, show_private=False)
    names = [line.split("|")[2].strip() for line in output.splitlines() if line.startswith("| ") and "Name" not in line]
    assert names == ["Tied First", "Tied Second", "Low", "No Cash"]


def test_tabular_output_flattens_multiline_pass_values():
    cards = [
        SimpleNamespace(
            nickname="MuniTrain",
            serial_number="123456788929",
            type="Adult",
            status="Active",
            products=[
                SimpleNamespace(name="Cash Value", value="$299.60"),
                SimpleNamespace(name="Pass", value="Muni Monthly\n  - Expires 2026-09-01"),
            ],
            features=[],
        )
    ]

    output = tabular_output(None, cards, show_private=False)

    assert "\n  - Expires" not in output
    assert "Muni Monthly - Expires 2026-09-01" in output
    assert output.count("\n") == 4


def test_summary_json_output_keeps_dashboard_card_order():
    cards = [
        SimpleNamespace(
            nickname="Low",
            serial_number="1",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$10.00")],
            features=[],
        ),
        SimpleNamespace(
            nickname="High",
            serial_number="2",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$90.00")],
            features=[],
        ),
    ]

    output = json.loads(summary_json_output(None, cards, show_private=False))
    assert [card["nickname"] for card in output["cards"]] == ["Low", "High"]


def test_summary_json_output_renders_profile_and_cards_without_private_info():
    profile = namedtuple("Profile", "name email alt_phone")(
        name="Golden Gate Hacker",
        email="goldengate88@systemfu.com",
        alt_phone="",
    )
    cards = [
        SimpleNamespace(
            nickname="Primary, card ending in 4134",
            serial_number="2021234134",
            type="ADULT",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$195.00")],
            features=[SimpleNamespace(name="Reload", value="$255 - Autoload")],
        )
    ]

    output = json.loads(summary_json_output(profile, cards, show_private=False))

    assert output == {
        "profile": {
            "name": "Go*** Ga*** Ha***",
            "email": "g***@systemfu.com",
        },
        "cards": [
            {
                "serial_number": "******4134",
                "nickname": "Primary, card ending in 4134",
                "type": "ADULT",
                "status": "Active",
                "products": [{"name": "Cash Value", "value": "$195.00"}],
                "features": [{"name": "Reload", "value": "$255 - Autoload"}],
            }
        ],
    }


def test_column_style_bolds_headers():
    assert _column_style(color=False) == {}
    assert _column_style(color=True) == {"header_style": _HEADER_STYLE}
    assert _column_style(color=True, row_header=True) == {
        "header_style": _HEADER_STYLE,
        "style": _ROW_HEADER_STYLE,
    }


def _decoded_lines(output):
    return list(AnsiDecoder().decode(output))


def _is_bold_at(text, index):
    for span in text.spans:
        if not (span.start <= index < span.end):
            continue
        style = span.style if isinstance(span.style, Style) else Style.parse(str(span.style))
        if style.bold:
            return True
    return False


def test_tabular_output_emits_ansi_when_color_is_enabled(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    cards = [
        SimpleNamespace(
            nickname="Phone",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$244.55")],
            features=[],
        ),
        SimpleNamespace(
            nickname="Watch",
            serial_number="123456788838",
            type="Adult",
            status="Expired",
            products=[SimpleNamespace(name="Cash Value", value="$0.00")],
            features=[],
        ),
    ]

    output = tabular_output(None, cards, show_private=False, color=True)

    assert "\x1b[" in output
    assert "╭" in output
    assert "Phone" in output
    assert "Watch" in output


def test_tabular_output_bolds_column_and_row_headers(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    cards = [
        SimpleNamespace(
            nickname="Phone",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$244.55")],
            features=[],
        )
    ]

    output = tabular_output(None, cards, show_private=False, color=True)
    lines = _decoded_lines(output)
    header = next(line for line in lines if "Name" in line.plain and "Serial" in line.plain)
    row = next(line for line in lines if "Phone" in line.plain)

    assert _is_bold_at(header, header.plain.find("#"))
    assert _is_bold_at(header, header.plain.find("Name"))
    assert _is_bold_at(row, row.plain.find("Phone"))
    assert _is_bold_at(row, row.plain.find("1"))


def test_tabular_output_stays_plain_ascii_by_default():
    cards = [
        SimpleNamespace(
            nickname="Phone",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$244.55")],
            features=[],
        )
    ]

    output = tabular_output(None, cards, show_private=False)

    assert "\x1b[" not in output
    assert "╭" not in output
    assert output.startswith("+")


def test_tabular_output_respects_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    cards = [
        SimpleNamespace(
            nickname="Phone",
            serial_number="123456788820",
            type="Adult",
            status="Active",
            products=[SimpleNamespace(name="Cash Value", value="$244.55")],
            features=[],
        )
    ]

    output = tabular_output(None, cards, show_private=False, color=True)

    assert "\x1b[" not in output
    assert output.startswith("+")
