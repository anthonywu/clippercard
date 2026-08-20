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

from pathlib import Path

import clippercard.parser as parser

DATA_DIR = Path(__file__).parent / "data"


def test_profile_page():
    parsed_profile = parser.parse_profile_page((DATA_DIR / "profile.html").read_text())
    assert parsed_profile.name == "EXAMPLE RIDER"
    assert parsed_profile.email == "rider@example.com"
    assert parsed_profile.mailing_address == "123 SAMPLE ST APT 4 EXAMPLE CITY, CA 94105"
    assert parsed_profile.phone == "+1 415-555-0100"
    assert parsed_profile.alt_phone == "+1 510-555-0199"
    assert parsed_profile.primary_payment == ""
    assert parsed_profile.backup_payment == ""
