import re
import sqlite3
from pathlib import Path

import pytest

from backend.db import connect

CONTENT_JS = (Path(__file__).parent.parent / "frontend" / "content.js").read_text(encoding="utf-8")


def test_foreign_keys_enabled_on_every_connection(db_path):
    with connect(db_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_foreign_key_violation_rejected(db_path):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute("INSERT INTO city_languages(city_id, language_id, sort_order) VALUES (999, 1, 1)")


def test_language_in_use_cannot_be_deleted(db_path):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute("DELETE FROM languages WHERE code = 'hi'")


def test_deleting_city_cascades_to_city_languages(db_path):
    with connect(db_path) as conn:
        conn.execute("DELETE FROM cities WHERE slug = 'delhi'")
        assert conn.execute("SELECT COUNT(*) FROM city_languages cl LEFT JOIN cities c ON c.id = cl.city_id WHERE c.id IS NULL").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM cities WHERE slug='delhi'").fetchone()[0] == 0


@pytest.mark.parametrize("sql", [
    "INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('hi', 'Other', 'x', 'x')",  # duplicate code
    "INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('xx', 'Hindi', 'x', 'x')",  # duplicate name
    "INSERT INTO languages(code, name, native_name, tts_locale) VALUES ('xx', NULL, 'x', 'x')",     # NOT NULL
    "INSERT INTO users(handle, display_name) VALUES ('demo-alex', 'Dup')",
    "INSERT INTO cefr_levels(code, rank, label) VALUES ('Z9', 1, 'dup rank')",
    "INSERT INTO cefr_levels(code, rank, label) VALUES ('Z9', 0, 'bad rank')",
    "INSERT INTO cities(slug, name, flag, emoji, tagline, blurb, is_ready) VALUES ('x','x','x','x','x','x', 2)",
    "INSERT INTO city_languages(city_id, language_id, sort_order) SELECT city_id, language_id, 9 FROM city_languages LIMIT 1",  # duplicate PK
])
def test_constraints_reject_bad_rows(db_path, sql):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(db_path) as conn:
            conn.execute(sql)


def test_seed_languages_match_prototype(db_path):
    block = CONTENT_JS.split("window.LANGUAGES")[1].split("];")[0]
    expected = re.findall(r'code: "(\w+)"', block)
    with connect(db_path) as conn:
        got = [r[0] for r in conn.execute("SELECT code FROM languages ORDER BY id")]
    assert got == expected and len(got) == 19                 # Marathi joined in migration 0030, Kannada in 0036, Tamil in 0039, Bengali in 0047, Telugu and Urdu in 0050, Kashmiri and Dogri in 0054


def test_seed_cities_match_prototype(db_path):
    block = CONTENT_JS.split("window.CITIES")[1].split("];")[0]
    cities = re.findall(r'id: "(\w+)".*?langs: \[([^\]]*)\].*?ready: (true|false)', block)
    with connect(db_path) as conn:
        for slug, langs, ready in cities:
            codes = re.findall(r'"(\w+)"', langs)
            got = [r[0] for r in conn.execute(
                "SELECT l.code FROM city_languages cl JOIN cities c ON c.id=cl.city_id JOIN languages l ON l.id=cl.language_id "
                "WHERE c.slug=? ORDER BY cl.sort_order", (slug,))]
            assert got == codes
            assert conn.execute("SELECT is_ready FROM cities WHERE slug=?", (slug,)).fetchone()[0] == (ready == "true")
        assert conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0] == len(cities) == 12                    # Puducherry joined in 0043, Jaipur and Lucknow in 0046, Kolkata in 0047, Bhopal in 0053, J&K in 0054


def test_seed_cefr_and_user(db_path):
    with connect(db_path) as conn:
        assert [r[0] for r in conn.execute("SELECT code FROM cefr_levels ORDER BY rank")] == ["A1", "A2", "B1", "B2", "C1", "C2"]
        assert conn.execute("SELECT display_name FROM users WHERE handle='demo-alex'").fetchone()[0] == "Alex"
