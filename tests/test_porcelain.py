from collections import namedtuple
from types import SimpleNamespace

from clippercard.porcelain import tabular_output


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
+---------------------------------------------------------------------------------------+
| # | Name                      | Serial     | Type  | Status | Products                |
|---+---------------------------+------------+-------+--------+-------------------------|
| 1 | Primary, card #2021234134 | 2021234134 | ADULT | Active | Cash Value: $195.00     |
|   |                           |            |       |        | Current Passes: None    |
|   |                           |            |       |        | Reload: $255 - Autoload |
+---------------------------------------------------------------------------------------+"""
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
+------------------------------------------------------------------------------------------+
| # | Name                         | Serial     | Type  | Status | Products                |
|---+------------------------------+------------+-------+--------+-------------------------|
| 1 | Primary, card ending in 4134 | ******4134 | ADULT | Active | Cash Value: $195.00     |
|   |                              |            |       |        | Current Passes: None    |
|   |                              |            |       |        | Reload: $255 - Autoload |
+------------------------------------------------------------------------------------------+"""
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
