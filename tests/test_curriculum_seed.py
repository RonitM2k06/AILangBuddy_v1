"""The seeded curriculum must match the prototype content it was migrated from."""
import re
from pathlib import Path

from backend.db import connect

JS = (Path(__file__).parent.parent / "frontend" / "content.js").read_text(encoding="utf-8")
PACKS = JS.split("window.PACKS")[1].split("window.SCENARIOS")[0]
GLOSSARY = JS.split("window.GLOSSARY")[1].split("window.READINGS")[0]
PLACEMENT = JS.split("window.PLACEMENT")[1]

DAY = re.compile(r'\{ day: (\d+), key: "(\w+)", icon: "[^"]*", title: "([^"]*)", desc: "([^"]*)",\s*situation: "([^"]*)", scenario: "\w+",\s*tip: "([^"]*)"')
PHRASE = re.compile(r'\{ hi: "([^"]*)", roman: "([^"]*)", en: "([^"]*)", natural: "([^"]*)" \}')


def js_days():
    """[(day fields, [phrases])] parsed straight from content.js."""
    starts = list(DAY.finditer(PACKS))
    out = []
    for i, m in enumerate(starts):
        body = PACKS[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(PACKS)]
        out.append((m.groups(), PHRASE.findall(body)))
    return out


def test_parser_found_the_prototype_content():
    days = js_days()
    assert len(days) == 7 and sum(len(p) for _, p in days) == 30


def test_lessons_match_pack_days(db_path):
    with connect(db_path) as conn:
        for (day, key, title, desc, situation, tip), _ in js_days():
            row = conn.execute(
                """SELECT l.title, l.description, l.situation, l.tip, l.sort_order, l.status, l.cefr_code, lang.code AS lang
                   FROM lessons l JOIN languages lang ON lang.id = l.language_id WHERE l.slug = ?""", (key,)).fetchone()
            assert tuple(row) == (title, desc, situation, tip, int(day), "published", "A1", "hi")


def test_phrases_match_pack_phrases_in_order(db_path):
    with connect(db_path) as conn:
        for (_, key, *_), phrases in js_days():
            rows = conn.execute(
                """SELECT v.text, v.pronunciation, t.meaning, t.natural FROM lesson_vocabulary lv
                   JOIN lessons l ON l.id = lv.lesson_id JOIN vocabulary_items v ON v.id = lv.item_id
                   JOIN vocabulary_translations t ON t.item_id = v.id JOIN languages tl ON tl.id = t.language_id AND tl.code = 'en'
                   WHERE l.slug = ? AND l.language_id = (SELECT id FROM languages WHERE code='hi') AND v.kind = 'phrase' ORDER BY lv.sort_order""", (key,)).fetchall()   # the Hindi seed (Marathi: 0031)
            assert [tuple(r) for r in rows] == [(hi, roman, en, natural) for hi, roman, en, natural in phrases]


def test_topics_match_categories(db_path):
    cats = re.findall(r'\{ key: "(\w+)", label: "([^"]*)", icon: "([^"]*)"', JS.split("window.CATEGORIES")[1].split("];")[0])
    with connect(db_path) as conn:
        # the category topics come from content.js; later phases add more (e.g. Emergency) after them
        assert [tuple(r) for r in conn.execute("SELECT slug, name, icon FROM topics ORDER BY id LIMIT ?", (len(cats),))] == cats
        for (_, key, *_), _p in js_days():  # each lesson carries the topic of its day
            assert conn.execute("SELECT t.slug FROM lesson_topics lt JOIN topics t ON t.id=lt.topic_id JOIN lessons l ON l.id=lt.lesson_id WHERE l.slug=? AND l.language_id = (SELECT id FROM languages WHERE code='hi')", (key,)).fetchone()[0] == key


def test_words_match_glossary(db_path):
    glossary = dict(re.findall(r'(?:^|,)\s*"?([a-z]+(?: [a-z]+)?)"?: "([^"]*)"', GLOSSARY, re.M))
    glossary.pop("achha")  # duplicate spelling of "accha"
    with connect(db_path) as conn:
        rows = conn.execute("SELECT v.pronunciation, t.meaning FROM vocabulary_items v JOIN vocabulary_translations t ON t.item_id=v.id WHERE v.kind='word' AND v.language_id = (SELECT id FROM languages WHERE code='hi')").fetchall()
    assert {r[0]: r[1] for r in rows} == glossary and len(glossary) == 18


def test_multiple_choice_exercises_reuse_placement_questions(db_path):
    qs = re.findall(r'\{ q: "([^"]*)", options: \[([^\]]*)\], a: (\d) \}', PLACEMENT)
    assert len(qs) == 5
    with connect(db_path) as conn:
        for q, options, a in qs:
            opts = re.findall(r'"([^"]*)"', options)
            ex = conn.execute("SELECT id FROM exercises WHERE kind='multiple_choice' AND prompt=?", (q,)).fetchone()
            assert ex, q
            rows = conn.execute("SELECT answer_text, is_correct FROM exercise_answers WHERE exercise_id=? ORDER BY sort_order", (ex[0],)).fetchall()
            assert [r[0] for r in rows] == opts
            assert [r[0] for r in rows if r[1]] == [opts[int(a)]]


def test_seed_is_internally_consistent(db_path):
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lessons WHERE status='published' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 7
        for lesson, n in conn.execute("SELECT lesson_id, COUNT(*) FROM exercises GROUP BY lesson_id"):
            assert n >= 2
        assert conn.execute("SELECT COUNT(DISTINCT lesson_id) FROM exercises WHERE language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 7
        for ex, kind in conn.execute("SELECT id, kind FROM exercises").fetchall():
            correct = conn.execute("SELECT COUNT(*) FROM exercise_answers WHERE exercise_id=? AND is_correct=1", (ex,)).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM exercise_answers WHERE exercise_id=?", (ex,)).fetchone()[0]
            if kind == "multiple_choice":
                assert correct == 1 and total >= 3
            else:
                assert correct >= 1 and correct == total
        # every item has an English meaning, every grammar topic an English text
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items v WHERE NOT EXISTS (SELECT 1 FROM vocabulary_translations t JOIN languages l ON l.id=t.language_id WHERE t.item_id=v.id AND l.code='en')").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM grammar_topics g WHERE NOT EXISTS (SELECT 1 FROM grammar_topic_texts t WHERE t.grammar_topic_id=g.id)").fetchone()[0] == 0
        # the curriculum is Hindi (this seed), Marathi (0031, tests/test_marathi_lessons.py) Kannada (0037, 0038) Tamil (0040-0045) and French (0044), nothing else
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE language_id NOT IN (SELECT id FROM languages WHERE code IN ('hi', 'mr', 'kn', 'ta', 'fr', 'bn', 'te', 'ur', 'ks', 'doi'))").fetchone()[0] == 0


def test_fill_blank_answers_complete_the_real_phrase(db_path):
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT e.prompt, a.answer_text, v.pronunciation FROM exercises e JOIN exercise_answers a ON a.exercise_id=e.id
               JOIN vocabulary_items v ON v.id=e.item_id WHERE e.kind='fill_blank'""").fetchall()
        assert conn.execute("SELECT COUNT(*) FROM exercises WHERE kind='fill_blank' AND language_id = (SELECT id FROM languages WHERE code='hi')").fetchone()[0] == 7
        assert len(rows) == 7 + 27 + 25 + 28 + 9 + 25 + 9 + 9 + 9 + 9           # Hindi's 7, Marathi's 27, Kannada's 25, Tamil's 28, French's 9, Bengali's 25, Telugu's 9, Urdu's 9, Kashmiri's 9, Dogri's 9: every one is checked below
        for prompt, answer, roman in rows:
            masked = re.search(r"“([^”]*____[^”]*)”", prompt).group(1)
            assert masked.replace("____", answer) == roman
