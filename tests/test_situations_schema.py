import sqlite3

import pytest

from backend.db import connect

HI = "(SELECT id FROM languages WHERE code='hi')"
TOPIC = "(SELECT id FROM topics WHERE slug='food')"


def one(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def fails(db_path, *statements):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            for s in statements:
                conn.execute(s)


def new_situation(slug="extra", order=50, difficulty=1, status="published", cefr="A1", lang=HI, topic=TOPIC, persona="NULL, NULL"):
    return (f"INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, partner_name, partner_role, difficulty, sort_order, status) "
            f"VALUES ({lang}, '{cefr}', {topic}, '{slug}', 't', 'd', {persona}, {difficulty}, {order}, '{status}')")


# ---------- situations: language, CEFR, topic ----------
def test_situation_requires_supported_language_level_combination(db_path):
    fails(db_path, new_situation(cefr="B1"))
    fails(db_path, new_situation(lang="(SELECT id FROM languages WHERE code='es')", cefr="A1"))


def test_newly_supported_combination_needs_no_code_change(db_path):
    with connect(db_path) as conn:
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES ((SELECT id FROM languages WHERE code='hi'), 'B1')")
        conn.execute(new_situation(cefr="B1"))
        assert one(conn, "SELECT COUNT(*) FROM situations WHERE cefr_code='B1' AND language_id = (SELECT id FROM languages WHERE code='hi')") == 1   # Marathi's B1: 0035


@pytest.mark.parametrize("kwargs", [
    {"slug": "food"},                # duplicate slug within the language
    {"order": 1},                    # duplicate ordering within language+level
    {"order": 0},                    # sort_order >= 1
    {"difficulty": 0}, {"difficulty": 6},
    {"status": "live"},
    {"topic": "(SELECT 999)"},       # unknown topic
])
def test_situation_constraints(db_path, kwargs):
    fails(db_path, new_situation(**{"slug": "extra", **kwargs}))


def test_partner_name_and_role_go_together(db_path):
    fails(db_path, new_situation(persona="'Raju', NULL"))
    fails(db_path, new_situation(persona="NULL, 'Driver'"))
    with connect(db_path) as conn:
        conn.execute(new_situation(persona="'Raju', 'Driver'"))


def test_default_status_is_draft(db_path):
    with connect(db_path) as conn:
        conn.execute(f"INSERT INTO situations(language_id, cefr_code, topic_id, slug, title, description, difficulty, sort_order) VALUES ({HI}, 'A1', {TOPIC}, 'd', 't', 'd', 1, 60)")
        assert one(conn, "SELECT status FROM situations WHERE slug='d'") == "draft"


def test_topic_in_use_cannot_be_deleted_and_topic_has_many_situations(db_path):
    fails(db_path, "DELETE FROM topics WHERE slug='food'")
    with connect(db_path) as conn:
        conn.execute(new_situation(slug="food-2", order=51))
        assert one(conn, "SELECT COUNT(*) FROM situations s JOIN topics t ON t.id=s.topic_id WHERE t.slug='food' AND s.language_id = (SELECT id FROM languages WHERE code='hi')") == 2


# ---------- ordered steps ----------
def test_steps_are_ordered_and_contiguous_per_situation(db_path):
    with connect(db_path) as conn:
        for sid in [r[0] for r in conn.execute("SELECT id FROM situations")]:
            orders = [r[0] for r in conn.execute("SELECT sort_order FROM situation_steps WHERE situation_id=? ORDER BY sort_order", (sid,))]
            assert orders == list(range(1, len(orders) + 1))


STEP = "INSERT INTO situation_steps(situation_id, language_id, sort_order, kind, prompt, item_id) VALUES ({sit}, {lang}, {order}, '{kind}', {prompt}, {item})"
FOOD = "(SELECT id FROM situations WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi'))"
ITEM = "(SELECT id FROM vocabulary_items WHERE pronunciation='Paani milega?')"


@pytest.mark.parametrize("kwargs", [
    {"order": 1},                                                   # order slot taken
    {"order": 0},
    {"order": 99, "kind": "monologue"},                             # kind vocabulary
    {"order": 99, "kind": "learn_phrase", "prompt": "NULL", "item": "NULL"},   # learn needs an item
    {"order": 99, "kind": "translate", "prompt": "NULL"},           # other kinds need a prompt
    {"order": 99, "kind": "translate", "prompt": "'  '"},
    {"order": 99, "sit": "(SELECT 999)"},                           # unknown situation
])
def test_step_constraints(db_path, kwargs):
    base = {"sit": FOOD, "lang": HI, "order": 99, "kind": "translate", "prompt": "'p'", "item": "NULL"}
    fails(db_path, STEP.format(**{**base, **kwargs}))


def test_all_five_step_kinds_are_supported(db_path):
    with connect(db_path) as conn:
        for i, kind in enumerate(["learn_phrase", "choose_response", "translate", "fill_blank", "conversation"], start=90):
            conn.execute(STEP.format(sit=FOOD, lang=HI, order=i, kind=kind, prompt="NULL" if kind == "learn_phrase" else "'p'",
                                     item=ITEM if kind == "learn_phrase" else "NULL"))
        assert one(conn, "SELECT COUNT(DISTINCT kind) FROM situation_steps") == 5


def test_database_rejects_cross_language_links(db_path):
    with connect(db_path) as conn:
        es = one(conn, "SELECT id FROM languages WHERE code='es'")
        conn.execute("INSERT INTO language_levels(language_id, cefr_code) VALUES (?, 'A1')", (es,))
        conn.execute("INSERT INTO vocabulary_items(language_id, cefr_code, kind, text) VALUES (?, 'A1', 'word', 'hola')", (es,))
        hola = one(conn, "SELECT id FROM vocabulary_items WHERE text='hola'")
        hi = one(conn, "SELECT id FROM languages WHERE code='hi'")
    fails(db_path, STEP.format(sit=FOOD, lang=hi, order=99, kind="learn_phrase", prompt="NULL", item=hola))   # Spanish item in a Hindi situation
    fails(db_path, STEP.format(sit=FOOD, lang=es, order=99, kind="learn_phrase", prompt="NULL", item=hola))   # language disagrees with the situation


def test_deleting_a_situation_cascades_but_keeps_shared_vocabulary(db_path):
    with connect(db_path) as conn:
        sid = one(conn, "SELECT id FROM situations WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        vocab = one(conn, "SELECT COUNT(*) FROM vocabulary_items")
        conn.execute("DELETE FROM situations WHERE id=?", (sid,))
        assert one(conn, "SELECT COUNT(*) FROM situation_steps WHERE situation_id=?", sid) == 0
        assert one(conn, "SELECT COUNT(*) FROM situation_step_answers WHERE step_id NOT IN (SELECT id FROM situation_steps)") == 0
        assert one(conn, "SELECT COUNT(*) FROM vocabulary_items") == vocab


def test_vocabulary_used_by_a_step_cannot_be_deleted(db_path):
    fails(db_path, "DELETE FROM vocabulary_items WHERE id = (SELECT item_id FROM situation_steps WHERE item_id IS NOT NULL LIMIT 1)")


@pytest.mark.parametrize("sql", [
    "INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES (999, 'x', 1, 1)",
    "INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES ((SELECT id FROM situation_steps WHERE kind='choose_response' LIMIT 1), 'x', 2, 50)",
    "INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) VALUES ((SELECT id FROM situation_steps WHERE kind='choose_response' LIMIT 1), ' ', 0, 50)",
    "INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) SELECT step_id, 'other', 0, sort_order FROM situation_step_answers LIMIT 1",  # duplicate slot
    "INSERT INTO situation_step_answers(step_id, answer_text, is_correct, sort_order) SELECT step_id, answer_text, 0, 50 FROM situation_step_answers LIMIT 1",     # duplicate text
])
def test_answer_constraints(db_path, sql):
    fails(db_path, sql)


# ---------- progress tables ----------
def _user(conn):
    return one(conn, "SELECT id FROM users WHERE handle='demo-alex'")


INS = "INSERT INTO situation_step_attempts(user_id, step_id, answer_id, submitted_text, is_correct, attempted_at) VALUES "


def test_attempt_constraints(db_path):
    with connect(db_path) as conn:
        u = _user(conn)
        s1, s2 = [r[0] for r in conn.execute("SELECT id FROM situation_steps WHERE kind='choose_response' ORDER BY id LIMIT 2")]
        a1 = one(conn, "SELECT id FROM situation_step_answers WHERE step_id=? LIMIT 1", s1)
        a2 = one(conn, "SELECT id FROM situation_step_answers WHERE step_id=? LIMIT 1", s2)
    fails(db_path, INS + f"({u}, {s1}, {a2}, NULL, 0, '2026-01-01 00:00:00')")         # option of another step
    fails(db_path, INS + f"({u}, {s1}, {a1}, 'both', 0, '2026-01-01 00:00:00')")       # answer and text together
    fails(db_path, INS + f"({u}, {s1}, {a1}, NULL, 2, '2026-01-01 00:00:00')")         # is_correct domain
    fails(db_path, INS + f"(999, {s1}, {a1}, NULL, 1, '2026-01-01 00:00:00')")         # unknown user
    with connect(db_path) as conn:  # history is kept; an acknowledgement has neither answer nor text
        conn.execute(INS + f"({u}, {s1}, {a1}, NULL, 1, '2026-01-01 00:00:00')")
        conn.execute(INS + f"({u}, {s1}, {a1}, NULL, 1, '2026-01-01 00:00:01')")
        conn.execute(INS + f"({u}, {s1}, NULL, NULL, 1, '2026-01-01 00:00:02')")
        assert one(conn, "SELECT COUNT(*) FROM situation_step_attempts") == 3


def test_situation_progress_constraints_and_cascades(db_path):
    with connect(db_path) as conn:
        u, sid = _user(conn), one(conn, "SELECT id FROM situations WHERE slug='food' AND language_id = (SELECT id FROM languages WHERE code='hi')")
        conn.execute("INSERT INTO situation_progress(user_id, situation_id, started_at) VALUES (?, ?, '2026-01-02 00:00:00')", (u, sid))
        step = one(conn, "SELECT id FROM situation_steps WHERE situation_id=? LIMIT 1", sid)
        conn.execute(INS + f"({u}, {step}, NULL, NULL, 1, '2026-01-02 00:00:00')")
    fails(db_path, f"INSERT INTO situation_progress(user_id, situation_id, started_at) VALUES ({u}, {sid}, '2026-01-03 00:00:00')")   # one row per user+situation
    fails(db_path, f"UPDATE situation_progress SET completed_at='2026-01-01 00:00:00' WHERE user_id={u}")                              # completed before started
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id=?", (u,))
        assert one(conn, "SELECT COUNT(*) FROM situation_progress") == 0
        assert one(conn, "SELECT COUNT(*) FROM situation_step_attempts") == 0
