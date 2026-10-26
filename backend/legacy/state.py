"""Rules for the legacy prototype state (one JSON blob per signed-in user). No HTTP and no SQL in here.

The blob is written by the user's own browser, but it is rendered back into HTML by the legacy frontend, so it is treated as untrusted:
  * it must be a JSON object of the shape the frontend writes (engine.js DEMO()): known keys only, each with its expected type;
  * the version must be exactly LEGACY_STATE_VERSION;
  * the size limit is checked on the raw body by the caller, before parsing (nothing is ever truncated).
A key may be missing (the frontend fills it from its defaults); an unknown key, a wrong type or an out-of-range number is refused."""
import json
import math
import re

from .. import settings

_SLUG = re.compile(r"^[a-z0-9-]{1,32}$")
_CODE = re.compile(r"^[a-z-]{2,16}$")
_PACK = re.compile(r"^[a-z0-9-]{1,32}(:[a-z-]{2,16})?$")   # a pack's progress key: a city ("mumbai") or city:language ("mumbai:mr")
_MAX_PACKS = 20
_MAX_TUTOR_MESSAGES = 100
_MAX_LIST = 50
_MAX_MAP = 500
_SRS_FIELDS = frozenset({"ease", "interval", "reps", "due"})
_PLACEMENT_FIELDS = frozenset({"score", "at"})


class InvalidState(ValueError):
    """The body is not a legacy state the frontend could have written. `field` names where it went wrong."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v):
    return (_is_int(v) or isinstance(v, float)) and math.isfinite(v)


def _text(field, v, limit, pattern=None):
    if not isinstance(v, str) or len(v) > limit or (pattern is not None and not pattern.match(v)):
        raise InvalidState(field, f"{field} must be a short text value")


def _count(field, v):
    if not _is_int(v) or v < 0:
        raise InvalidState(field, f"{field} must be a whole number of at least 0")


def _percentages(field, v, key_limit=32, max_items=_MAX_MAP):
    if not isinstance(v, dict) or len(v) > max_items:
        raise InvalidState(field, f"{field} must be an object")
    for key, value in v.items():
        if len(key) > key_limit or not _is_number(value) or not 0 <= value <= 100:
            raise InvalidState(field, f"{field} values must be numbers from 0 to 100")


def _completed_days(field, v):
    if not isinstance(v, list) or len(v) > _MAX_LIST or not all(_is_int(d) and d >= 0 for d in v):
        raise InvalidState(field, f"{field} must be a list of day numbers")


def _pack_days(field, v):
    """Days completed in each pack other than Delhi's (engine.js daysDone): {pack key: [day numbers]}."""
    if not isinstance(v, dict) or len(v) > _MAX_PACKS:
        raise InvalidState(field, f"{field} must be an object")
    for key, days in v.items():
        if not _PACK.match(key):
            raise InvalidState(field, f"{field} keys must be pack names")
        _completed_days(field, days)


def _achievements(field, v):
    if not isinstance(v, list) or len(v) > _MAX_LIST or not all(isinstance(a, str) and len(a) <= 32 for a in v):
        raise InvalidState(field, f"{field} must be a list of short names")


def _srs(field, v):
    if not isinstance(v, dict) or len(v) > _MAX_MAP:
        raise InvalidState(field, f"{field} must be an object")
    for key, card in v.items():
        if len(key) > 32 or not isinstance(card, dict) or not set(card) <= _SRS_FIELDS or not all(_is_number(x) for x in card.values()):
            raise InvalidState(field, f"{field} entries must be review records")


def _placement(field, v):
    if v is None:
        return
    if not isinstance(v, dict) or not set(v) <= _PLACEMENT_FIELDS or not all(_is_number(x) for x in v.values()):
        raise InvalidState(field, f"{field} must be null or a placement result")


def _tutor(field, v):
    if not isinstance(v, list) or len(v) > _MAX_TUTOR_MESSAGES or not all(isinstance(m, dict) for m in v):
        raise InvalidState(field, f"{field} must be a list of messages")


def _rules(levels):
    def level(field, v):
        if v not in levels:
            raise InvalidState(field, f"{field} must be a CEFR level code")

    return {
        "name": lambda f, v: _text(f, v, 60),
        "city": lambda f, v: _text(f, v, 32, _SLUG),
        "language": lambda f, v: _text(f, v, 16, _CODE),
        "level": level,
        "confidence": _percentages,
        "skills": _percentages,
        "practiced": lambda f, v: _percentages(f, v, key_limit=200),
        "completedDays": _completed_days,
        "packDays": _pack_days,
        "xp": _count,
        "streak": _count,
        "roleplays": _count,
        "lastActive": lambda f, v: _text(f, v, 40),
        "srs": _srs,
        "placement": _placement,
        "tutor": _tutor,
        "achievements": _achievements,
    }


def parse(raw: bytes, levels, city_languages=None) -> dict:
    """Decode and validate a state body. `levels` is the set of valid CEFR codes; `city_languages` maps each catalogue city's slug to the
    language codes it offers. Raises InvalidState; returns the state."""
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as exc:          # UnicodeDecodeError is a ValueError; absurd nesting is a RecursionError
        raise InvalidState("body", "The state must be valid JSON") from exc
    if not isinstance(data, dict):
        raise InvalidState("body", "The state must be a JSON object")
    version = data.get("v")
    if not _is_int(version) or version != settings.LEGACY_STATE_VERSION:
        raise InvalidState("v", f"v must be {settings.LEGACY_STATE_VERSION}")
    rules = _rules(frozenset(levels))
    for key, value in data.items():
        if key == "v":
            continue
        rule = rules.get(key)
        if rule is None:
            raise InvalidState(key, f"Unknown state field: {key[:40]}")
        rule(key, value)
    # a catalogue city is learnt only in a language it offers (Delhi is never "in Marathi"); the frontend repairs an old pair before saving
    offered = (city_languages or {}).get(data.get("city"))
    if offered is not None and "language" in data and data["language"] not in offered:
        raise InvalidState("language", "language is not offered for this city")
    return data
