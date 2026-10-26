"""Read access for the admin views of accounts and security events (Phase 14E). SQL only; the services decide what leaves the server.
Writing security events is backend/auth/events.py; nothing here updates or deletes them (the schema refuses both anyway)."""


def page_events(conn, before_id, event_type, limit):
    """Newest first. `before_id` is the cursor (exclusive); `event_type` an optional exact filter (validated by the caller). limit + 1 rows
    are read so the caller can tell whether another page exists."""
    return conn.execute(
        """SELECT id, occurred_at, event_type, outcome, user_id, method, reason, stage, count, ip_ref FROM security_events
           WHERE (? IS NULL OR id < ?) AND (? IS NULL OR event_type = ?) ORDER BY id DESC LIMIT ?""",
        (before_id, before_id, event_type, event_type, limit + 1)).fetchall()


def count_accounts(conn):
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def page_accounts(conn, limit, offset):
    """Accounts in creation order: id (for the reference only), creation time, roles and whether two-factor is on. Never a name, e-mail,
    handle, password hash, session or 2FA detail."""
    return conn.execute(
        """SELECT u.id, u.created_at,
                  (SELECT group_concat(name, ',') FROM (SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = u.id ORDER BY r.name)) AS roles,
                  EXISTS (SELECT 1 FROM two_factor_credentials t WHERE t.user_id = u.id AND t.status = 'enabled') AS two_factor
           FROM users u ORDER BY u.id LIMIT ? OFFSET ?""", (limit, offset)).fetchall()


def admin_mfa_counts(conn):
    """(admins, admins with two-factor on)."""
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(EXISTS (SELECT 1 FROM two_factor_credentials t WHERE t.user_id = ur.user_id AND t.status = 'enabled')), 0)
           FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE r.name = 'admin'""").fetchone()
    return row[0], row[1]
