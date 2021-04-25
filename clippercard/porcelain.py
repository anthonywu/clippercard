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

import prettytable


def tabular_output(user_profile, cards):
    """
    Pretty prints a user profile and its associated cards and products.
    """
    profile_table = prettytable.PrettyTable(["name", "value"], header=False)
    profile_table.align["name"] = "r"
    profile_table.align["value"] = "l"
    for label, value in user_profile._asdict().items():
        profile_table.add_row([label, value])

    if cards:
        card_table = prettytable.PrettyTable(
            ["#", "Name", "Serial", "Type", "Status", "Products"]
        )
        for col in card_table.align.keys():
            card_table.align[col] = "l"
        for i, card in enumerate(cards, 1):
            card_table.add_row(
                [
                    i,
                    card.nickname,
                    card.serial_number,
                    card.type,
                    card.status,
                    "\n".join((str(_) for _ in card.products + card.features)),
                ]
            )
    else:
        card_table = None

    output = "\n".join(
        [
            profile_table.get_string(),
            card_table.get_string() if card_table else "No cards registered",
        ]
    )
    return output
