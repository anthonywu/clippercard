"""Unofficial Python client for clippercard.com."""

from importlib.metadata import PackageNotFoundError, version

from clippercard.client import ClipperCardAuthError, ClipperCardError, ClipperCardWebSession
from clippercard.parser import Card, CardFeature, CardProduct, Profile

Session = ClipperCardWebSession

try:
    __version__ = version("clippercard")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "Card",
    "CardFeature",
    "CardProduct",
    "ClipperCardAuthError",
    "ClipperCardError",
    "Profile",
    "Session",
    "__version__",
]
