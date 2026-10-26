"""Session persistence. Only token hashes are ever stored or queried; sessions are named outside the server by their public_id.
Every query that acts for a user is scoped by that user's id, so one user can never reach another's session."""
import secrets


def new_public_id():
    return secrets.token_hex(16)


def create(conn, user_id, token_hash, created_at, expires_at, public_id=None, mfa_level=0, auth_method="password"):
    """Returns the new session's public id. last_seen_at starts at created_at. mfa_level / auth_method are fixed for the session's life
    (0026's trigger): a session that gains a second factor is a NEW session."""
    public_id = public_id or new_public_id()
    conn.execute(
        "INSERT INTO sessions(user_id, token_hash, public_id, created_at, last_seen_at, expires_at, mfa_level, auth_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, token_hash, public_id, created_at, created_at, expires_at, mfa_level, auth_method),
    )
    return public_id


def get_user_by_token_hash(conn, token_hash):
    """Returns the session's user fields plus the session's own id, public id, last use and expiry, or None."""
    return conn.execute(
        """SELECT u.id, u.handle, u.display_name, u.email, s.id AS session_id, s.public_id, s.last_seen_at, s.expires_at, s.mfa_level, s.auth_method
           FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?""",
        (token_hash,),
    ).fetchone()


def touch(conn, session_id, now):
    """Record a use. Only ever moves last_seen_at forward (the schema refuses anything else)."""
    conn.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ? AND last_seen_at < ?", (now, session_id, now))


def delete_by_token_hash(conn, token_hash):
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def delete_expired_for_user(conn, user_id, now, idle_cutoff):
    """Drop this user's sessions that have passed their absolute expiry or have been idle since before `idle_cutoff`."""
    conn.execute("DELETE FROM sessions WHERE user_id = ? AND (expires_at <= ? OR last_seen_at <= ?)", (user_id, now, idle_cutoff))


def list_for_user(conn, user_id, now, idle_cutoff):
    """The user's live sessions, newest use first. Safe fields only: never the token hash or the row id."""
    return conn.execute(
        """SELECT public_id, created_at, last_seen_at, expires_at, auth_method FROM sessions
           WHERE user_id = ? AND expires_at > ? AND last_seen_at > ? ORDER BY last_seen_at DESC, created_at DESC""",
        (user_id, now, idle_cutoff),
    ).fetchall()


def delete_for_user(conn, user_id, public_id):
    """Revoke one of this user's own sessions. Returns 1 if it was theirs, 0 otherwise (unknown and foreign look the same)."""
    return conn.execute("DELETE FROM sessions WHERE user_id = ? AND public_id = ?", (user_id, public_id)).rowcount


def delete_others_for_user(conn, user_id, keep_public_id):
    """Revoke every session of this user except `keep_public_id`. Returns how many were revoked."""
    return conn.execute("DELETE FROM sessions WHERE user_id = ? AND public_id <> ?", (user_id, keep_public_id)).rowcount


def delete_all_for_user(conn, user_id):
    return conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,)).rowcount
