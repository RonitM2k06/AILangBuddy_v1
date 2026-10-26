"""Admin CMS persistence: the read side that builds validator snapshots, and (below) the guarded writes. Takes an open connection.
A snapshot is a plain dict of everything a pure validator needs about one lesson / situation / listening activity, so the same rules can run for a
dry run, a publish and the integrity sweep without any SQL in the rules themselves."""
from .. import settings

LIFECYCLE_TABLES = {"lesson": "lessons", "situation": "situations", "listening_activity": "listening_activities"}
AGE_TABLES = {"lesson": ("lesson_age_groups", "lesson_id"), "situation": ("situation_age_groups", "situation_id"),
              "listening_activity": ("listening_activity_age_groups", "activity_id")}


def _marks(ids):
    return ",".join("?" * len(ids))


def english_language_id(conn):
    row = conn.execute("SELECT id FROM languages WHERE code = ?", (settings.REQUIRED_TRANSLATION_LANGUAGE,)).fetchone()
    return row["id"] if row else None


def item_info(conn, item_ids):
    """{item_id: {id, language_id, text, cefr_rank, meaning_en}} for the ids that exist (meaning_en is None without an English translation)."""
    ids = sorted({i for i in item_ids if i is not None})
    if not ids:
        return {}
    en = english_language_id(conn)
    rows = conn.execute(
        f"""SELECT v.id, v.language_id, v.text, c.rank AS cefr_rank, t.meaning AS meaning_en
            FROM vocabulary_items v JOIN cefr_levels c ON c.code = v.cefr_code
            LEFT JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = ?
            WHERE v.id IN ({_marks(ids)})""", [en, *ids]).fetchall()
    return {r["id"]: dict(r) for r in rows}


def _base(conn, entity_type, row):
    """Fields every snapshot shares: the lifecycle columns, the language/level validity, the age targets and the sibling-title count."""
    age_table, age_fk = AGE_TABLES[entity_type]
    snap = {"type": entity_type, "id": row["id"], "slug": row["slug"], "title": row["title"], "language_id": row["language_id"], "cefr_code": row["cefr_code"],
            "sort_order": row["sort_order"], "status": row["status"], "published_at": row["published_at"], "archived_at": row["archived_at"],
            "updated_at": row["updated_at"], "revision": row["revision"]}
    snap["cefr_rank"] = (conn.execute("SELECT rank FROM cefr_levels WHERE code = ?", (row["cefr_code"],)).fetchone() or {"rank": None})["rank"]
    snap["level_valid"] = conn.execute("SELECT 1 FROM language_levels WHERE language_id = ? AND cefr_code = ?", (row["language_id"], row["cefr_code"])).fetchone() is not None
    snap["age_group_ids"] = [r[0] for r in conn.execute(f"SELECT age_group_id FROM {age_table} WHERE {age_fk} = ? ORDER BY age_group_id", (row["id"],))]
    snap["known_age_group_ids"] = {r[0] for r in conn.execute("SELECT id FROM age_groups")}
    snap["sibling_title_count"] = conn.execute(
        f"SELECT COUNT(*) FROM {LIFECYCLE_TABLES[entity_type]} WHERE id <> ? AND language_id = ? AND cefr_code = ? AND lower(trim(title)) = lower(trim(?))",
        (row["id"], row["language_id"], row["cefr_code"], row["title"])).fetchone()[0]
    snap["dependencies"] = []        # status-bearing content this one depends on: none exists in the 0001-0025 schema (see docs/ARCHITECTURE.md §21)
    return snap


def load_lesson(conn, lesson_id):
    row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if row is None:
        return None
    snap = _base(conn, "lesson", row)
    snap.update(description=row["description"], situation=row["situation"], tip=row["tip"])
    snap["topics"] = [dict(r) for r in conn.execute(
        "SELECT t.id, t.slug FROM lesson_topics lt JOIN topics t ON t.id = lt.topic_id WHERE lt.lesson_id = ? ORDER BY t.slug", (lesson_id,))]
    snap["vocabulary_ids"] = [r[0] for r in conn.execute("SELECT item_id FROM lesson_vocabulary WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,))]
    exercises = [dict(r) for r in conn.execute(
        "SELECT id, kind, prompt, explanation, item_id, sort_order, difficulty FROM exercises WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,))]
    answers = {}
    for r in conn.execute("SELECT a.id, a.exercise_id, a.answer_text, a.is_correct, a.sort_order FROM exercise_answers a JOIN exercises e ON e.id = a.exercise_id "
                          "WHERE e.lesson_id = ? ORDER BY a.exercise_id, a.sort_order", (lesson_id,)):
        answers.setdefault(r["exercise_id"], []).append({"id": r["id"], "text": r["answer_text"], "is_correct": bool(r["is_correct"]), "sort_order": r["sort_order"]})
    for e in exercises:
        e["answers"] = answers.get(e["id"], [])
    snap["exercises"] = exercises
    snap["items"] = item_info(conn, [*snap["vocabulary_ids"], *[e["item_id"] for e in exercises]])
    return snap


def load_situation(conn, situation_id):
    row = conn.execute("SELECT * FROM situations WHERE id = ?", (situation_id,)).fetchone()
    if row is None:
        return None
    snap = _base(conn, "situation", row)
    snap.update(description=row["description"], goal=row["goal"], setting=row["setting"], partner_name=row["partner_name"], partner_role=row["partner_role"],
                difficulty=row["difficulty"])
    topic = conn.execute("SELECT id, slug FROM topics WHERE id = ?", (row["topic_id"],)).fetchone()
    snap["topic"] = dict(topic) if topic else None
    steps = [dict(r) for r in conn.execute(
        "SELECT id, sort_order, kind, prompt, prompt_meaning, item_id, explanation FROM situation_steps WHERE situation_id = ? ORDER BY sort_order", (situation_id,))]
    answers = {}
    for r in conn.execute("SELECT a.id, a.step_id, a.answer_text, a.is_correct, a.sort_order FROM situation_step_answers a JOIN situation_steps s ON s.id = a.step_id "
                          "WHERE s.situation_id = ? ORDER BY a.step_id, a.sort_order", (situation_id,)):
        answers.setdefault(r["step_id"], []).append({"id": r["id"], "text": r["answer_text"], "is_correct": bool(r["is_correct"]), "sort_order": r["sort_order"]})
    for s in steps:
        s["answers"] = answers.get(s["id"], [])
    snap["steps"] = steps
    snap["items"] = item_info(conn, [s["item_id"] for s in steps])
    return snap


def load_listening_activity(conn, activity_id):
    row = conn.execute("SELECT * FROM listening_activities WHERE id = ?", (activity_id,)).fetchone()
    if row is None:
        return None
    snap = _base(conn, "listening_activity", row)
    snap.update(mode=row["mode"], prompt=row["prompt"], difficulty=row["difficulty"], item_id=row["item_id"])
    topic = conn.execute("SELECT id, slug FROM topics WHERE id = ?", (row["topic_id"],)).fetchone()
    snap["topic"] = dict(topic) if topic else None
    snap["options"] = [dict(r) for r in conn.execute("SELECT id, item_id, sort_order FROM listening_options WHERE activity_id = ? ORDER BY sort_order", (activity_id,))]
    snap["items"] = item_info(conn, [row["item_id"], *[o["item_id"] for o in snap["options"]]])
    return snap


LOADERS = {"lesson": load_lesson, "situation": load_situation, "listening_activity": load_listening_activity}


def ids_of(conn, entity_type):
    return [r[0] for r in conn.execute(f"SELECT id FROM {LIFECYCLE_TABLES[entity_type]} ORDER BY id")]


# ---------- whole-database checks used by the integrity sweep ----------
def foreign_key_violations(conn):
    """[(table, count)] from PRAGMA foreign_key_check. Table names only: no row contents leave the database layer."""
    counts = {}
    for r in conn.execute("PRAGMA foreign_key_check"):
        counts[r[0]] = counts.get(r[0], 0) + 1
    return sorted(counts.items())


def integrity_check(conn):
    return [r[0] for r in conn.execute("PRAGMA integrity_check")]


def orphan_vocabulary_ids(conn):
    """Vocabulary items nothing refers to: no lesson, exercise, step, listening activity/option, grammar or vocabulary example, speaking session or AI drill."""
    return [r[0] for r in conn.execute(
        """SELECT v.id FROM vocabulary_items v WHERE
             NOT EXISTS (SELECT 1 FROM lesson_vocabulary x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM exercises x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM situation_steps x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM listening_activities x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM listening_options x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM grammar_examples x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM vocabulary_examples x WHERE x.item_id = v.id OR x.example_item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM speaking_sessions x WHERE x.item_id = v.id)
         AND NOT EXISTS (SELECT 1 FROM ai_micro_lessons x WHERE x.item_id = v.id)
         ORDER BY v.id""")]


def orphan_topic_ids(conn):
    return [r[0] for r in conn.execute(
        """SELECT t.id FROM topics t WHERE NOT EXISTS (SELECT 1 FROM lesson_topics x WHERE x.topic_id = t.id)
             AND NOT EXISTS (SELECT 1 FROM situations x WHERE x.topic_id = t.id) AND NOT EXISTS (SELECT 1 FROM listening_activities x WHERE x.topic_id = t.id)
           ORDER BY t.id""")]


# =====================================================================================================================
# Writes and the lookups they need. Every write function does exactly one thing; the rules (who may, in which state) live in backend/admin/*.
# =====================================================================================================================
def _like(q):
    """A LIKE pattern for a plain substring search (the user's % and _ are matched literally)."""
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


# ---------- lookups ----------
def language_by_code(conn, code):
    return conn.execute("SELECT id, code, name FROM languages WHERE code = ?", (code,)).fetchone()


def level_exists(conn, language_id, cefr):
    return conn.execute("SELECT 1 FROM language_levels WHERE language_id = ? AND cefr_code = ?", (language_id, cefr)).fetchone() is not None


def age_group_id(conn, code):
    row = conn.execute("SELECT id FROM age_groups WHERE code = ?", (code,)).fetchone()
    return row["id"] if row else None


def topic_id(conn, slug):
    row = conn.execute("SELECT id FROM topics WHERE slug = ?", (slug,)).fetchone()
    return row["id"] if row else None


def vocabulary_row(conn, item_id):
    row = conn.execute("SELECT id, language_id, cefr_code, kind, text, pronunciation FROM vocabulary_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def unit_row(conn, entity_type, entity_id):
    row = conn.execute(f"SELECT * FROM {LIFECYCLE_TABLES[entity_type]} WHERE id = ?", (entity_id,)).fetchone()
    return dict(row) if row else None


def slug_taken(conn, entity_type, language_id, slug, exclude_id=None):
    return conn.execute(f"SELECT 1 FROM {LIFECYCLE_TABLES[entity_type]} WHERE language_id = ? AND slug = ? AND id IS NOT ?", (language_id, slug, exclude_id)).fetchone() is not None


def sort_taken(conn, entity_type, language_id, cefr, sort_order, exclude_id=None):
    return conn.execute(f"SELECT 1 FROM {LIFECYCLE_TABLES[entity_type]} WHERE language_id = ? AND cefr_code = ? AND sort_order = ? AND id IS NOT ?",
                        (language_id, cefr, sort_order, exclude_id)).fetchone() is not None


def next_sort(conn, entity_type, language_id, cefr):
    return conn.execute(f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {LIFECYCLE_TABLES[entity_type]} WHERE language_id = ? AND cefr_code = ?", (language_id, cefr)).fetchone()[0]


# ---------- lifecycle columns ----------
def bump(conn, entity_type, entity_id, expected_revision, now):
    """The optimistic-concurrency step: one guarded UPDATE that succeeds only if nobody changed the row since the caller read `expected_revision`.
    Returns the new revision, or None when the revision was stale."""
    table = LIFECYCLE_TABLES[entity_type]
    cur = conn.execute(f"UPDATE {table} SET revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?", (now, entity_id, expected_revision))
    return expected_revision + 1 if cur.rowcount == 1 else None


def set_status(conn, entity_type, entity_id, status, now):
    """published_at is the time of the CURRENT publication, archived_at the time of the current archiving: each is cleared when the row leaves that state."""
    table = LIFECYCLE_TABLES[entity_type]
    conn.execute(f"UPDATE {table} SET status = ?, published_at = ?, archived_at = ? WHERE id = ?",
                 (status, now if status == "published" else None, now if status == "archived" else None, entity_id))


def set_age_groups(conn, entity_type, entity_id, group_ids):
    table, fk = AGE_TABLES[entity_type]
    conn.execute(f"DELETE FROM {table} WHERE {fk} = ?", (entity_id,))
    conn.executemany(f"INSERT INTO {table}({fk}, age_group_id) VALUES (?, ?)", [(entity_id, g) for g in group_ids])


def age_group_codes(conn, entity_type, entity_id):
    table, fk = AGE_TABLES[entity_type]
    return [r[0] for r in conn.execute(f"SELECT g.code FROM {table} x JOIN age_groups g ON g.id = x.age_group_id WHERE x.{fk} = ? ORDER BY g.min_age", (entity_id,))]


def update_fields(conn, entity_type, entity_id, fields):
    """UPDATE the named columns of a lifecycle row. Column names come from the services' own fixed lists, never from a request."""
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE {LIFECYCLE_TABLES[entity_type]} SET {sets} WHERE id = ?", [*fields.values(), entity_id])


# ---------- lessons ----------
def insert_lesson(conn, language_id, cefr, slug, title, description, situation, tip, sort_order, now):
    return conn.execute(
        """INSERT INTO lessons(language_id, cefr_code, slug, title, description, situation, tip, sort_order, status, updated_at, revision)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, 1)""", (language_id, cefr, slug, title, description, situation, tip, sort_order, now)).lastrowid


def set_lesson_topics(conn, lesson_id, topic_ids_):
    conn.execute("DELETE FROM lesson_topics WHERE lesson_id = ?", (lesson_id,))
    conn.executemany("INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (?, ?)", [(lesson_id, t) for t in topic_ids_])


def set_lesson_vocabulary(conn, lesson_id, language_id, item_ids):
    conn.execute("DELETE FROM lesson_vocabulary WHERE lesson_id = ?", (lesson_id,))
    conn.executemany("INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES (?, ?, ?, ?)",
                     [(lesson_id, item, language_id, n) for n, item in enumerate(item_ids, 1)])


def lesson_vocabulary_ids(conn, lesson_id):
    return [r[0] for r in conn.execute("SELECT item_id FROM lesson_vocabulary WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,))]


def lesson_topic_slugs(conn, lesson_id):
    return [r[0] for r in conn.execute("SELECT t.slug FROM lesson_topics lt JOIN topics t ON t.id = lt.topic_id WHERE lt.lesson_id = ? ORDER BY t.slug", (lesson_id,))]


def exercise_row(conn, lesson_id, exercise_id):
    row = conn.execute("SELECT id, lesson_id, language_id, kind, prompt, explanation, item_id, sort_order, difficulty FROM exercises WHERE id = ? AND lesson_id = ?",
                       (exercise_id, lesson_id)).fetchone()
    return dict(row) if row else None


def exercise_sort_taken(conn, lesson_id, sort_order, exclude_id=None):
    return conn.execute("SELECT 1 FROM exercises WHERE lesson_id = ? AND sort_order = ? AND id IS NOT ?", (lesson_id, sort_order, exclude_id)).fetchone() is not None


def next_exercise_sort(conn, lesson_id):
    return conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM exercises WHERE lesson_id = ?", (lesson_id,)).fetchone()[0]


def insert_exercise(conn, lesson_id, language_id, kind, prompt, explanation, item_id, sort_order, difficulty):
    return conn.execute(
        "INSERT INTO exercises(lesson_id, language_id, kind, prompt, explanation, item_id, sort_order, difficulty) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (lesson_id, language_id, kind, prompt, explanation, item_id, sort_order, difficulty)).lastrowid


def update_exercise(conn, exercise_id, fields):
    if fields:
        conn.execute(f"UPDATE exercises SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), exercise_id])


def exercise_answers(conn, exercise_id):
    return [dict(r) for r in conn.execute("SELECT id, answer_text AS text, is_correct, sort_order FROM exercise_answers WHERE exercise_id = ? ORDER BY sort_order", (exercise_id,))]


def exercise_answer_used(conn, answer_id):
    """True once any learner chose this answer (the attempt row points at it)."""
    return conn.execute("SELECT 1 FROM exercise_attempts WHERE answer_id = ? LIMIT 1", (answer_id,)).fetchone() is not None


def insert_exercise_answer(conn, exercise_id, text, is_correct, sort_order):
    return conn.execute("INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES (?, ?, ?, ?)", (exercise_id, text, 1 if is_correct else 0, sort_order)).lastrowid


def update_exercise_answer(conn, answer_id, text, is_correct, sort_order):
    conn.execute("UPDATE exercise_answers SET answer_text = ?, is_correct = ?, sort_order = ? WHERE id = ?", (text, 1 if is_correct else 0, sort_order, answer_id))


def park_exercise_answer_orders(conn, exercise_id):
    """Answers are renumbered in one go; the UNIQUE (exercise_id, sort_order) would trip mid-way, so move them out of the way first."""
    conn.execute("UPDATE exercise_answers SET sort_order = sort_order + 1000 WHERE exercise_id = ?", (exercise_id,))


# ---------- situations ----------
def insert_situation(conn, f, now):
    return conn.execute(
        """INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, goal, setting, partner_name, partner_role, difficulty, sort_order, status, updated_at, revision)
           VALUES (:language_id, :cefr, :topic_id, :slug, :title, :description, :goal, :setting, :partner_name, :partner_role, :difficulty, :sort_order, 'draft', :now, 1)""",
        {**f, "now": now}).lastrowid


def step_row(conn, situation_id, step_id):
    row = conn.execute("SELECT id, situation_id, language_id, sort_order, kind, prompt, prompt_meaning, item_id, explanation FROM situation_steps WHERE id = ? AND situation_id = ?",
                       (step_id, situation_id)).fetchone()
    return dict(row) if row else None


def step_sort_taken(conn, situation_id, sort_order, exclude_id=None):
    return conn.execute("SELECT 1 FROM situation_steps WHERE situation_id = ? AND sort_order = ? AND id IS NOT ?", (situation_id, sort_order, exclude_id)).fetchone() is not None


def next_step_sort(conn, situation_id):
    return conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM situation_steps WHERE situation_id = ?", (situation_id,)).fetchone()[0]


def insert_step(conn, situation_id, language_id, sort_order, kind, prompt, prompt_meaning, item_id, explanation):
    return conn.execute(
        "INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, prompt, prompt_meaning, item_id, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (situation_id, language_id, sort_order, kind, prompt, prompt_meaning, item_id, explanation)).lastrowid


def update_step(conn, step_id, fields):
    if fields:
        conn.execute(f"UPDATE situation_steps SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), step_id])


def step_answers(conn, step_id):
    return [dict(r) for r in conn.execute("SELECT id, answer_text AS text, is_correct, sort_order FROM situation_step_answers WHERE step_id = ? ORDER BY sort_order", (step_id,))]


def step_answer_used(conn, answer_id):
    return conn.execute("SELECT 1 FROM situation_step_attempts WHERE answer_id = ? LIMIT 1", (answer_id,)).fetchone() is not None


def insert_step_answer(conn, step_id, text, is_correct, sort_order):
    return conn.execute("INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES (?, ?, ?, ?)", (step_id, text, 1 if is_correct else 0, sort_order)).lastrowid


def update_step_answer(conn, answer_id, text, is_correct, sort_order):
    conn.execute("UPDATE situation_step_answers SET answer_text = ?, is_correct = ?, sort_order = ? WHERE id = ?", (text, 1 if is_correct else 0, sort_order, answer_id))


def park_step_answer_orders(conn, step_id):
    conn.execute("UPDATE situation_step_answers SET sort_order = sort_order + 1000 WHERE step_id = ?", (step_id,))


# ---------- listening ----------
def insert_activity(conn, f, now):
    return conn.execute(
        """INSERT INTO listening_activities(language_id, cefr_code, topic_id, item_id, slug, title, mode, prompt, difficulty, sort_order, status, updated_at, revision)
           VALUES (:language_id, :cefr, :topic_id, :item_id, :slug, :title, :mode, :prompt, :difficulty, :sort_order, 'draft', :now, 1)""", {**f, "now": now}).lastrowid


def option_row(conn, activity_id, option_id):
    row = conn.execute("SELECT id, activity_id, language_id, item_id, sort_order FROM listening_options WHERE id = ? AND activity_id = ?", (option_id, activity_id)).fetchone()
    return dict(row) if row else None


def options_of(conn, activity_id):
    return [dict(r) for r in conn.execute("SELECT id, item_id, sort_order FROM listening_options WHERE activity_id = ? ORDER BY sort_order", (activity_id,))]


def option_has_attempts(conn, option_id):
    return conn.execute("SELECT 1 FROM listening_attempts WHERE option_id = ? LIMIT 1", (option_id,)).fetchone() is not None


def activity_has_attempts(conn, activity_id):
    return conn.execute("SELECT 1 FROM listening_attempts WHERE activity_id = ? LIMIT 1", (activity_id,)).fetchone() is not None


def insert_option(conn, activity_id, language_id, item_id, sort_order):
    return conn.execute("INSERT INTO listening_options(activity_id, language_id, item_id, sort_order) VALUES (?, ?, ?, ?)", (activity_id, language_id, item_id, sort_order)).lastrowid


def update_option(conn, option_id, fields):
    if fields:
        conn.execute(f"UPDATE listening_options SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), option_id])


def option_sort_taken(conn, activity_id, sort_order, exclude_id=None):
    return conn.execute("SELECT 1 FROM listening_options WHERE activity_id = ? AND sort_order = ? AND id IS NOT ?", (activity_id, sort_order, exclude_id)).fetchone() is not None


def option_item_taken(conn, activity_id, item_id, exclude_id=None):
    return conn.execute("SELECT 1 FROM listening_options WHERE activity_id = ? AND item_id = ? AND id IS NOT ?", (activity_id, item_id, exclude_id)).fetchone() is not None


# ---------- evidence guards ----------
def exercise_has_attempts(conn, exercise_id):
    return conn.execute("SELECT 1 FROM exercise_attempts WHERE exercise_id = ? LIMIT 1", (exercise_id,)).fetchone() is not None


def step_has_attempts(conn, step_id):
    return conn.execute("SELECT 1 FROM situation_step_attempts WHERE step_id = ? LIMIT 1", (step_id,)).fetchone() is not None


# ---------- vocabulary ----------
VOCAB_REFERENCES = (
    "SELECT 1 FROM lesson_vocabulary WHERE item_id = :i", "SELECT 1 FROM exercises WHERE item_id = :i", "SELECT 1 FROM situation_steps WHERE item_id = :i",
    "SELECT 1 FROM listening_activities WHERE item_id = :i", "SELECT 1 FROM listening_options WHERE item_id = :i", "SELECT 1 FROM grammar_examples WHERE item_id = :i",
    "SELECT 1 FROM vocabulary_examples WHERE item_id = :i OR example_item_id = :i", "SELECT 1 FROM speaking_sessions WHERE item_id = :i",
    "SELECT 1 FROM ai_micro_lessons WHERE item_id = :i", "SELECT 1 FROM weaknesses WHERE item_id = :i",
)


def vocabulary_is_referenced(conn, item_id):
    return any(conn.execute(sql, {"i": item_id}).fetchone() for sql in VOCAB_REFERENCES)


def vocabulary_used_by_published(conn, item_id):
    """True when a PUBLISHED lesson, situation or listening activity uses the item (directly, through an exercise/step, or as a listening option)."""
    sql = """SELECT 1 FROM lesson_vocabulary lv JOIN lessons l ON l.id = lv.lesson_id WHERE lv.item_id = :i AND l.status = 'published'
             UNION ALL SELECT 1 FROM exercises e JOIN lessons l ON l.id = e.lesson_id WHERE e.item_id = :i AND l.status = 'published'
             UNION ALL SELECT 1 FROM situation_steps s JOIN situations x ON x.id = s.situation_id WHERE s.item_id = :i AND x.status = 'published'
             UNION ALL SELECT 1 FROM listening_activities a WHERE a.item_id = :i AND a.status = 'published'
             UNION ALL SELECT 1 FROM listening_options o JOIN listening_activities a ON a.id = o.activity_id WHERE o.item_id = :i AND a.status = 'published'
             LIMIT 1"""
    return conn.execute(sql, {"i": item_id}).fetchone() is not None


def vocabulary_text_taken(conn, language_id, text, exclude_id=None):
    return conn.execute("SELECT 1 FROM vocabulary_items WHERE language_id = ? AND text = ? AND id IS NOT ?", (language_id, text, exclude_id)).fetchone() is not None


def insert_vocabulary(conn, language_id, cefr, kind, text, pronunciation):
    return conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text, pronunciation) VALUES (?, ?, ?, ?, ?)", (language_id, cefr, kind, text, pronunciation)).lastrowid


def update_vocabulary(conn, item_id, fields):
    if fields:
        conn.execute(f"UPDATE vocabulary_items SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), item_id])


def translation_row(conn, item_id, language_id):
    row = conn.execute("SELECT meaning, natural FROM vocabulary_translations WHERE item_id = ? AND language_id = ?", (item_id, language_id)).fetchone()
    return dict(row) if row else None


def upsert_translation(conn, item_id, language_id, meaning, natural):
    conn.execute("""INSERT INTO vocabulary_translations(item_id, language_id, meaning, natural) VALUES (?, ?, ?, ?)
                    ON CONFLICT(item_id, language_id) DO UPDATE SET meaning = excluded.meaning, natural = excluded.natural""", (item_id, language_id, meaning, natural))


def translations_of(conn, item_id):
    return [dict(r) for r in conn.execute(
        """SELECT l.code AS language, t.meaning, t.natural FROM vocabulary_translations t JOIN languages l ON l.id = t.language_id WHERE t.item_id = ? ORDER BY l.code""", (item_id,))]


def vocabulary_usage(conn, item_id):
    """How many lessons / situations / listening activities (any status) use the item. Counts of content, never of learners."""
    return {
        "lessons": conn.execute("SELECT COUNT(DISTINCT lesson_id) FROM (SELECT lesson_id FROM lesson_vocabulary WHERE item_id = :i UNION SELECT lesson_id FROM exercises WHERE item_id = :i)", {"i": item_id}).fetchone()[0],
        "situations": conn.execute("SELECT COUNT(DISTINCT situation_id) FROM situation_steps WHERE item_id = :i", {"i": item_id}).fetchone()[0],
        "listening_activities": conn.execute("SELECT COUNT(DISTINCT activity_id) FROM (SELECT id AS activity_id FROM listening_activities WHERE item_id = :i UNION SELECT activity_id FROM listening_options WHERE item_id = :i)", {"i": item_id}).fetchone()[0],
    }


def list_vocabulary(conn, language_id, cefr, kind, q, limit, offset):
    where, params = ["1"], []
    if language_id is not None:
        where.append("v.language_id = ?")
        params.append(language_id)
    if cefr:
        where.append("v.cefr_code = ?")
        params.append(cefr)
    if kind:
        where.append("v.kind = ?")
        params.append(kind)
    if q:
        where.append("(v.text LIKE ? ESCAPE '\\' OR v.pronunciation LIKE ? ESCAPE '\\')")
        params += [_like(q), _like(q)]
    en = english_language_id(conn)
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM vocabulary_items v WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT v.id, l.code AS language, v.cefr_code AS cefr, v.kind, v.text, v.pronunciation,
                   EXISTS (SELECT 1 FROM vocabulary_translations t WHERE t.item_id = v.id AND t.language_id = ?) AS has_english
            FROM vocabulary_items v JOIN languages l ON l.id = v.language_id WHERE {clause} ORDER BY v.language_id, v.id LIMIT ? OFFSET ?""", [en, *params, limit, offset]).fetchall()
    return total, [{**dict(r), "has_english": bool(r["has_english"])} for r in rows]


# ---------- topics ----------
def list_topics(conn):
    return [dict(r) for r in conn.execute(
        """SELECT t.id, t.slug, t.name, t.icon,
                  (SELECT COUNT(*) FROM lesson_topics x WHERE x.topic_id = t.id) AS lessons,
                  (SELECT COUNT(*) FROM situations x WHERE x.topic_id = t.id) AS situations,
                  (SELECT COUNT(*) FROM listening_activities x WHERE x.topic_id = t.id) AS listening_activities
           FROM topics t ORDER BY t.slug""")]


def topic_row(conn, topic_id_):
    row = conn.execute("SELECT id, slug, name, icon FROM topics WHERE id = ?", (topic_id_,)).fetchone()
    return dict(row) if row else None


def insert_topic(conn, slug, name, icon):
    return conn.execute("INSERT INTO topics(slug, name, icon) VALUES (?, ?, ?)", (slug, name, icon)).lastrowid


def update_topic(conn, topic_id_, name, icon):
    conn.execute("UPDATE topics SET name = ?, icon = ? WHERE id = ?", (name, icon, topic_id_))


# ---------- reference data (read-only) ----------
def reference_languages(conn):
    out = []
    for r in conn.execute("SELECT id, code, name, native_name FROM languages ORDER BY code"):
        levels = [x[0] for x in conn.execute("SELECT l.cefr_code FROM language_levels l JOIN cefr_levels c ON c.code = l.cefr_code WHERE l.language_id = ? ORDER BY c.rank", (r["id"],))]
        out.append({"code": r["code"], "name": r["name"], "native_name": r["native_name"], "cefr_levels": levels})
    return out


def reference_cefr(conn):
    return [dict(r) for r in conn.execute("SELECT code, rank, label FROM cefr_levels ORDER BY rank")]


def reference_age_groups(conn):
    return [dict(r) for r in conn.execute("SELECT code, label, min_age, max_age FROM age_groups ORDER BY min_age")]


# ---------- lists and details ----------
def list_units(conn, entity_type, status, language_id, cefr, q, limit, offset, extra_counts):
    table = LIFECYCLE_TABLES[entity_type]
    where, params = ["1"], []
    if status:
        where.append("u.status = ?")
        params.append(status)
    if language_id is not None:
        where.append("u.language_id = ?")
        params.append(language_id)
    if cefr:
        where.append("u.cefr_code = ?")
        params.append(cefr)
    if q:
        where.append("(u.title LIKE ? ESCAPE '\\' OR u.slug LIKE ? ESCAPE '\\')")
        params += [_like(q), _like(q)]
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM {table} u WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT u.id, u.slug, u.title, l.code AS language, u.cefr_code AS cefr, u.status, u.revision, u.sort_order, u.updated_at, u.published_at, u.archived_at
                   {extra_counts}
            FROM {table} u JOIN languages l ON l.id = u.language_id WHERE {clause}
            ORDER BY u.language_id, (SELECT rank FROM cefr_levels WHERE code = u.cefr_code), u.sort_order, u.id LIMIT ? OFFSET ?""", [*params, limit, offset]).fetchall()
    return total, [dict(r) for r in rows]


LESSON_COUNTS = """, (SELECT COUNT(*) FROM exercises x WHERE x.lesson_id = u.id) AS exercises,
                      (SELECT COUNT(*) FROM lesson_vocabulary x WHERE x.lesson_id = u.id) AS vocabulary"""
SITUATION_COUNTS = """, (SELECT COUNT(*) FROM situation_steps x WHERE x.situation_id = u.id) AS steps"""
LISTENING_COUNTS = """, (SELECT COUNT(*) FROM listening_options x WHERE x.activity_id = u.id) AS options"""


def unit_languages(conn, row):
    r = conn.execute("SELECT code, name FROM languages WHERE id = ?", (row["language_id"],)).fetchone()
    return {"code": r["code"], "name": r["name"]}
