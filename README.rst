.. image:: ./logo.png
===========================

.. image:: https://badge.fury.io/py/clippercard.png
    :target: http://badge.fury.io/py/clippercard

.. image:: https://pypip.in/d/clippercard/badge.png
        :target: https://crate.io/packages/clippercard/
        
.. image:: https://pypip.in/license/vxapi/badge.png
        :target: ./LICENSE.txt

``clippercard`` is an unofficial web API to clippercard.com, written in Python.

Not only is the `clippercard web site <https://www.clippercard.com>`_ a total UX/UI disaster, its behind-the-scene's HTML structure and HTTP protocol is a complete exercise in palmface. This library aims to provide an unofficial but sensible interface to the official web service.

Features
--------

- Profile Data
- Multiple cards' data
- For each card, multiple products and balances

I don't have access to all products loadable on the ClipperCard, so transit agency support is limtied to what I personally use for now. If you'd like me to add support for your product, send me the page source from your `account home page <https://www.clippercard.com/ClipperCard/dashboard.jsf>`_

Installation
------------

To install clippercard, simply:

.. code-block:: bash

    $ pip install clippercard

Usage
-----

.. code-block:: python

    import clippercard
    session = clippercard.Session(<username>, <password>)
    print(session.user_profile)
    for c in session.cards:
        print(c)


.. code-block: bash

    $ clippercard -h # see usage information

    $ clippercard summary

    Name: ANTHONY WU
    Email: anthonywu@example.com
    Phone: 415-555-5555
    Address: 1 Main St San Francisco, CA 94103
    ----------------------------------------
    Card 1: 1234567890 "Golden Gate Bridge Limited Edition" (ADULT - Active)
      - BART HVD 60/64: $47.55
      - Cash value: $51.40
    Card 2: 1234567891 "Bay Bridge Limited Edition" (ADULT - Active)
      - Cash value: $2.35


If you wish to use clippercard without specifying username/password on the CLI, create a file ``~/.clippercardrc`` with this format::

    [default]
    username = <replace_with_your_email>
    password = <replace_with_your_password>

You may toggle accounts via the ``--account`` flag on the command line to access one of several configs in the file::

    [default]
    username = <replace_with_your_email>
    password = <replace_with_your_password>
    
    [wife]
    username = <replace_with_login_email>
    password = <replace_with_login_password>
    
The ``wife`` credentials can then be accessed via::

    $ clippercard summary --account=wife

Contribute
----------

#. Fork the repo, make your changes, add adequate tests, and send me a pull request.
