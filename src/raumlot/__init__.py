"""Raumlot package metadata."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("raumlot")
except PackageNotFoundError:
    __version__ = "0.1.0"
