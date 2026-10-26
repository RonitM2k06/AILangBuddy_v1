"""Service-level input rules shared by every CMS write: text hygiene, slugs, reference lookups, answer shapes. These run on every write (the publish
validators then re-check the stored result). They raise InvalidInput (422) tied to one field, or Conflict (409) when the content's state refuses."""
from datetime import datetime, timezone

from .. import settings
from ..textnorm import normalize
from .errors import Conflict, InvalidInput
from .validators import MAX_SLUG, SLUG, has_control_characters

MAX_ANSWERS = 8
MAX_ACCEPTED = 10
MAX_ANSWER_CHARS = 200


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_text(field, value, max_len, *, required=True, multiline=False):
    """Trimmed text, or None for an optional blank. Rejects control characters (a newline is allowed only in multi-line prose) and over-long text."""
    if value is None:
        if required:
            raise InvalidInput(field, "is required")
        return None
    if not isinstance(value, str):
        raise InvalidInput(field, "must be text")
    value = value.strip()
    if not value:
        if required:
            raise InvalidInput(field, "must not be blank")
        return None
    if len(value) > max_len:
        raise InvalidInput(field, f"must be at most {max_len} characters")
    if has_control_characters(value, multiline):
        raise InvalidInput(field, "must not contain control characters")
    return value


def clean_slug(field, value):
    if not isinstance(value, str) or len(value) > MAX_SLUG or not SLUG.match(value):
        raise InvalidInput(field, "use lowercase letters and digits separated by single hyphens (60 characters at most)")
    return value


def clean_difficulty(field, value, high):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
        raise InvalidInput(field, f"must be between 1 and {high}")
    return value


def language_id(repo, conn, code, field="language"):
    row = repo.language_by_code(conn, code)
    if row is None:
        raise InvalidInput(field, "Unknown language")
    return row["id"]


def check_level(repo, conn, language_id_, cefr, field="cefr"):
    if not repo.level_exists(conn, language_id_, cefr):
        raise InvalidInput(field, f"{cefr} is not available for this language")


def age_group_ids(repo, conn, codes, field="age_groups"):
    if len(set(codes)) != len(codes):
        raise InvalidInput(field, "the same age group is listed more than once")
    ids = []
    for code in codes:
        gid = repo.age_group_id(conn, code)
        if gid is None:
            raise InvalidInput(field, f"Unknown age group: {code}")
        ids.append(gid)
    return ids


def topic_ids(repo, conn, slugs, field="topics"):
    if len(set(slugs)) != len(slugs):
        raise InvalidInput(field, "the same topic is listed more than once")
    ids = []
    for slug in slugs:
        tid = repo.topic_id(conn, slug)
        if tid is None:
            raise InvalidInput(field, f"Unknown topic: {slug}")
        ids.append(tid)
    return ids


def vocabulary_item(repo, conn, item_id, language_id_, field="item_id"):
    """The item must exist and be in the unit's own language (vocabulary language consistency)."""
    item = repo.vocabulary_row(conn, item_id)
    if item is None:
        raise InvalidInput(field, "Unknown vocabulary item")
    if item["language_id"] != language_id_:
        raise InvalidInput(field, "The vocabulary item is in a different language than this content")
    return item


def ensure_draft(row, what):
    if row["status"] != "draft":
        raise Conflict("not_draft", f"This {what} is {row['status']}: " + ("unpublish it" if row["status"] == "published" else "restore it") + " to a draft before editing.")


def clean_answers(field, answers, shape):
    """shape: 'choose' (exactly one correct among 2+), 'typed' (1+ accepted answers, all accepted), 'none' (learn_phrase: no answers).
    Returns [{id, text, is_correct}] with trimmed text. Duplicates are judged the way the graders judge them (case/punctuation ignored)."""
    if shape == "none":
        if answers:
            raise InvalidInput(field, "this kind of step has no answers")
        return []
    out = []
    for a in answers:
        out.append({"id": a.id, "text": clean_text(field, a.text, MAX_ANSWER_CHARS), "is_correct": bool(a.is_correct)})
    if shape == "choose":
        if not 2 <= len(out) <= MAX_ANSWERS:
            raise InvalidInput(field, f"needs between 2 and {MAX_ANSWERS} answers")
        if sum(a["is_correct"] for a in out) != 1:
            raise InvalidInput(field, "exactly one answer must be correct")
    else:
        if not 1 <= len(out) <= MAX_ACCEPTED:
            raise InvalidInput(field, f"needs between 1 and {MAX_ACCEPTED} accepted answers")
        if not all(a["is_correct"] for a in out):
            raise InvalidInput(field, "a typed answer list holds accepted answers only")
    if len({normalize(a["text"]) for a in out}) != len(out):
        raise InvalidInput(field, "two answers are the same once case and punctuation are ignored")
    ids = [a["id"] for a in out if a["id"] is not None]
    if len(set(ids)) != len(ids):
        raise InvalidInput(field, "an answer id is used twice")
    return out


def changed(before, after, fields):
    """The names of the fields whose value actually differs (names only, never values: they go into the audit event)."""
    return [f for f in fields if before.get(f) != after.get(f)]


LISTENING_OPTIONS = settings.LISTENING_OPTION_COUNT
