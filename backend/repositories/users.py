"""User, role and session persistence. Functions take an open connection so callers
(the auth service) can group several of them into one transaction."""


def create_user(conn, handle, display_name, email, password_hash):
    cur = conn.execute(
        "INSERT INTO users(handle, display_name, email, password_hash) VALUES (?, ?, ?, ?)",
        (handle, display_name, email, password_hash),
    )
    return cur.lastrowid


def assign_role(conn, user_id, role_name):
    cur = conn.execute(
        "INSERT INTO user_roles(user_id, role_id) SELECT ?, id FROM roles WHERE name = ?", (user_id, role_name)
    )
    if cur.rowcount != 1:
        raise ValueError(f"Unknown role: {role_name}")


def get_by_email(conn, email):
    return conn.execute(
        "SELECT id, handle, display_name, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()


def get_roles(conn, user_id):
    rows = conn.execute(
        "SELECT r.name FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = ? ORDER BY r.name",
        (user_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def get_password_hash(conn, user_id):
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["password_hash"] if row else None


def set_password_hash(conn, user_id, password_hash):
    """Replace a user's password hash (only for a user who has credentials: the schema keeps email and hash set together)."""
    return conn.execute("UPDATE users SET password_hash = ? WHERE id = ? AND password_hash IS NOT NULL", (password_hash, user_id)).rowcount
