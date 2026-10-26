"""Parent-child links, one-time link codes and parental controls. Takes an open connection. Every read of a child goes through a
link and is scoped by the PARENT's id, so a parent cannot name their way to a learner they are not linked to."""


# ---------- codes ----------
def delete_unused_codes(conn, learner_id):
    conn.execute("DELETE FROM parent_link_codes WHERE learner_id = ? AND used_at IS NULL", (learner_id,))


def insert_code(conn, learner_id, code_hash, created_at, expires_at):
    conn.execute("INSERT INTO parent_link_codes(learner_id, code_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
                 (learner_id, code_hash, created_at, expires_at))


def find_live_code(conn, code_hash, now):
    row = conn.execute("SELECT id, learner_id FROM parent_link_codes WHERE code_hash = ? AND used_at IS NULL AND expires_at > ?",
                       (code_hash, now)).fetchone()
    return dict(row) if row else None


def consume_code(conn, code_id, parent_id, now):
    """Single use: only an unused code can be consumed. Returns True if this call consumed it."""
    return conn.execute("UPDATE parent_link_codes SET used_at = ?, used_by = ? WHERE id = ? AND used_at IS NULL",
                        (now, parent_id, code_id)).rowcount == 1


# ---------- links ----------
def insert_link(conn, parent_id, learner_id, now):
    return conn.execute("INSERT INTO parent_links(parent_id, learner_id, created_at) VALUES (?, ?, ?)", (parent_id, learner_id, now)).lastrowid


def count_children(conn, parent_id):
    return conn.execute("SELECT COUNT(*) FROM parent_links WHERE parent_id = ?", (parent_id,)).fetchone()[0]


def count_parents(conn, learner_id):
    return conn.execute("SELECT COUNT(*) FROM parent_links WHERE learner_id = ?", (learner_id,)).fetchone()[0]


def link_exists(conn, parent_id, learner_id):
    return conn.execute("SELECT 1 FROM parent_links WHERE parent_id = ? AND learner_id = ?", (parent_id, learner_id)).fetchone() is not None


_LINK = """SELECT pl.id AS link_id, pl.learner_id, pl.created_at AS linked_at, u.display_name
           FROM parent_links pl JOIN users u ON u.id = pl.learner_id"""


def list_links(conn, parent_id):
    return [dict(r) for r in conn.execute(f"{_LINK} WHERE pl.parent_id = ? ORDER BY pl.id", (parent_id,)).fetchall()]


def get_link(conn, parent_id, link_id):
    """The link, only if it belongs to this parent (a foreign or unknown id gives None)."""
    row = conn.execute(f"{_LINK} WHERE pl.parent_id = ? AND pl.id = ?", (parent_id, link_id)).fetchone()
    return dict(row) if row else None


def delete_link(conn, parent_id, link_id):
    return conn.execute("DELETE FROM parent_links WHERE id = ? AND parent_id = ?", (link_id, parent_id)).rowcount == 1


# ---------- controls ----------
def get_control(conn, link_id):
    row = conn.execute("SELECT voice_disabled, updated_at FROM parent_controls WHERE link_id = ?", (link_id,)).fetchone()
    return dict(row) if row else None


def set_control(conn, link_id, voice_disabled, now):
    conn.execute(
        """INSERT INTO parent_controls(link_id, voice_disabled, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(link_id) DO UPDATE SET voice_disabled = excluded.voice_disabled, updated_at = excluded.updated_at""",
        (link_id, 1 if voice_disabled else 0, now))


def voice_disabled_for_learner(conn, learner_id):
    """True if ANY linked parent has switched the learner's voice features off (the strictest control applies)."""
    return conn.execute(
        "SELECT 1 FROM parent_controls c JOIN parent_links pl ON pl.id = c.link_id WHERE pl.learner_id = ? AND c.voice_disabled = 1 LIMIT 1",
        (learner_id,)).fetchone() is not None


# ---------- activity (the existing unified attempts view) ----------
def recent_activity(conn, learner_id, language_id, limit):
    return [dict(r) for r in conn.execute(
        """SELECT source, is_correct, difficulty, attempted_at FROM learner_attempts
           WHERE user_id = ? AND language_id = ? ORDER BY attempted_at DESC, source, attempt_id DESC LIMIT ?""",
        (learner_id, language_id, limit)).fetchall()]


def activity_by_source(conn, learner_id, language_id):
    return {r["source"]: {"attempts": r["n"], "correct": r["c"], "last_at": r["last"]} for r in conn.execute(
        """SELECT source, COUNT(*) AS n, SUM(is_correct) AS c, MAX(attempted_at) AS last FROM learner_attempts
           WHERE user_id = ? AND language_id = ? GROUP BY source""", (learner_id, language_id)).fetchall()}
