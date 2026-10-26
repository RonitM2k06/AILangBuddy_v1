"""Child game state: lives and the record of lives lost. Takes an open connection; every function is scoped by user_id.
Lives only change through guarded statements, and the database itself bounds them (CHECK 0..5)."""


def get_state(conn, user_id):
    row = conn.execute("SELECT lives, lives_updated_at FROM child_game_state WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_state(conn, user_id, lives, now):
    conn.execute("INSERT OR IGNORE INTO child_game_state(user_id, lives, lives_updated_at, created_at) VALUES (?, ?, ?, ?)",
                 (user_id, lives, now, now))


def save_regenerated(conn, user_id, lives, anchor):
    conn.execute("UPDATE child_game_state SET lives = ?, lives_updated_at = ? WHERE user_id = ?", (lives, anchor, user_id))


def lose_life(conn, user_id, now, max_lives):
    """Takes one life, only if there is one to take. Returns the lives left, or None when there were none (nothing changes).
    The regeneration anchor restarts only when the child was at full lives (otherwise a loss must not delay a life already coming)."""
    cur = conn.execute(
        """UPDATE child_game_state SET lives = lives - 1, lives_updated_at = CASE WHEN lives >= ? THEN ? ELSE lives_updated_at END
           WHERE user_id = ? AND lives > 0""", (max_lives, now, user_id))
    if cur.rowcount == 0:
        return None
    return conn.execute("SELECT lives FROM child_game_state WHERE user_id = ?", (user_id,)).fetchone()["lives"]


def record_loss(conn, user_id, attempt_id, lives_after, now):
    conn.execute("INSERT INTO child_life_losses(user_id, attempt_id, attempt_correct, lives_after, lost_at) VALUES (?, ?, 0, ?, ?)",
                 (user_id, attempt_id, lives_after, now))


def losses(conn, user_id):
    return [dict(r) for r in conn.execute(
        "SELECT attempt_id, lives_after, lost_at FROM child_life_losses WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()]
