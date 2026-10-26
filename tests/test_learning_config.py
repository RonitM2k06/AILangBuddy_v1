import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from backend.db import connect
from backend.learner import service as learner_service
from backend.repositories import learner

CONTENT_JS = (Path(__file__).parent.parent / "frontend" / "content.js").read_text(encoding="utf-8")
APP_JS = (Path(__file__).parent.parent / "frontend" / "app.js").read_text(encoding="utf-8")


# ---------- language / CEFR data ----------
def test_language_catalogue_is_complete(client):
    body = client.get("/api/languages").json()["languages"]
    assert {l["code"] for l in body} == set(re.findall(r'code: "(\w+)"', CONTENT_JS.split("window.LANGUAGES")[1].split("];")[0]))


def test_cefr_levels_endpoint(client):
    levels = client.get("/api/cefr-levels").json()["levels"]
    assert [l["code"] for l in levels] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert [l["rank"] for l in levels] == [1, 2, 3, 4, 5, 6]
    assert levels[0] == {"code": "A1", "rank": 1, "label": "Beginner"}


def test_cefr_levels_match_frontend_level_list():
    chips = re.search(r'\["A1", "A2", "B1", "B2", "C1", "C2"\]', APP_JS)
    assert chips, "frontend level chip list changed; keep the catalogue in sync"


def test_language_levels_preserve_prototype_a1_a2_behaviour(client):
    combos = {c["language"]: c["levels"] for c in client.get("/api/language-levels").json()["language_levels"]}
    assert combos == {"en": ["A1", "A2"], "hi": ["A1", "A2"], "hinglish": ["A1", "A2"], "mr": ["A1", "A2", "B1"], "kn": ["A1", "A2", "B1"], "ta": ["A1", "A2", "B1"], "fr": ["A1"], "bn": ["A1", "A2", "B1"], "te": ["A1"], "ur": ["A1"], "ks": ["A1"], "doi": ["A1"]}     # mr: 0031, 0035; kn: 0037, 0038; ta: 0040, 0041; fr: 0044; bn: 0048, 0049; te: 0051; ur: 0052; ks: 0055; doi: 0056


def test_prototype_levels_are_all_supported(db_path):
    """Levels the prototype ships content for (readings) and can assign (placement: A1/A2) are supported."""
    shipped = set(re.findall(r'level: "([ABC]\d)"', CONTENT_JS))
    assert shipped == {"A1"}
    assert 'S().level = score >= 5 ? "A2" : "A1"' in APP_JS  # placement only ever assigns A1/A2
    with connect(db_path) as conn:
        for code in ("hi", "hinglish", "en"):
            lid = learner.get_language_id(conn, code)
            for lvl in ("A1", "A2"):
                assert learner.is_supported_combination(conn, lid, lvl)


@pytest.mark.parametrize("lang,level,supported", [
    ("hi", "A1", True), ("hi", "A2", True), ("hi", "B1", False), ("hi", "C2", False),
    ("es", "A1", False),  # in the catalogue, but no content yet
    ("hi", "Z9", False),
])
def test_combination_check(db_path, lang, level, supported):
    with connect(db_path) as conn:
        assert learner.is_supported_combination(conn, learner.get_language_id(conn, lang), level) is supported


def test_unknown_language_has_no_id(db_path):
    with connect(db_path) as conn:
        assert learner.get_language_id(conn, "xx") is None


# ---------- constraints ----------
@pytest.mark.parametrize("sql", [
    "INSERT INTO language_levels(language_id, cefr_code) VALUES (999, 'A1')",
    "INSERT INTO language_levels(language_id, cefr_code) VALUES (1, 'Z9')",
    "INSERT INTO language_levels(language_id, cefr_code) SELECT language_id, cefr_code FROM language_levels LIMIT 1",  # dup PK
    "DELETE FROM cefr_levels WHERE code = 'A1'",  # still referenced
    "INSERT INTO age_groups(code, label, min_age, max_age) VALUES ('x', 'x', -1, 5)",
    "INSERT INTO age_groups(code, label, min_age, max_age) VALUES ('x', 'x', 30, 20)",
    "INSERT INTO age_groups(code, label, min_age, max_age) VALUES ('child', 'dup code', 40, 50)",
    "INSERT INTO age_groups(code, label, min_age, max_age) VALUES ('x', 'dup min', 10, 50)",
])
def test_config_constraints(db_path, sql):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql)


def _user(conn):
    return conn.execute("SELECT id FROM users WHERE handle='demo-alex'").fetchone()[0]


def _insert(conn, native="1", target="10", level="'A1'", dob="'2000-01-01'"):
    # language ids by seed order: en=1 ... hi=10, hinglish=11
    conn.execute(
        f"INSERT INTO learner_profiles(user_id, native_language_id, target_language_id, cefr_level, date_of_birth) VALUES (?, {native}, {target}, {level}, {dob})",
        (_user(conn),),
    )


def test_profile_row_accepts_valid_combination(db_path):
    with connect(db_path) as conn:
        _insert(conn)
        assert conn.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0] == 1


@pytest.mark.parametrize("kwargs", [
    {"level": "'B1'"},                     # unsupported combination (composite FK)
    {"target": "2", "level": "'A1'"},      # Spanish has no levels
    {"native": "10"},                      # native == target
    {"native": "999"},                     # unknown native language
    {"dob": "'2000-13-45'"},               # not a date
    {"dob": "'01/01/2000'"},               # wrong format
    {"dob": "NULL"},
])
def test_profile_db_constraints(db_path, kwargs):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            _insert(conn, **kwargs)


def test_one_profile_per_user_and_cascade_delete(db_path):
    with connect(db_path) as conn:
        _insert(conn)
        with pytest.raises(sqlite3.IntegrityError):
            _insert(conn)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE handle='demo-alex'")
        assert conn.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0] == 0


def test_language_in_use_by_profile_cannot_be_deleted(db_path):
    with connect(db_path) as conn:
        _insert(conn)
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute("DELETE FROM language_levels WHERE language_id = 10 AND cefr_code = 'A1'")


# ---------- age groups ----------
def test_age_groups_seeded(db_path):
    with connect(db_path) as conn:
        rows = [tuple(r) for r in conn.execute("SELECT code, min_age, max_age FROM age_groups ORDER BY min_age")]
    assert rows == [("child", 0, 9), ("teen", 10, 17), ("adult", 18, None)]


def test_age_groups_are_contiguous_and_cover_every_age(db_path):
    with connect(db_path) as conn:
        rows = conn.execute("SELECT min_age, max_age FROM age_groups ORDER BY min_age").fetchall()
        assert rows[0]["min_age"] == 0 and rows[-1]["max_age"] is None
        for a, b in zip(rows, rows[1:]):
            assert a["max_age"] + 1 == b["min_age"]
        for age in range(0, 121):  # exactly one group per age
            n = conn.execute("SELECT COUNT(*) FROM age_groups WHERE min_age <= ? AND (max_age IS NULL OR ? <= max_age)", (age, age)).fetchone()[0]
            assert n == 1


@pytest.mark.parametrize("age,code", [(0, "child"), (9, "child"), (10, "teen"), (17, "teen"), (18, "adult"), (45, "adult"), (120, "adult")])
def test_age_group_lookup(db_path, age, code):
    with connect(db_path) as conn:
        assert learner.age_group_for_age(conn, age)["code"] == code


@pytest.mark.parametrize("dob,on,age", [
    (date(2010, 6, 15), date(2020, 6, 14), 9),    # day before 10th birthday
    (date(2010, 6, 15), date(2020, 6, 15), 10),   # on the birthday
    (date(2000, 2, 29), date(2021, 2, 28), 20),   # leap-day birth, before the anniversary
    (date(2000, 2, 29), date(2021, 3, 1), 21),
    (date(2008, 1, 1), date(2026, 1, 1), 18),     # turns adult exactly on the 18th birthday
])
def test_age_calculation(dob, on, age):
    assert learner_service.age_on(dob, on) == age
