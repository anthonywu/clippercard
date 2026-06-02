"""Tests for dashboard HTML parsing

NOTE: These tests use a snapshot of the dashboard page after login.
They do NOT test the actual login flow because CSRF tokens are time-sensitive
and the snapshot token would be stale.

To test real login, run: uv run clippercard summary
And provide credentials when prompted.
"""

import pathlib

import pytest

from clippercard import parser


@pytest.fixture
def dashboard_html():
    """Load the dashboard.html test file"""
    test_file = pathlib.Path(__file__).parent / "data" / "dashboard.html"
    return test_file.read_text()


class TestDashboardCardParsing:
    """Test parsing of card data from dashboard HTML"""

    def test_parse_returns_multiple_cards(self, dashboard_html):
        """Should parse multiple cards from dashboard"""
        result = parser.parse_dashboard_cards(dashboard_html)
        assert len(result) == 8

    def test_parse_card_nickname_first_card(self, dashboard_html):
        """Extract card nickname from dashboard"""
        result = parser.parse_dashboard_cards(dashboard_html)
        assert result[0].nickname == "Sample Card 1"
        assert result[1].nickname == "Sample Card 2"

    def test_parse_cash_value_phone_card(self, dashboard_html):
        """Extract Cash Value purse balance for Sample Card 2"""
        result = parser.parse_dashboard_cards(dashboard_html)
        # Second card is "Sample Card 2"
        phone_card = result[1]
        cash_products = [p for p in phone_card.products if p.name == "Cash Value"]
        assert len(cash_products) == 1
        assert cash_products[0].value == "$258.40"

    def test_parse_bart_value_phone_card(self, dashboard_html):
        """Extract BART purse balance for Sample Card 2"""
        result = parser.parse_dashboard_cards(dashboard_html)
        # Second card "Sample Card 2" has a BART purse
        phone_card = result[1]
        bart_products = [p for p in phone_card.products if p.name == "BART"]
        assert len(bart_products) == 1
        assert bart_products[0].value == "$1.25"

    def test_parse_card_without_bart(self, dashboard_html):
        """Card without BART purse should not have BART product"""
        result = parser.parse_dashboard_cards(dashboard_html)
        # First card "Sample Card 1" doesn't have BART purse (bartPurse: null)
        first_card = result[0]
        bart_products = [p for p in first_card.products if p.name == "BART"]
        assert len(bart_products) == 0
        # But should have Cash Value
        cash_products = [p for p in first_card.products if p.name == "Cash Value"]
        assert len(cash_products) == 1
        assert cash_products[0].value == "$41.75"

    def test_parse_with_pass_list(self, dashboard_html):
        """Card with passList should have products for each pass"""
        result = parser.parse_dashboard_cards(dashboard_html)
        # First card "Sample Card 1" has a passList with 1 pass
        first_card = result[0]
        pass_products = [p for p in first_card.products if p.name == "Pass"]
        assert len(pass_products) == 1
        assert "VTA Standard Pass" in pass_products[0].value
        assert "Expires 2026-05-01" in pass_products[0].value

    def test_parse_serial_numbers(self, dashboard_html):
        """Verify serial numbers are parsed"""
        result = parser.parse_dashboard_cards(dashboard_html)
        assert result[0].serial_number == "100000111111"
        assert result[1].serial_number == "100000111129"

    def test_parse_rider_class(self, dashboard_html):
        """Verify rider class (card type) is parsed"""
        result = parser.parse_dashboard_cards(dashboard_html)
        # Most cards should be Adult
        assert result[0].type == "Adult"
        assert result[1].type == "Adult"

    def test_all_required_fields(self, dashboard_html):
        """Verify all Card fields are populated"""
        result = parser.parse_dashboard_cards(dashboard_html)
        for card in result:
            assert card.serial_number is not None
            assert card.nickname is not None
            assert isinstance(card.products, list)
            assert isinstance(card.features, list)
            assert card.type is not None
            assert card.status is not None
