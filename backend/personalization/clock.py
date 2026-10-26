"""Time source for personalization (a module so tests can replace it)."""
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
