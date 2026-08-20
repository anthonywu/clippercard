import json
from collections import namedtuple
from types import SimpleNamespace

from clippercard.porcelain import summary_json_output, tabular_output


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
| 1 | Bridge SF Cute | ********8846 | Adult | Active |     $40.00 |        |
| 2 | Phone 12 Blue  | ********8820 | Adult | Active |    $244.55 |  $1.10 |
| 3 | Phone 15       | ********8937 | Adult | Active |    $237.99 | $52.15 |
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
| 1 | Phone 12 Blue | ********8820 | Adult | Active |    $244.55 | $1.10 |        |
| 2 | MuniTrain     | ********8929 | Adult | Active |    $299.60 |       | $12.00 |
+---------------------------------------------------------------------------------+"""
    )


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
