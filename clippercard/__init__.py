"""Unofficial Python client for clippercard.com."""

from importlib.metadata import PackageNotFoundError, version

import clippercard.client as client

Session = client.ClipperCardWebSession

try:
    __version__ = version("clippercard")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
