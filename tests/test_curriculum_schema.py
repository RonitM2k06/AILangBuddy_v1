import sqlite3

import pytest

from backend.db import connect


def lang(conn, code):
    return conn.execute("SELECT id FROM languages WHERE code = ?", (code,)).fetchone()[0]


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def fails(db_path, *statements):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            for s in statements:
                conn.execute(s) if isinstance(s, str) else conn.execute(*s)


HI = "(SELECT id FROM languages WHERE code='hi')"
LESSON = f"INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order, status) VALUES ({HI}, 'A1', '{{slug}}', 't', 'd', {{order}}, '{{status}}')"


# ---------- lessons: language + CEFR ----------
def test_lesson_requires_supported_language_level_combination(db_path):
    fails(db_path, f"INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES ({HI}, 'B1', 'x', 't', 'd', 1)")
    fails(db_path, "INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES ((SELECT id FROM languages WHERE code='es'), 'A1', 'x', 't', 'd', 1)")


def test_lesson_accepts_newly_supported_combination_without_code_changes(db_path):
    with connect(db_path) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES ((SELECT id FROM languages WHERE code='es'), 'A1')")
        conn.execute("INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES ((SELECT id FROM languages WHERE code='es'), 'A1', 'hola', 't', 'd', 1)")
        assert one(conn, "SELECT COUNT(*) FROM lessons WHERE language_id = (SELECT id FROM languages WHERE code='es')") == 1


@pytest.mark.parametrize("kwargs", [
    {"slug": "greetings", "order": 9, "status": "draft"},      # duplicate slug within the language
    {"slug": "new", "order": 1, "status": "draft"},            # duplicate ordering within language+level
    {"slug": "new", "order": 0, "status": "draft"},            # sort_order >= 1
    {"slug": "new", "order": 9, "status": "live"},             # status vocabulary
])
def test_lesson_constraints(db_path, kwargs):
    fails(db_path, LESSON.format(**kwargs))


def test_lesson_default_status_is_draft(db_path):
    with connect(db_path) as conn:
        conn.execute(f"INSERT INTO lessons(language_id, cefr_code, slug, title, description, sort_order) VALUES ({HI}, 'A1', 'n', 't', 'd', 50)")
        assert one(conn, "SELECT status FROM lessons WHERE slug='n'") == "draft"


# ---------- topics ----------
def test_topics_are_many_to_many_with_lessons(db_path):
    with connect(db_path) as conn:
        hindi = "l.language_id = (SELECT id FROM languages WHERE code='hi')"                                            # one language's lessons (Marathi has the same slugs)
        conn.execute(f"INSERT INTO lesson_topics(lesson_id, topic_id) SELECT l.id, t.id FROM lessons l, topics t WHERE l.slug='shopping' AND l.language_id = (SELECT id FROM languages WHERE code='hi') AND t.slug='food' AND {hindi}")
        assert one(conn, f"SELECT COUNT(*) FROM lesson_topics lt JOIN lessons l ON l.id=lt.lesson_id WHERE l.slug='shopping' AND {hindi}") == 2
        assert one(conn, f"SELECT COUNT(*) FROM lesson_topics lt JOIN topics t ON t.id=lt.topic_id JOIN lessons l ON l.id=lt.lesson_id WHERE t.slug='food' AND {hindi}") == 2


def test_topic_link_constraints(db_path):
    fails(db_path, "INSERT INTO lesson_topics(lesson_id, topic_id) SELECT l.id, t.id FROM lessons l, topics t WHERE l.slug='food' AND l.language_id = (SELECT id FROM languages WHERE code='hi') AND t.slug='food'")  # duplicate
    fails(db_path, "INSERT INTO lesson_topics(lesson_id, topic_id) VALUES (999, 1)")
    fails(db_path, "DELETE FROM topics WHERE slug='food'")  # in use


def test_deleting_a_lesson_cascades_to_its_content_links(db_path):
    with connect(db_path) as conn:
        lid = one(conn, "SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        vocab_before = one(conn, "SELECT COUNT(*) FROM vocabulary_items")
        conn.execute("DELETE FROM lessons WHERE id=?", (lid,))
        for t in ("lesson_topics", "lesson_vocabulary", "lesson_grammar", "exercises"):
            assert one(conn, f"SELECT COUNT(*) FROM {t} WHERE lesson_id=?", lid) == 0
        assert one(conn, "SELECT COUNT(*) FROM exercise_answers WHERE exercise_id NOT IN (SELECT id FROM exercises)") == 0
        assert one(conn, "SELECT COUNT(*) FROM vocabulary_items") == vocab_before  # shared vocabulary survives


# ---------- vocabulary ----------
@pytest.mark.parametrize("sql", [
    f"INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES ({HI}, 'A1', 'sentence', 'x')",       # kind
    f"INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES ({HI}, 'A1', 'word', '   ')",          # blank
    f"INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES ({HI}, 'A1', 'word', 'नमस्ते')",        # duplicate text
    f"INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES ({HI}, 'C2', 'word', 'new')",          # unsupported combo
    f"INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (999, 'A1', 'word', 'new')",
    "INSERT INTO vocabulary_translations(item_id, language_id, meaning) SELECT item_id, language_id, 'dup' FROM vocabulary_translations LIMIT 1",  # PK
    "INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (1, (SELECT id FROM languages WHERE code='es'), '  ')",
    "INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (9999, 1, 'orphan')",
])
def test_vocabulary_constraints(db_path, sql):
    fails(db_path, sql)


def test_same_item_can_have_meanings_in_several_native_languages(db_path):
    with connect(db_path) as conn:
        item = one(conn, "SELECT id FROM vocabulary_items WHERE pronunciation='namaste'")
        conn.execute("INSERT INTO vocabulary_translations(item_id, language_id, meaning) VALUES (?, ?, 'hola')", (item, lang(conn, "es")))
        assert one(conn, "SELECT COUNT(*) FROM vocabulary_translations WHERE item_id=?", item) == 2


def test_examples_reuse_vocabulary_and_cannot_reference_themselves(db_path):
    with connect(db_path) as conn:
        namaste = one(conn, "SELECT id FROM vocabulary_items WHERE pronunciation='namaste'")
        ex = conn.execute("SELECT v.kind FROM vocabulary_examples e JOIN vocabulary_items v ON v.id=e.example_item_id WHERE e.item_id=?", (namaste,)).fetchone()
        assert ex["kind"] == "phrase"
        assert one(conn, f"SELECT COUNT(*) FROM vocabulary_items WHERE text LIKE '%नमस्ते%' AND language_id = {HI}") == 2  # stored once, referenced, not copied (Dogri's greeting has its own)
    fails(db_path, f"INSERT INTO vocabulary_examples(item_id, example_item_id, language_id) VALUES ({namaste}, {namaste}, {HI})")


def test_database_rejects_cross_language_links(db_path):
    """A Spanish word cannot be placed in a Hindi lesson, even though both ids exist."""
    with connect(db_path) as conn:
        es = lang(conn, "es")
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (?, 'A1')", (es,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (?, 'A1', 'word', 'hola')", (es,))
        hola = one(conn, "SELECT id FROM vocabulary_items WHERE text='hola'")
        lesson = one(conn, "SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        hi = lang(conn, "hi")
    fails(db_path, f"INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES ({lesson}, {hola}, {hi}, 99)")
    fails(db_path, f"INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) VALUES ({lesson}, {hola}, {es}, 99)")
    fails(db_path, f"INSERT INTO exercises(lesson_id, language_id, kind, prompt, item_id, sort_order) VALUES ({lesson}, {hi}, 'fill_blank', 'p', {hola}, 99)")


def test_lesson_vocabulary_constraints(db_path):
    fails(db_path, "INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) SELECT lesson_id, item_id, language_id, 99 FROM lesson_vocabulary LIMIT 1")  # PK
    fails(db_path, "INSERT INTO lesson_vocabulary(lesson_id, item_id, language_id, sort_order) SELECT lesson_id, (SELECT MAX(id) FROM vocabulary_items), language_id, 1 FROM lesson_vocabulary LIMIT 1")  # order slot taken
    fails(db_path, "DELETE FROM vocabulary_items WHERE id = (SELECT item_id FROM lesson_vocabulary LIMIT 1)")  # in use


# ---------- grammar ----------
def test_grammar_topics_bound_to_language_level_with_translatable_text(db_path):
    with connect(db_path) as conn:
        gid = one(conn, "SELECT id FROM grammar_topics WHERE slug='polite-requests'")
        conn.execute("INSERT INTO grammar_topic_texts(grammar_topic_id, language_id, title, explanation) VALUES (?, ?, 'Peticiones', 'Usa -iye')", (gid, lang(conn, "es")))
        assert one(conn, "SELECT COUNT(*) FROM grammar_topic_texts WHERE grammar_topic_id=?", gid) == 2
    fails(db_path, f"INSERT INTO grammar_topics(language_id, cefr_code, slug, sort_order) VALUES ({HI}, 'B2', 'x', 9)")   # unsupported combo
    fails(db_path, f"INSERT INTO grammar_topics(language_id, cefr_code, slug, sort_order) VALUES ({HI}, 'A1', 'tag-na', 9)")  # duplicate slug
    fails(db_path, f"INSERT INTO grammar_topic_texts(grammar_topic_id, language_id, title, explanation) VALUES ({gid}, {HI}, ' ', 'x')")


def test_grammar_examples_are_vocabulary_items(db_path):
    with connect(db_path) as conn:
        rows = conn.execute("SELECT v.kind FROM grammar_examples ge JOIN vocabulary_items v ON v.id=ge.item_id").fetchall()
        assert rows and all(r["kind"] == "phrase" for r in rows)
    fails(db_path, "INSERT INTO grammar_examples(grammar_topic_id, item_id, language_id, sort_order) SELECT grammar_topic_id, item_id, language_id, 50 FROM grammar_examples LIMIT 1")


# ---------- exercises ----------
def test_exercise_constraints(db_path):
    lesson = "(SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi'))"
    base = f"INSERT INTO exercises(lesson_id, language_id, kind, prompt, sort_order) VALUES ({lesson}, {HI}, "
    fails(db_path, base + "'essay', 'p', 50)")                 # kind
    fails(db_path, base + "'fill_blank', '  ', 50)")           # blank prompt
    fails(db_path, base + "'fill_blank', 'p', 1)")             # order slot taken
    fails(db_path, f"INSERT INTO exercises(lesson_id, language_id, kind, prompt, sort_order) VALUES ({lesson}, (SELECT id FROM languages WHERE code='en'), 'fill_blank', 'p', 50)")  # lesson language mismatch


def test_exercise_subjects_are_optional_links(db_path):
    with connect(db_path) as conn:
        vocab_q = one(conn, "SELECT COUNT(*) FROM exercises WHERE item_id IS NOT NULL AND grammar_topic_id IS NULL")
        grammar_q = one(conn, "SELECT COUNT(*) FROM exercises WHERE grammar_topic_id IS NOT NULL")
        assert vocab_q > 0 and grammar_q > 0


def test_answer_constraints(db_path):
    ex = "(SELECT id FROM exercises WHERE kind='multiple_choice' LIMIT 1)"
    fails(db_path, f"INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES ({ex}, 'x', 2, 50)")
    fails(db_path, f"INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES ({ex}, 'Goodbye only', 0, 50)")  # duplicate text
    fails(db_path, f"INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES ({ex}, 'new', 0, 1)")  # duplicate slot
    fails(db_path, "INSERT INTO exercise_answers(exercise_id, answer_text, is_correct, sort_order) VALUES (9999, 'x', 0, 1)")


# ---------- progress tables ----------
def _user(conn):
    return one(conn, "SELECT id FROM users WHERE handle='demo-alex'")


def test_attempt_constraints(db_path):
    with connect(db_path) as conn:
        u = _user(conn)
        ex1, ex2 = [r[0] for r in conn.execute("SELECT id FROM exercises WHERE kind='multiple_choice' ORDER BY id LIMIT 2")]
        a_of_ex2 = one(conn, "SELECT id FROM exercise_answers WHERE exercise_id=? LIMIT 1", ex2)
        a_of_ex1 = one(conn, "SELECT id FROM exercise_answers WHERE exercise_id=? LIMIT 1", ex1)
    ins = "INSERT INTO exercise_attempts(user_id, exercise_id, answer_id, submitted_text, is_correct, attempted_at) VALUES "
    fails(db_path, ins + f"({u}, {ex1}, NULL, NULL, 0, '2026-01-01 00:00:00')")                 # neither answer nor text
    fails(db_path, ins + f"({u}, {ex1}, {a_of_ex2}, NULL, 0, '2026-01-01 00:00:00')")           # option from another exercise
    fails(db_path, ins + f"({u}, {ex1}, {a_of_ex1}, NULL, 2, '2026-01-01 00:00:00')")           # is_correct domain
    fails(db_path, ins + f"(999, {ex1}, {a_of_ex1}, NULL, 1, '2026-01-01 00:00:00')")           # unknown user
    with connect(db_path) as conn:  # repeated attempts are allowed (history)
        for _ in range(2):
            conn.execute(ins + f"({u}, {ex1}, {a_of_ex1}, NULL, 1, '2026-01-01 00:00:00')")
        assert one(conn, "SELECT COUNT(*) FROM exercise_attempts") == 2


def test_lesson_progress_constraints_and_cascades(db_path):
    with connect(db_path) as conn:
        u, lesson = _user(conn), one(conn, "SELECT id FROM lessons WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        conn.execute("INSERT INTO lesson_progress(user_id, lesson_id, started_at) VALUES (?, ?, '2026-01-02 00:00:00')", (u, lesson))
    fails(db_path, f"INSERT INTO lesson_progress(user_id, lesson_id, started_at) VALUES ({u}, {lesson}, '2026-01-02 00:00:00')")  # one row per user+lesson
    fails(db_path, f"UPDATE lesson_progress SET completed_at='2026-01-01 00:00:00' WHERE user_id={u}")                          # completed before started
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id=?", (u,))
        assert one(conn, "SELECT COUNT(*) FROM lesson_progress") == 0
