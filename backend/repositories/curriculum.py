"""Read access to lessons, vocabulary, grammar and exercises. Takes an open connection."""
from . import age


def _marks(ids):
    return ",".join("?" * len(ids))


def get_learner_context(conn, user_id):
    """The learner's native/target language and the rank of their selected CEFR level, or None without a profile."""
    row = conn.execute(
        """SELECT p.native_language_id, p.target_language_id, c.rank AS max_rank, p.date_of_birth
           FROM learner_profiles p JOIN cefr_levels c ON c.code = p.cefr_level WHERE p.user_id = ?""",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


_LESSON_COLUMNS = """l.id, l.slug, l.title, l.description, l.situation, l.tip, l.cefr_code, l.sort_order"""


def list_available_lessons(conn, language_id, max_rank, age_group_id):
    """Published lessons in the target language at or below the learner's level, easiest first."""
    rows = conn.execute(
        f"""SELECT {_LESSON_COLUMNS} FROM lessons l JOIN cefr_levels c ON c.code = l.cefr_code
            WHERE l.language_id = ? AND l.status = 'published' AND c.rank <= ? AND {age.lesson()}
            ORDER BY c.rank, l.sort_order""",
        (language_id, max_rank, age_group_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_available_lesson(conn, lesson_id, language_id, max_rank, age_group_id):
    row = conn.execute(
        f"""SELECT {_LESSON_COLUMNS} FROM lessons l JOIN cefr_levels c ON c.code = l.cefr_code
            WHERE l.id = ? AND l.language_id = ? AND l.status = 'published' AND c.rank <= ? AND {age.lesson()}""",
        (lesson_id, language_id, max_rank, age_group_id),
    ).fetchone()
    return dict(row) if row else None


def topics_for_lessons(conn, lesson_ids):
    if not lesson_ids:
        return {}
    rows = conn.execute(
        f"""SELECT lt.lesson_id, t.slug, t.name, t.icon FROM lesson_topics lt JOIN topics t ON t.id = lt.topic_id
            WHERE lt.lesson_id IN ({_marks(lesson_ids)}) ORDER BY t.slug""",
        lesson_ids,
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["lesson_id"], []).append({"slug": r["slug"], "name": r["name"], "icon": r["icon"]})
    return out


def vocabulary_for_lesson(conn, lesson_id, native_id, fallback_id):
    """Lesson items with meanings in the learner's native language, falling back to the fallback language."""
    rows = conn.execute(
        """SELECT v.id, v.kind, v.text, v.pronunciation,
                  COALESCE(t.meaning, f.meaning) AS meaning, COALESCE(t.natural, f.natural) AS natural
           FROM lesson_vocabulary lv
           JOIN vocabulary_items v ON v.id = lv.item_id
           LEFT JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = ?
           LEFT JOIN vocabulary_translations f ON f.item_id = v.id AND f.language_id = ?
           WHERE lv.lesson_id = ? ORDER BY lv.sort_order""",
        (native_id, fallback_id, lesson_id),
    ).fetchall()
    return [dict(r) for r in rows]


def examples_for_items(conn, item_ids, native_id, fallback_id):
    if not item_ids:
        return {}
    rows = conn.execute(
        f"""SELECT ve.item_id, v.id, v.text, v.pronunciation, COALESCE(t.meaning, f.meaning) AS meaning
            FROM vocabulary_examples ve
            JOIN vocabulary_items v ON v.id = ve.example_item_id
            LEFT JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = ?
            LEFT JOIN vocabulary_translations f ON f.item_id = v.id AND f.language_id = ?
            WHERE ve.item_id IN ({_marks(item_ids)}) ORDER BY ve.item_id, v.id""",
        [native_id, fallback_id, *item_ids],
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["item_id"], []).append({"text": r["text"], "pronunciation": r["pronunciation"], "meaning": r["meaning"]})
    return out


def grammar_for_lesson(conn, lesson_id, native_id, fallback_id):
    topics = conn.execute(
        """SELECT g.id, g.slug, COALESCE(t.title, f.title) AS title, COALESCE(t.explanation, f.explanation) AS explanation
           FROM lesson_grammar lg
           JOIN grammar_topics g ON g.id = lg.grammar_topic_id
           LEFT JOIN grammar_topic_texts t ON t.grammar_topic_id = g.id AND t.language_id = ?
           LEFT JOIN grammar_topic_texts f ON f.grammar_topic_id = g.id AND f.language_id = ?
           WHERE lg.lesson_id = ? ORDER BY g.sort_order""",
        (native_id, fallback_id, lesson_id),
    ).fetchall()
    topics = [dict(r) for r in topics]
    if not topics:
        return []
    ids = [t["id"] for t in topics]
    rows = conn.execute(
        f"""SELECT ge.grammar_topic_id, v.text, v.pronunciation, COALESCE(t.meaning, f.meaning) AS meaning
            FROM grammar_examples ge
            JOIN vocabulary_items v ON v.id = ge.item_id
            LEFT JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = ?
            LEFT JOIN vocabulary_translations f ON f.item_id = v.id AND f.language_id = ?
            WHERE ge.grammar_topic_id IN ({_marks(ids)}) ORDER BY ge.grammar_topic_id, ge.sort_order""",
        [native_id, fallback_id, *ids],
    ).fetchall()
    examples = {}
    for r in rows:
        examples.setdefault(r["grammar_topic_id"], []).append({"text": r["text"], "pronunciation": r["pronunciation"], "meaning": r["meaning"]})
    return [{"slug": t["slug"], "title": t["title"], "explanation": t["explanation"], "examples": examples.get(t["id"], [])} for t in topics]


def exercises_for_lesson(conn, lesson_id):
    """Learner-facing exercise data: never includes which answers are correct."""
    exercises = [dict(r) for r in conn.execute(
        "SELECT id, kind, prompt FROM exercises WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,)).fetchall()]
    mc_ids = [e["id"] for e in exercises if e["kind"] == "multiple_choice"]
    options = {}
    if mc_ids:
        for r in conn.execute(
            f"SELECT id, exercise_id, answer_text FROM exercise_answers WHERE exercise_id IN ({_marks(mc_ids)}) ORDER BY exercise_id, sort_order", mc_ids):
            options.setdefault(r["exercise_id"], []).append({"id": r["id"], "text": r["answer_text"]})
    for e in exercises:
        if e["kind"] == "multiple_choice":
            e["options"] = options.get(e["id"], [])
    return exercises


def get_exercise(conn, exercise_id):
    row = conn.execute(
        "SELECT id, lesson_id, language_id, kind, explanation FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    return dict(row) if row else None


def answers_for_exercise(conn, exercise_id):
    """Server-side only: includes is_correct."""
    return [dict(r) for r in conn.execute(
        "SELECT id, answer_text, is_correct FROM exercise_answers WHERE exercise_id = ? ORDER BY sort_order", (exercise_id,)).fetchall()]
