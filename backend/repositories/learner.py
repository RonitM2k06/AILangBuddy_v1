"""Learner profile persistence. Functions take an open connection so the service can group them."""


def get_language_id(conn, code):
    row = conn.execute("SELECT id FROM languages WHERE code = ?", (code,)).fetchone()
    return row["id"] if row else None


def is_supported_combination(conn, language_id, cefr_code):
    return conn.execute(
        "SELECT 1 FROM language_levels WHERE language_id = ? AND cefr_code = ?", (language_id, cefr_code)
    ).fetchone() is not None


def age_group_for_age(conn, age):
    row = conn.execute(
        "SELECT code, label FROM age_groups WHERE min_age <= ? AND (max_age IS NULL OR ? <= max_age) ORDER BY min_age DESC LIMIT 1",
        (age, age),
    ).fetchone()
    return dict(row) if row else None


def age_group_id_for_age(conn, age):
    """The age group an age falls in, with its id (for content targeting), or None."""
    row = conn.execute(
        "SELECT id, code FROM age_groups WHERE min_age <= ? AND (max_age IS NULL OR ? <= max_age) ORDER BY min_age DESC LIMIT 1",
        (age, age)).fetchone()
    return dict(row) if row else None


def upsert_profile(conn, user_id, native_id, target_id, cefr_code, date_of_birth, updated_at):
    conn.execute(
        """INSERT INTO learner_profiles(user_id, native_language_id, target_language_id, cefr_level, date_of_birth, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET native_language_id = excluded.native_language_id,
               target_language_id = excluded.target_language_id, cefr_level = excluded.cefr_level,
               date_of_birth = excluded.date_of_birth, updated_at = excluded.updated_at""",
        (user_id, native_id, target_id, cefr_code, date_of_birth, updated_at),
    )


def get_profile(conn, user_id):
    row = conn.execute(
        """SELECT nl.code AS native_language, tl.code AS target_language, p.cefr_level, p.date_of_birth, p.updated_at
           FROM learner_profiles p
           JOIN languages nl ON nl.id = p.native_language_id
           JOIN languages tl ON tl.id = p.target_language_id
           WHERE p.user_id = ?""",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None
