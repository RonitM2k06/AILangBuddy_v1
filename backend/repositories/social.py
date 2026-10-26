"""Friend codes, requests and friendships. Takes an open connection. Reads of other learners return display names only and go
through a friendship or a request addressed to the caller."""


def user_for_code(conn, code):
    row = conn.execute("SELECT user_id FROM learner_gamification WHERE friend_code = ?", (code,)).fetchone()
    return row["user_id"] if row else None


def profile_dob(conn, user_id):
    row = conn.execute("SELECT date_of_birth FROM learner_profiles WHERE user_id = ?", (user_id,)).fetchone()
    return row["date_of_birth"] if row else None


def has_learner_role(conn, user_id):
    return conn.execute("SELECT 1 FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = ? AND r.name = 'learner'", (user_id,)).fetchone() is not None


def display_name(conn, user_id):
    return conn.execute("SELECT display_name FROM users WHERE id = ?", (user_id,)).fetchone()["display_name"]


def friendship_between(conn, a, b):
    low, high = min(a, b), max(a, b)
    row = conn.execute("SELECT id FROM friendships WHERE user_low = ? AND user_high = ?", (low, high)).fetchone()
    return row["id"] if row else None


def count_friends(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM friendships WHERE user_low = ? OR user_high = ?", (user_id, user_id)).fetchone()[0]


def list_friendships(conn, user_id):
    """[{id, friend_id, since}] for the caller (internal friend_id: the service turns it into a display name)."""
    return [dict(r) for r in conn.execute(
        """SELECT id, CASE WHEN user_low = ? THEN user_high ELSE user_low END AS friend_id, created_at AS since FROM friendships
           WHERE user_low = ? OR user_high = ? ORDER BY id""", (user_id, user_id, user_id)).fetchall()]


def delete_friendship(conn, user_id, friendship_id):
    return conn.execute("DELETE FROM friendships WHERE id = ? AND (user_low = ? OR user_high = ?)", (friendship_id, user_id, user_id)).rowcount == 1


def insert_friendship(conn, a, b, now):
    conn.execute("INSERT OR IGNORE INTO friendships(user_low, user_high, created_at) VALUES (?, ?, ?)", (min(a, b), max(a, b), now))


def pending_between(conn, a, b):
    return conn.execute("SELECT 1 FROM friend_requests WHERE status = 'pending' AND MIN(requester_id, addressee_id) = ? AND MAX(requester_id, addressee_id) = ?",
                        (min(a, b), max(a, b))).fetchone() is not None


def recently_rejected(conn, requester, addressee, since):
    return conn.execute("SELECT 1 FROM friend_requests WHERE requester_id = ? AND addressee_id = ? AND status = 'rejected' AND responded_at >= ?",
                        (requester, addressee, since)).fetchone() is not None


def count_pending_outgoing(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM friend_requests WHERE requester_id = ? AND status = 'pending'", (user_id,)).fetchone()[0]


def insert_request(conn, requester, addressee, now):
    return conn.execute("INSERT INTO friend_requests(requester_id, addressee_id, created_at) VALUES (?, ?, ?)", (requester, addressee, now)).lastrowid


def incoming(conn, user_id):
    return [dict(r) for r in conn.execute("SELECT id, requester_id AS other_id, created_at FROM friend_requests WHERE addressee_id = ? AND status = 'pending' ORDER BY id", (user_id,)).fetchall()]


def outgoing(conn, user_id):
    return [dict(r) for r in conn.execute("SELECT id, addressee_id AS other_id, created_at FROM friend_requests WHERE requester_id = ? AND status = 'pending' ORDER BY id", (user_id,)).fetchall()]


def get_incoming(conn, user_id, request_id):
    """A request, only if it is addressed to this learner (anyone else's, or an unknown id, gives None)."""
    row = conn.execute("SELECT id, requester_id, status FROM friend_requests WHERE id = ? AND addressee_id = ?", (request_id, user_id)).fetchone()
    return dict(row) if row else None


def respond(conn, request_id, user_id, status, now):
    """Guarded: only a pending request addressed to this learner. Returns True if this call answered it."""
    return conn.execute("UPDATE friend_requests SET status = ?, responded_at = ? WHERE id = ? AND addressee_id = ? AND status = 'pending'",
                        (status, now, request_id, user_id)).rowcount == 1
