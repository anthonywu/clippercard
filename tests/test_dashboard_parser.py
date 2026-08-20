"""Tests for dashboard HTML parsing.

These tests use a snapshot of the dashboard page after login.
They do not test the actual login flow because CSRF tokens are time-sensitive
and the snapshot token would be stale.

To test real login, run: uv run clippercard summary
"""

from pathlib import Path

import pytest

from clippercard import parser


@pytest.fixture
def dashboard_html():
    test_file = Path(__file__).parent / "data" / "dashboard.html"
    return test_file.read_text(encoding="utf-8")


def test_parse_returns_multiple_cards(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    assert len(result) == 8


def test_parse_card_nickname_first_card(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    assert result[0].nickname == "Sample Card 1"
    assert result[1].nickname == "Sample Card 2"


def test_parse_cash_value_phone_card(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    phone_card = result[1]
    cash_products = [p for p in phone_card.products if p.name == "Cash Value"]
    assert len(cash_products) == 1
    assert cash_products[0].value == "$258.40"


def test_parse_bart_value_phone_card(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    phone_card = result[1]
    bart_products = [p for p in phone_card.products if p.name == "BART"]
    assert len(bart_products) == 1
    assert bart_products[0].value == "$1.25"


def test_parse_card_without_bart(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    first_card = result[0]
    bart_products = [p for p in first_card.products if p.name == "BART"]
    assert len(bart_products) == 0
    cash_products = [p for p in first_card.products if p.name == "Cash Value"]
    assert len(cash_products) == 1
    assert cash_products[0].value == "$41.75"


def test_parse_with_pass_list(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    first_card = result[0]
    pass_products = [p for p in first_card.products if p.name == "Pass"]
    assert len(pass_products) == 1
    assert "VTA Standard Pass" in pass_products[0].value
    assert "Expires 2026-05-01" in pass_products[0].value


def test_parse_serial_numbers(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    assert result[0].serial_number == "100000111111"
    assert result[1].serial_number == "100000111129"


def test_parse_rider_class(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    assert result[0].type == "Adult"
    assert result[1].type == "Adult"


def test_products_from_purses_includes_other_agencies():
    account = {
        "purseList": [
            {
                "balance": 4000,
                "purseRestriction": "Unrestricted",
                "purseName": "Unrestricted",
            },
            {
                "balance": 110,
                "purseRestriction": "OperatorRestricted",
                "description": "BART",
                "purseName": "BART HVD Purse",
            },
            {
                "balance": 525,
                "purseRestriction": "OperatorRestricted",
                "description": "Muni",
                "purseName": "Muni HVD Purse",
            },
        ]
    }

    products = parser._products_from_purses(account)

    assert [(product.name, product.value) for product in products] == [
        ("Cash Value", "$40.00"),
        ("BART", "$1.10"),
        ("Muni", "$5.25"),
    ]


def test_products_from_purses_falls_back_to_convenience_fields():
    account = {
        "cashPurse": {"balance": 19500},
        "bartPurse": {"balance": 110},
    }

    products = parser._products_from_purses(account)

    assert [(product.name, product.value) for product in products] == [
        ("Cash Value", "$195.00"),
        ("BART", "$1.10"),
    ]


def test_cents_to_dollars_formats_from_integer_cents():
    assert parser._cents_to_dollars(None) is None
    assert parser._cents_to_dollars(0) == "$0.00"
    assert parser._cents_to_dollars(1) == "$0.01"
    assert parser._cents_to_dollars(110) == "$1.10"
    assert parser._cents_to_dollars(-255) == "-$2.55"


def test_purse_display_name_strips_hvd_suffix_without_description():
    assert (
        parser._purse_display_name(
            {
                "purseRestriction": "OperatorRestricted",
                "purseName": "Caltrain HVD Purse",
            }
        )
        == "Caltrain"
    )


def test_all_required_fields(dashboard_html):
    result = parser.parse_dashboard_cards(dashboard_html)
    for card in result:
        assert card.serial_number is not None
        assert card.nickname is not None
        assert isinstance(card.products, list)
        assert isinstance(card.features, list)
        assert card.type is not None
        assert card.status is not None
