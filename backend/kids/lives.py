"""The life rules, as pure functions of (stored lives, the time they were last brought up to date, now). No SQL, no clock.

Stored: `lives` (0..MAX_LIVES) and `anchor`, the moment regeneration is counted from. Lives come back one per LIFE_REGEN_SECONDS
since the anchor, up to MAX_LIVES. The remainder of a partly elapsed interval is kept (the anchor moves forward by whole
intervals only), so checking often never speeds up or slows down regeneration. Time going backwards counts as no time passing."""
from datetime import datetime, timedelta

from .. import settings

TIME = "%Y-%m-%d %H:%M:%S"


def parse(text):
    return datetime.strptime(text, TIME)


def fmt(moment):
    return moment.strftime(TIME)


def effective(lives, anchor, now):
    """-> (lives_now, new_anchor, seconds_until_next_life or None when full). Never outside 0..MAX_LIVES."""
    lives = max(0, min(settings.MAX_LIVES, lives))
    if lives >= settings.MAX_LIVES:
        return settings.MAX_LIVES, now, None
    elapsed = max(0, int((now - anchor).total_seconds()))
    gained = elapsed // settings.LIFE_REGEN_SECONDS
    lives = min(settings.MAX_LIVES, lives + gained)
    if lives >= settings.MAX_LIVES:
        return settings.MAX_LIVES, now, None
    anchor = anchor + timedelta(seconds=gained * settings.LIFE_REGEN_SECONDS)
    since = max(0, int((now - anchor).total_seconds()))
    return lives, anchor, settings.LIFE_REGEN_SECONDS - since
