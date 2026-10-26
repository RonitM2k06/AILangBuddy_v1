"""The admin audit service. Every change an admin makes to content is recorded here, in the same transaction as the change.

Rules this module enforces (and tests/test_admin_audit.py proves):
  * the actor is the authenticated session's user object. There is no parameter through which a request body could name one;
  * the metadata is an allow-list of safe keys with strictly typed values: revisions, field NAMES, finding CODES, statuses. Anything else
    is refused, so answer text, learner content, tutor messages, transcripts, tokens and keys cannot be logged by accident;
  * record() writes on the caller's connection, so a failed audit insert rolls the content change back with it;
  * a rejected publish is recorded by record_rejected() on its own connection, after the change has already been rolled back."""
import json

from ..db import connect
from ..repositories import admin_audit
from .codes import FIELD_NAMES, FINDING_CODES

ACTIONS = ("create", "update", "publish", "unpublish", "archive", "restore", "validation_failed", "config_change", "login_denied")
ENTITY_TYPES = ("lesson", "exercise", "lesson_vocabulary", "situation", "situation_step", "listening_activity", "listening_option",
                "vocabulary", "vocabulary_translation", "topic", "admin_access", "config")
STATUSES = ("draft", "published", "archived")
MAX_LIST = 50


class AuditError(ValueError):
    """The event itself is malformed. This is a programming error, never a user error, and it aborts the change."""


def _members_of(allowed, what):
    """A list drawn from a closed vocabulary. 'Looks like an identifier' is not enough: a secret can look like one."""
    def check(value):
        if not isinstance(value, (list, tuple)) or len(value) > MAX_LIST or not all(isinstance(v, str) and v in allowed for v in value):
            raise AuditError(f"{what} must be a list of known names")
        return sorted(set(value))
    return check


def _revision(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuditError("a revision is a non-negative integer")
    return value


def _status(value):
    if value not in STATUSES:
        raise AuditError("unknown status")
    return value


_META = {"revision_before": _revision, "revision_after": _revision, "changed_fields": _members_of(FIELD_NAMES, "changed_fields"),
         "finding_codes": _members_of(FINDING_CODES, "finding_codes"),
         "status_before": _status, "status_after": _status}


def clean_meta(meta):
    meta = meta or {}
    unknown = set(meta) - set(_META)
    if unknown:
        raise AuditError(f"metadata key not allowed: {sorted(unknown)[0]}")
    return {k: _META[k](v) for k, v in meta.items()}


def record(conn, actor, action, entity_type, entity_id=None, entity_key=None, meta=None, outcome="ok", request_id=None):
    """Write one event on `conn` (the caller's transaction). `actor` is the session's User."""
    if action not in ACTIONS or entity_type not in ENTITY_TYPES or outcome not in ("ok", "rejected"):
        raise AuditError("unknown action, entity type or outcome")
    if getattr(actor, "id", None) is None or not getattr(actor, "handle", None):
        raise AuditError("the actor must be the authenticated user")
    meta_json = json.dumps(clean_meta(meta), sort_keys=True, separators=(",", ":"))
    return admin_audit.insert(conn, actor.id, actor.handle, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id)


def record_rejected(db_path, actor, action, entity_type, entity_id=None, entity_key=None, meta=None, request_id=None):
    """A refused request (e.g. a publish that failed validation), recorded on its own connection once the change has been rolled back."""
    with connect(db_path) as conn:
        return record(conn, actor, action, entity_type, entity_id, entity_key, meta, "rejected", request_id)


def _view(row):
    return {"id": row["id"], "occurred_at": row["occurred_at"], "actor": row["actor_label"], "action": row["action"],
            "entity_type": row["entity_type"], "entity_id": row["entity_id"], "entity_key": row["entity_key"], "outcome": row["outcome"],
            "meta": json.loads(row["meta_json"]), "request_id": row["request_id"]}


def list_events(db_path, filters, limit, offset):
    with connect(db_path) as conn:
        total = admin_audit.count(conn, filters)
        return total, [_view(r) for r in admin_audit.list_events(conn, filters, limit, offset)]


def get_event(db_path, event_id):
    with connect(db_path) as conn:
        row = admin_audit.get(conn, event_id)
    return _view(row) if row else None
