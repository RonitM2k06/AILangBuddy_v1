"""The seeded listening set must be built from the existing curriculum and obey its own design."""
import re
from pathlib import Path

from backend.db import connect

from .test_situations_seed import APP, pack_phrases

ROOT = Path(__file__).parent.parent / "frontend"
SOS = re.findall(r'\{ hi: "([^"]*)", roman: "([^"]*)", en: "([^"]*)" \}', APP.split("window.SOS_LIST")[1].split("]);")[0])
DAY_ORDER = ["greetings", "transport", "food", "shopping", "directions", "college", "smalltalk"]


def activities(conn):
    return [dict(r) for r in conn.execute(
        """SELECT a.id, a.slug, a.title, a.mode, a.difficulty, a.sort_order, a.status, a.cefr_code, t.slug AS topic, v.text AS item_text, l.code AS lang
           FROM listening_activities a JOIN topics t ON t.id=a.topic_id JOIN vocabulary_items v ON v.id=a.item_id JOIN languages l ON l.id=a.language_id
           WHERE l.code = 'hi' ORDER BY a.sort_order""")]                       # the Hindi seed (Marathi's come from 0033: tests/test_marathi_learning.py)


def option_texts(conn, activity_id):
    return [r[0] for r in conn.execute("SELECT v.text FROM listening_options o JOIN vocabulary_items v ON v.id=o.item_id WHERE o.activity_id=? ORDER BY o.sort_order", (activity_id,))]


def test_small_published_hindi_a1_set(db_path):
    with connect(db_path) as conn:
        acts = activities(conn)
        assert len(acts) == 15 and conn.execute("SELECT COUNT(*) FROM listening_options WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 45
    assert {(a["lang"], a["cefr_code"], a["status"]) for a in acts} == {("hi", "A1", "published")}
    assert [a["sort_order"] for a in acts] == list(range(1, 16))
    assert len({a["title"] for a in acts}) == 15 and len({a["slug"] for a in acts}) == 15


def test_activities_play_existing_pack_phrases(db_path):
    phrases = pack_phrases()
    with connect(db_path) as conn:
        by_slug = {a["slug"]: a for a in activities(conn)}
        for key in DAY_ORDER:
            texts = [hi for hi, _ in phrases[key]]
            meaning, phrase = by_slug[f"{key}-meaning"], by_slug[f"{key}-phrase"]
            assert (meaning["mode"], meaning["difficulty"], meaning["item_text"], meaning["topic"]) == ("choose_meaning", 1, texts[1], key)
            assert (phrase["mode"], phrase["difficulty"], phrase["item_text"], phrase["topic"]) == ("choose_phrase", 2, texts[2], key)
            # options: the played phrase plus the next two phrases of the same day, nothing invented
            k = len(texts)
            assert sorted(option_texts(conn, meaning["id"])) == sorted([texts[1], texts[2 % k], texts[3 % k]])
            assert sorted(option_texts(conn, phrase["id"])) == sorted([texts[2], texts[3 % k], texts[4 % k]])


def test_emergency_activity_uses_the_sos_phrases(db_path):
    assert len(SOS) == 5
    with connect(db_path) as conn:
        a = next(x for x in activities(conn) if x["slug"] == "emergency-meaning")
        assert a["item_text"] == SOS[1][0] and a["topic"] == "emergency"
        assert sorted(option_texts(conn, a["id"])) == sorted([SOS[1][0], SOS[2][0], SOS[3][0]])


def test_every_activity_is_answerable_and_well_formed(db_path):
    with connect(db_path) as conn:
        for a in activities(conn):
            opts = conn.execute("SELECT item_id FROM listening_options WHERE activity_id=? ORDER BY sort_order", (a["id"],)).fetchall()
            played = conn.execute("SELECT item_id FROM listening_activities WHERE id=?", (a["id"],)).fetchone()[0]
            items = [o[0] for o in opts]
            assert len(items) == 3 and len(set(items)) == 3
            assert items.count(played) == 1                                   # exactly one correct option
            langs = {r[0] for r in conn.execute(f"SELECT language_id FROM vocabulary_items WHERE id IN ({','.join(map(str, items))})")}
            assert len(langs) == 1                                             # all options in the activity's language
            # every option has a meaning (choose_meaning shows it) and text (choose_phrase shows it)
            for i in items:
                assert conn.execute("SELECT COUNT(*) FROM vocabulary_translations WHERE item_id=?", (i,)).fetchone()[0] >= 1


def test_the_correct_option_position_is_not_constant(db_path):
    with connect(db_path) as conn:
        positions = set()
        for a in activities(conn):
            positions.add(conn.execute("SELECT o.sort_order FROM listening_options o JOIN listening_activities l ON l.id=o.activity_id WHERE o.activity_id=? AND o.item_id=l.item_id", (a["id"],)).fetchone()[0])
    assert positions == {1, 2, 3}


def test_topics_follow_the_pack_day_order_and_seed_ships_no_audio_files(db_path):
    with connect(db_path) as conn:
        assert [a["topic"] for a in activities(conn) if a["slug"].endswith("-meaning")] == DAY_ORDER + ["emergency"]
        assert conn.execute("SELECT COUNT(*) FROM audio_assets").fetchone()[0] == 0      # playback is browser TTS until assets are added
        assert conn.execute("SELECT COUNT(*) FROM audio_sessions").fetchone()[0] == 0


def test_seed_reuses_existing_vocabulary_without_adding_any(db_path):
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 53       # Hindi: unchanged since Phase 5
