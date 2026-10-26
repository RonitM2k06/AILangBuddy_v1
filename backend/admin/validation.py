"""Content validation as a service: the dry run for one entity and the whole-catalogue integrity sweep. Both load snapshots through the same
repository functions and run the same pure validators, so a finding for an entity is identical wherever it is reported."""
from ..db import connect
from ..repositories import admin_content as repo
from . import validators
from .errors import NotFound
from .validators import finding


def findings_for(conn, entity_type, entity_id):
    """(findings, snapshot) for one entity, on the caller's connection (publish uses it inside its own transaction)."""
    snap = repo.LOADERS[entity_type](conn, entity_id)
    if snap is None:
        raise NotFound()
    return validators.VALIDATORS[entity_type](snap), snap


def dry_run(db_path, entity_type, entity_id):
    with connect(db_path) as conn:
        findings, _ = findings_for(conn, entity_type, entity_id)
    return {"ok": not validators.errors(findings), "findings": findings}


def _global_findings(conn):
    out = []
    check = repo.integrity_check(conn)
    if check != ["ok"]:
        out.append(finding("integrity_database", "database", "SQLite's integrity check reports a problem."))
    for table, n in repo.foreign_key_violations(conn):
        out.append(finding("integrity_foreign_key", f"table:{table}", f"{n} row(s) point at something that does not exist."))
    for item_id in repo.orphan_vocabulary_ids(conn):
        out.append(finding("integrity_orphan_vocabulary", f"vocabulary:{item_id}", "No lesson, step, activity or example uses this vocabulary item."))
    for topic_id in repo.orphan_topic_ids(conn):
        out.append(finding("integrity_orphan_topic", f"topic:{topic_id}", "No lesson, situation or listening activity uses this topic."))
    return out


def sweep(db_path):
    """Every lesson, situation and listening activity (whatever its status) plus the whole-database checks. `ok` means nothing PUBLISHED, and no
    whole-database check, has an error: a draft is allowed to be incomplete, and its findings are listed (entity_status says so) but do not fail the sweep."""
    findings, checked = [], {}
    with connect(db_path) as conn:
        for entity_type in repo.LOADERS:
            ids = repo.ids_of(conn, entity_type)
            checked[entity_type] = len(ids)
            for entity_id in ids:
                found, snap = findings_for(conn, entity_type, entity_id)
                findings += [{**f, "entity_status": snap["status"]} for f in found]
        findings += [{**f, "entity_status": None} for f in _global_findings(conn)]
    blocking = [f for f in findings if f["severity"] == "error" and f["entity_status"] in ("published", None)]
    return {"ok": not blocking, "checked": checked, "errors": sum(f["severity"] == "error" for f in findings),
            "warnings": sum(f["severity"] == "warning" for f in findings), "published_errors": len(blocking), "findings": findings}
