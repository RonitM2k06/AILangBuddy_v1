"""Admin audit log persistence. Takes an open connection so an event is written in the same transaction as the change it records.
Rows are only ever inserted: the table refuses UPDATE and DELETE (migration 0025)."""

_COLUMNS = "id, occurred_at, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id"


def insert(conn, actor_user_id, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id):
    return conn.execute(
        """INSERT INTO admin_audit_log(actor_user_id, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (actor_user_id, actor_label, action, entity_type, entity_id, entity_key, outcome, meta_json, request_id),
    ).lastrowid


def _where(filters):
    clauses, params = [], []
    if filters.get("actor"):
        clauses.append("actor_label = ?")
        params.append(filters["actor"])
    for key in ("entity_type", "entity_id", "action", "outcome"):
        if filters.get(key) is not None:
            clauses.append(f"{key} = ?")
            params.append(filters[key])
    if filters.get("from"):
        clauses.append("occurred_at >= ?")
        params.append(filters["from"])
    if filters.get("to"):
        clauses.append("occurred_at < ?")
        params.append(filters["to"])
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def count(conn, filters):
    where, params = _where(filters)
    return conn.execute(f"SELECT COUNT(*) FROM admin_audit_log{where}", params).fetchone()[0]


def list_events(conn, filters, limit, offset):
    where, params = _where(filters)
    return [dict(r) for r in conn.execute(
        f"SELECT {_COLUMNS} FROM admin_audit_log{where} ORDER BY occurred_at DESC, id DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()]


def get(conn, event_id):
    row = conn.execute(f"SELECT {_COLUMNS} FROM admin_audit_log WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None
