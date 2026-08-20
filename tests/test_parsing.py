from pathlib import Path

import clippercard.parser as parser

DATA_DIR = Path(__file__).parent / "data"


def test_profile_page():
    parsed_profile = parser.parse_profile_page((DATA_DIR / "profile.html").read_text(encoding="utf-8"))
    assert parsed_profile.name == "EXAMPLE RIDER"
    assert parsed_profile.email == "rider@example.com"
    assert parsed_profile.mailing_address == "123 SAMPLE ST APT 4 EXAMPLE CITY, CA 94105"
    assert parsed_profile.phone == "+1 415-555-0100"
    assert parsed_profile.alt_phone == "+1 510-555-0199"
    assert parsed_profile.primary_payment == ""
    assert parsed_profile.backup_payment == ""
