"""Retail Search V2 demo package.

The package is intentionally split into small reusable modules so pieces can be
published independently later.
"""

from .app import create_app

__all__ = ["create_app"]
