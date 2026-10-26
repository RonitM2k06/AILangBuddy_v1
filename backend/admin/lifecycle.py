"""The content lifecycle: draft -> published -> archived, with the only transitions the design allows.

    publish    draft     -> published   (validated, in the same transaction as the change)
    unpublish  published -> draft
    archive    draft or published -> archived
    restore    archived  -> draft       (an archived item is NEVER published directly: restore, then publish again through validation)

Every transition needs the caller's current `revision` and bumps it (so a page opened before the change cannot act on the old state). Publishing is
the only one that can be refused for its content: the validators run on the stored rows inside the transaction, an error finding rolls everything
back (422 with the findings), and the refusal is recorded as a `validation_failed` event after the rollback. Nothing here touches learner evidence:
a learner's progress, attempts and history stay exactly as they were, whatever the status."""
from ..db import connect
from ..repositories import admin_content as repo
from . import audit, rules, validation, validators
from .errors import Conflict, NotFound, ValidationFailed

TRANSITIONS = {
    "publish": (("draft",), "published"),
    "unpublish": (("published",), "draft"),
    "archive": (("draft", "published"), "archived"),
    "restore": (("archived",), "draft"),
}
HINT = {"publish": {"archived": "Restore it to a draft first, then publish it again (it is validated again)."},
        "unpublish": {"draft": "It is already a draft.", "archived": "It is archived: restore it instead."},
        "archive": {"archived": "It is already archived."}, "restore": {"draft": "Only an archived item can be restored.", "published": "Only an archived item can be restored."}}


def transition(db_path, actor, rid, action, entity_type, entity_id, revision):
    allowed, target = TRANSITIONS[action]
    key = errors_ = row = None
    try:
        with connect(db_path) as conn:
            row = repo.unit_row(conn, entity_type, entity_id)
            if row is None:
                raise NotFound()
            key = row["slug"]
            if row["status"] not in allowed:
                hint = HINT[action].get(row["status"], f"It is {row['status']}.")
                raise Conflict("invalid_transition", f"A {row['status']} {entity_type.replace('_', ' ')} cannot be {action}ed. {hint}")
            if row["revision"] != revision:
                raise Conflict("stale_revision", f"This {entity_type.replace('_', ' ')} changed since you opened it (it is now revision {row['revision']}). Reload and try again.", current_revision=row["revision"])
            warnings = []
            if action == "publish":
                findings, _ = validation.findings_for(conn, entity_type, entity_id)
                errors_ = validators.errors(findings)
                if errors_:
                    raise ValidationFailed(findings)
                warnings = [f for f in findings if f["severity"] == "warning"]
            now = rules.now()
            new_revision = repo.bump(conn, entity_type, entity_id, revision, now)
            if new_revision is None:
                raise Conflict("stale_revision", "This item was changed by someone else a moment ago. Reload and try again.")
            repo.set_status(conn, entity_type, entity_id, target, now)
            audit.record(conn, actor, action, entity_type, entity_id, key,
                         {"revision_before": revision, "revision_after": new_revision, "status_before": row["status"], "status_after": target}, request_id=rid)
            after = repo.unit_row(conn, entity_type, entity_id)
            return {"entity_type": entity_type, "id": entity_id, "status": after["status"], "revision": after["revision"], "published_at": after["published_at"],
                    "archived_at": after["archived_at"], "warnings": warnings}
    except ValidationFailed as exc:
        codes = sorted({f["code"] for f in validators.errors(exc.findings)})
        audit.record_rejected(db_path, actor, "validation_failed", entity_type, entity_id, key,
                              {"finding_codes": codes, "status_before": row["status"], "revision_before": row["revision"]}, request_id=rid)
        raise
