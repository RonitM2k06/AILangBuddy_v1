"""The seeded situations must match the prototype content they were migrated from."""
import re
from pathlib import Path

from backend.db import connect

ROOT = Path(__file__).parent.parent / "frontend"
JS = (ROOT / "content.js").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")
SCEN = JS.split("window.SCENARIOS")[1].split("const PLACE_HI")[0]
PACKS = JS.split("window.PACKS")[1].split("window.SCENARIOS")[0]

SCEN_HEAD = re.compile(r'\n  (\w+): \{ category: "(\w+)", icon: "[^"]*", title: "([^"]*)", partner: "([^"]*)", role: "([^"]*)", place: "([^"]*)",\s*\n\s*goal: "([^"]*)",\s*\n\s*opening: \{ text: "([^"]*)", en: "([^"]*)" \},\s*\n\s*start: \[([^\]]*)\]')
REPLY = re.compile(r'text: "([^"]*)", en: "([^"]*)", s: \[([^\]]*)\]')
DAY = re.compile(r'\{ day: (\d+), key: "(\w+)"')
PHRASE = re.compile(r'\{ hi: "([^"]*)", roman: "([^"]*)"')
quoted = lambda s: re.findall(r'"([^"]*)"', s)


def scenarios():
    return [dict(zip(("key", "category", "title", "partner", "role", "place", "goal", "opening", "opening_en", "start"), m)) for m in SCEN_HEAD.findall(SCEN)]


def pack_phrases():
    days = list(DAY.finditer(PACKS))
    out = {}
    for i, m in enumerate(days):
        body = PACKS[m.end(): days[i + 1].start() if i + 1 < len(days) else len(PACKS)]
        out[m.group(2)] = PHRASE.findall(body)
    return out


def steps(conn, slug):
    return [dict(r) for r in conn.execute(
        """SELECT st.id, st.sort_order, st.kind, st.prompt, st.prompt_meaning, v.text AS item_text, v.pronunciation AS item_roman
           FROM situation_steps st JOIN situations s ON s.id = st.situation_id LEFT JOIN vocabulary_items v ON v.id = st.item_id
           WHERE s.slug = ? AND s.language_id = (SELECT id FROM languages WHERE code='hi') ORDER BY st.sort_order""", (slug,))]   # the Hindi seed (Marathi's: 0033)


def answers(conn, step_id):
    return [(r[0], r[1]) for r in conn.execute("SELECT answer_text, is_correct FROM situation_step_answers WHERE step_id=? ORDER BY sort_order", (step_id,))]


def test_parsers_found_the_prototype_content():
    assert len(scenarios()) == 7 and len(REPLY.findall(SCEN)) >= 40
    assert sum(len(p) for p in pack_phrases().values()) == 30


def test_one_situation_per_scenario_with_persona(db_path):
    with connect(db_path) as conn:
        for sc in scenarios():
            row = conn.execute("SELECT title, goal, setting, partner_name, partner_role, cefr_code, status FROM situations WHERE slug=? AND language_id = (SELECT id FROM languages WHERE code='hi')", (sc["category"],)).fetchone()
            assert tuple(row) == (sc["title"], sc["goal"], sc["place"], sc["partner"], sc["role"], "A1", "published")


def test_situation_description_is_the_pack_day_context(db_path):
    sit = dict(re.findall(r'key: "(\w+)".*?\n\s*situation: "([^"]*)"', PACKS))
    with connect(db_path) as conn:
        for key, text in sit.items():
            assert conn.execute("SELECT description FROM situations WHERE slug=? AND language_id = (SELECT id FROM languages WHERE code='hi')", (key,)).fetchone()[0] == text


def test_learn_steps_reference_the_pack_phrases_in_order(db_path):
    with connect(db_path) as conn:
        for key, phrases in pack_phrases().items():
            learn = [s for s in steps(conn, key) if s["kind"] == "learn_phrase"]
            assert [(s["item_text"], s["item_roman"]) for s in learn] == phrases
            # referenced, not copied: each phrase still exists exactly once in the vocabulary
            for hi, _ in phrases:
                assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE text=?", (hi,)).fetchone()[0] == 1


def test_choose_response_uses_scenario_opening_and_first_suggested_reply(db_path):
    with connect(db_path) as conn:
        for sc in scenarios():
            step = next(s for s in steps(conn, sc["category"]) if s["kind"] == "choose_response")
            assert (step["prompt"], step["prompt_meaning"]) == (sc["opening"], sc["opening_en"])
            opts = answers(conn, step["id"])
            assert [t for t, ok in opts if ok] == [quoted(sc["start"])[0]] and len(opts) == 3


def test_conversation_step_is_a_real_scripted_reply_with_its_suggestions(db_path):
    replies = {(t, en): quoted(s) for t, en, s in REPLY.findall(SCEN)}
    with connect(db_path) as conn:
        for sc in scenarios():
            step = next(s for s in steps(conn, sc["category"]) if s["kind"] == "conversation")
            key = (step["prompt"], step["prompt_meaning"])
            if "Connaught Place" in key[0]:  # the {place} template filled with the prototype's default place
                key = tuple(k.replace("Connaught Place", "{place}") for k in key)
            assert key in replies, key
            assert [t for t, ok in answers(conn, step["id"]) if ok] == replies[key]
            assert all(ok for _, ok in answers(conn, step["id"]))


def test_situations_follow_pack_day_order(db_path):
    days = [m.group(2) for m in DAY.finditer(PACKS)]
    with connect(db_path) as conn:
        got = [r[0] for r in conn.execute("SELECT slug FROM situations WHERE language_id = (SELECT id FROM languages WHERE code='hi') ORDER BY sort_order")]
    assert got == days + ["emergency"]


def test_emergency_situation_uses_the_help_me_now_phrases(db_path):
    sos = re.findall(r'\{ hi: "([^"]*)", roman: "([^"]*)", en: "([^"]*)" \}', APP.split("window.SOS_LIST")[1].split("]);")[0])
    assert len(sos) == 5
    with connect(db_path) as conn:
        learn = [s for s in steps(conn, "emergency") if s["kind"] == "learn_phrase"]
        assert [(s["item_text"], s["item_roman"]) for s in learn] == [(hi, roman) for hi, roman, _ in sos]
        for hi, roman, en in sos:
            assert conn.execute("SELECT t.meaning FROM vocabulary_translations t JOIN vocabulary_items v ON v.id=t.item_id JOIN languages l ON l.id=t.language_id WHERE v.text=? AND l.code='en'", (hi,)).fetchone()[0] == en
        assert conn.execute("SELECT t.slug FROM situations s JOIN topics t ON t.id=s.topic_id WHERE s.slug='emergency' AND s.language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == "emergency"


def test_seed_is_internally_consistent(db_path):
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM situations WHERE status='published' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 8
        for sid, slug in conn.execute("SELECT id, slug FROM situations WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchall():
            kinds = [s["kind"] for s in steps(conn, slug)]
            assert kinds[0] == "learn_phrase" and "choose_response" in kinds and len(kinds) >= 6
        for step in [s for slug, in conn.execute("SELECT slug FROM situations WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchall() for s in steps(conn, slug)]:
            ans = answers(conn, step["id"])
            if step["kind"] == "learn_phrase":
                assert ans == []
            elif step["kind"] == "choose_response":
                assert sum(ok for _, ok in ans) == 1 and len(ans) >= 3
            else:
                assert ans and all(ok for _, ok in ans)
        assert conn.execute("SELECT MIN(difficulty), MAX(difficulty) FROM situations WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[:] == (1, 3)
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items v WHERE NOT EXISTS (SELECT 1 FROM vocabulary_translations t WHERE t.item_id=v.id)").fetchone()[0] == 0
