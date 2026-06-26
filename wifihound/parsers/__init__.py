"""Parser package — importing it registers all built-in parsers."""

from wifihound.parsers.base import (  # noqa: F401
    Parser,
    all_parsers,
    detect_parser,
    get,
    register,
)

# Importing the modules runs their register() calls.
from wifihound.parsers import airodump_csv  # noqa: F401,E402

__all__ = ["Parser", "all_parsers", "detect_parser", "get", "register"]
