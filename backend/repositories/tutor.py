"""Tutor conversations, messages and the facts behind each reply. Takes an open connection; every function is scoped by user_id,
so another learner's conversation is simply not found."""
import sqlite3  # noqa: F401  (IntegrityError is handled by the service)


def count_conversations(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM tutor_conversations WHERE user_id = ?", (user_id,)).fetchone()[0]


def create_conversation(conn, user_id, language_id, cefr, mode, topic_id, lesson_id, situation_id, title, now):
    return conn.execute(
        """INSERT INTO tutor_conversations(user_id, language_id, cefr_code, mode, topic_id, lesson_id, situation_id, title, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (user_id, language_id, cefr, mode, topic_id, lesson_id, situation_id, title, now, now)).lastrowid


_CONV = """SELECT c.id, c.title, c.mode, c.status, c.message_count, c.created_at, c.updated_at, c.cefr_code,
                  c.topic_id, c.lesson_id, c.situation_id, t.slug AS topic_slug FROM tutor_conversations c LEFT JOIN topics t ON t.id = c.topic_id"""


def list_conversations(conn, user_id, limit):
    return [dict(r) for r in conn.execute(f"{_CONV} WHERE c.user_id = ? ORDER BY c.updated_at DESC, c.id DESC LIMIT ?", (user_id, limit)).fetchall()]


def get_conversation(conn, user_id, conversation_id):
    row = conn.execute(f"{_CONV} WHERE c.user_id = ? AND c.id = ?", (user_id, conversation_id)).fetchone()
    return dict(row) if row else None


def list_messages(conn, user_id, conversation_id, after_seq, limit):
    return [dict(r) for r in conn.execute(
        """SELECT id, seq, role, content, quick_prompt, provider, created_at FROM tutor_messages
           WHERE user_id = ? AND conversation_id = ? AND seq > ? ORDER BY seq LIMIT ?""", (user_id, conversation_id, after_seq, limit)).fetchall()]


def last_messages(conn, user_id, conversation_id, n):
    rows = conn.execute("SELECT role, content FROM tutor_messages WHERE user_id = ? AND conversation_id = ? ORDER BY seq DESC LIMIT ?",
                        (user_id, conversation_id, n)).fetchall()
    return [dict(r) for r in reversed(rows)]


def count_learner_messages(conn, user_id, conversation_id):
    return conn.execute("SELECT COUNT(*) FROM tutor_messages WHERE user_id = ? AND conversation_id = ? AND role = 'learner'", (user_id, conversation_id)).fetchone()[0]


def find_by_client_id(conn, user_id, conversation_id, client_id):
    """The learner message with this client id and the tutor reply that followed it (a replayed request gets the stored pair)."""
    row = conn.execute("SELECT id, seq, content, quick_prompt, created_at FROM tutor_messages WHERE user_id = ? AND conversation_id = ? AND client_id = ?",
                       (user_id, conversation_id, client_id)).fetchone()
    if row is None:
        return None
    reply = conn.execute("SELECT id, seq, content, provider, created_at FROM tutor_messages WHERE user_id = ? AND conversation_id = ? AND seq = ?",
                         (user_id, conversation_id, row["seq"] + 1)).fetchone()
    return dict(row), (dict(reply) if reply else None)


def insert_message(conn, conversation_id, user_id, seq, role, content, quick_prompt, client_id, provider, now):
    return conn.execute(
        """INSERT INTO tutor_messages(conversation_id, user_id, seq, role, content, quick_prompt, client_id, provider, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (conversation_id, user_id, seq, role, content, quick_prompt, client_id, provider, now)).lastrowid


def bump(conn, user_id, conversation_id, added, cap, now):
    """Adds to the message count only while it stays within the cap. Returns True if it did."""
    return conn.execute("UPDATE tutor_conversations SET message_count = message_count + ?, updated_at = ? WHERE id = ? AND user_id = ? AND message_count + ? <= ?",
                        (added, now, conversation_id, user_id, added, cap)).rowcount == 1


def insert_facts(conn, message_id, facts):
    conn.executemany("INSERT INTO tutor_message_facts(message_id, ord, kind, text) VALUES (?, ?, ?, ?)",
                     [(message_id, i, kind, text) for i, (kind, text) in enumerate(facts, start=1)])


def facts_for(conn, user_id, message_id):
    return [dict(r) for r in conn.execute(
        """SELECT f.kind, f.text FROM tutor_message_facts f JOIN tutor_messages m ON m.id = f.message_id
           WHERE f.message_id = ? AND m.user_id = ? ORDER BY f.ord""", (message_id, user_id)).fetchall()]


# ---------- context the tutor may use (all scoped to the learner) ----------
def recent_mistake_items(conn, user_id, language_id, limit):
    return [r[0] for r in conn.execute(
        """SELECT item_id FROM learner_attempts WHERE user_id = ? AND language_id = ? AND is_correct = 0 AND item_id IS NOT NULL
           GROUP BY item_id ORDER BY MAX(attempted_at) DESC, MAX(attempt_id) DESC LIMIT ?""", (user_id, language_id, limit)).fetchall()]


def lesson_title(conn, lesson_id):
    row = conn.execute("SELECT title FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    return row["title"] if row else None


def situation_title(conn, situation_id):
    row = conn.execute("SELECT title FROM situations WHERE id = ?", (situation_id,)).fetchone()
    return row["title"] if row else None
