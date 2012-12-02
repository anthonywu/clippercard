================
Clipper Card API
================

This module provides an interface to check Clipper Card account information and get card balances.

    session = ClipperCardWebSession()
    auth = {'username': 'your-username', 'password': 'your-password'}
    login_resp = session.login(**auth)
    acct_data = parse_acct_content(login_resp.content)
    print "Cardholder: %(Cardholder)s %(Email)s %(Address)s %(Phone)s" % acct_data.personal_details
    for card in acct_data.cards:
        balances = balance_lookup[card.serial_number]
        for b in balances:
            print b.product, b.valid_for

For thorough documentation, see included docs/clippercard.html
