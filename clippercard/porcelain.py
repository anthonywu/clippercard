"""
Copyright (c) 2012-2017 (https://github.com/clippercard/clippercard-python)

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
import six


def tabular_output(user_profile, cards):
    """
    Pretty prints a user profile and its associated cards and products.
    """
    pt = prettytable.PrettyTable(['name', 'value'], header=False)
    pt.align['name'] = 'r'
    pt.align['value'] = 'l'
    for k, v in six.iteritems(user_profile._asdict()):
        pt.add_row([k, v])

    ct = prettytable.PrettyTable(['Card', 'Serial', 'Type', 'Status', 'Product', 'Value'])
    for col in ct.align.keys():
        ct.align[col] = 'l'
    for c in cards:
        for p in c.products:
            ct.add_row([
                c.nickname,
                c.serial_number,
                c.type,
                c.status,
                p.name,
                p.value
                ])

    output = '\n'.join([pt.get_string(), ct.get_string()])
    return output
