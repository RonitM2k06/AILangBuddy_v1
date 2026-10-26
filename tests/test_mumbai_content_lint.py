"""Editorial lint for Mumbai's Hindi and Marathi content: the deterministic checks of the AI-assisted editorial pass (docs/CONTENT_REVIEW.md).
They catch mechanical problems (a missing script, Hindi inside Marathi, duplicates, two spellings of one word, a gendered phrase without its
feminine form, a fare that disagrees with its source). They are NOT a language review: passing them says nothing about naturalness, which
only a fluent speaker can judge, and the content stays "native review pending" whatever these tests say."""
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

from backend import main
from backend.adaptive import lexicon
from backend.db import connect

ROOT = Path(__file__).resolve().parent.parent
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINDI_ROMAN = re.compile(r"\b(hai|hain|kya|kahan|kidhar|mujhe|chahiye|kitna|kitne|dijiye|bhaiya|achha|accha|shukriya|namaste|yaar|saheb)\b", re.I)
HINDI_DEVA = ("है", "क्या", "कहाँ", "मुझे", "चाहिए", "कितना", "दीजिए", "भैया", "।", "शुक्रिया")
# a learner's phrase whose verb changes with the speaker's gender (Marathi masculine past/habitual forms); each must have a feminine form
MASCULINE_MR = re.compile(r"\b(aalo|gelo|karto|gheto|deto|visarlo|nighto|chuklo|rahto|basto|yeto|jaato)\b")
MASCULINE_HI = re.compile(r"\b(aaya hoon|gaya hoon|naya hoon|karta hoon|leta hoon|deta hoon)\b")


def _client_content():
    expr = ("var G = this; G.window = G; eval($.NSString.stringWithContentsOfFileEncodingError('" + str(ROOT / "frontend/content.js") + "', 4, null).js);"
            " JSON.stringify({hi: PACKS.mumbai, mr: LANGUAGE_PACKS.mumbai.mr, scenes: Object.fromEntries(Object.entries(SCENARIOS).filter(function (e) { return e[0].indexOf('mum_') === 0; })),"
            " local: LOCAL_CONTENT.mumbai, review: CONTENT_REVIEW.mumbai})")
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", expr], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


C = _client_content()


def pack_phrases(lang):
    return [p for d in C[lang] for p in d["phrases"]]


def local_phrases(lang):
    t = C["local"][lang]["tutor"]
    return [p for it in t["intents"] for p in it.get("phrases", [])] + t["generic"]["phrases"] + [l for r in C["local"][lang]["readings"] for l in r["lines"]]


def server_marathi():
    with connect(main.DB_PATH) as conn:
        return [dict(r) for r in conn.execute("""SELECT v.text, v.pronunciation, v.kind, t.meaning FROM vocabulary_items v
            JOIN vocabulary_translations t ON t.item_id = v.id AND t.language_id = (SELECT id FROM languages WHERE code = 'en')
            WHERE v.language_id = (SELECT id FROM languages WHERE code = 'mr')""")]


# ---------- every phrase in both scripts ----------
@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_every_client_phrase_has_devanagari_and_roman(lang):
    for p in pack_phrases(lang) + local_phrases(lang):
        assert DEVANAGARI.search(p["hi"]) and p["roman"] and not DEVANAGARI.search(p["roman"]), p


def test_every_server_marathi_item_has_devanagari_and_roman(client):
    for r in server_marathi():
        assert DEVANAGARI.search(r["text"]) and r["pronunciation"] and not DEVANAGARI.search(r["pronunciation"]) and r["meaning"], r


# ---------- no Hindi inside Marathi ----------
def test_the_marathi_client_content_has_no_hindi():
    phrases = pack_phrases("mr") + local_phrases("mr")
    lines = [s["opening"]["text"] for k, s in C["scenes"].items() if k.startswith("mum_mr_")]
    lines += [x for k, s in C["scenes"].items() if k.startswith("mum_mr_") for r in s["rules"] for x in [r["text"]] + r["s"]]
    assert not [p["hi"] for p in phrases if any(h in p["hi"] for h in HINDI_DEVA)]
    assert not [p["roman"] for p in phrases if HINDI_ROMAN.search(p["roman"])]
    assert not [l for l in lines if HINDI_ROMAN.search(l)]


def test_the_marathi_server_content_has_no_hindi(client):
    rows = server_marathi()
    assert not [r["text"] for r in rows if any(h in r["text"] for h in HINDI_DEVA)]
    assert not [r["pronunciation"] for r in rows if HINDI_ROMAN.search(r["pronunciation"])]


# ---------- duplicates ----------
@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_no_phrase_is_taught_twice_in_a_pack(lang):
    romans = [p["roman"].lower() for p in pack_phrases(lang)]
    assert len(romans) == len(set(romans))


# ---------- one spelling per word ----------
# Words the content deliberately spells two ways, each for a reason a reviewer can check.
ALLOWED_VARIANTS = {
    "vadapav": {"vadapav", "vada"},          # "vadapav" (one word, Marathi pack) and "vada pav" (English name in prices and tips)
}


def _words(texts):
    seen = defaultdict(set)
    canon = lexicon.for_language("mr").canon_roman
    for t in texts:
        for w in re.findall(r"[a-z]+", t.lower()):
            seen[canon(w)].add(w)
    return seen


def test_romanised_marathi_spells_each_word_one_way(client):
    texts = [p["roman"] for p in pack_phrases("mr") + local_phrases("mr")] + [r["pronunciation"] for r in server_marathi()]
    clashes = {k: v for k, v in _words(texts).items() if len(v) > 1 and k not in ALLOWED_VARIANTS}
    assert clashes == {}, clashes


# ---------- gendered phrases ----------
@pytest.mark.parametrize("lang,pattern", [("mr", MASCULINE_MR), ("hi", MASCULINE_HI)])
def test_a_gendered_pack_phrase_shows_its_feminine_form(lang, pattern):
    missing = [p["roman"] for p in pack_phrases(lang) if pattern.search(p["roman"].lower()) and "fem" not in p]
    assert missing == []


def test_a_gendered_server_phrase_has_a_feminine_twin(client):
    rows = server_marathi()
    fem = {r["meaning"] for r in rows if r["meaning"].endswith("(said by a woman)")}
    missing = [r["pronunciation"] for r in rows if r["kind"] == "phrase" and MASCULINE_MR.search(r["pronunciation"].lower()) and not r["meaning"].endswith("(said by a woman)")
               and r["meaning"] + " (said by a woman)" not in fem]
    assert missing == []


# ---------- the review record says the same everywhere ----------
def test_the_review_status_is_the_same_on_client_server_and_docs(client):
    for lang in ("hi", "mr"):
        r = C["review"][lang]
        assert (r["editorial_status"], r["native_review_status"], r["last_editorial_reviewed_at"]) == ("ai_assisted_review", "pending", "2026-10-18")
        assert "not yet checked by a native" in r["note"] and r["known_limitations"]
    with connect(main.DB_PATH) as conn:
        row = conn.execute("SELECT editorial_status, native_review_status, last_editorial_reviewed_at FROM content_reviews "
                           "WHERE language_id = (SELECT id FROM languages WHERE code = 'mr')").fetchone()
    assert tuple(row) == ("ai_assisted_review", "pending", "2026-10-18")
    doc = (ROOT / "docs/CONTENT_REVIEW.md").read_text()
    assert "**Status: AI-assisted editorial review done; native-speaker review pending.**" in doc and "approved" in doc


# ---------- fares agree with their dated source ----------
# Sources (checked 2026-10-18, recorded in docs/CONTENT_REVIEW.md): the revised Mumbai MMRTA tariff as reported by the press in September 2026
# (auto ₹27 for the first 1.5 km then ₹18.22/km; kaali-peeli taxi ₹33 then ₹21.90/km) and Western/Central Railway second-class fares (₹5 for
# the shortest journeys, about ₹15 for longer ones). The ranges in the app must contain these.
AUTO_5KM = 27 + 3.5 * 18.22
TAXI_5KM = 33 + 3.5 * 21.90


def test_the_mumbai_fare_ranges_contain_the_sourced_fares():
    app = (ROOT / "frontend/app.js").read_text()
    start = app.index("const MUMBAI_PRICES = [")
    block = app[start:app.index("];", start)]                                          # Mumbai's list only, not the cities after it
    prices = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in re.finditer(r'id: "(\w+)".*?min: (\d+), max: (\d+)', block)}
    assert prices["auto"][0] <= AUTO_5KM <= prices["auto"][1]
    assert prices["taxi"][0] <= TAXI_5KM <= prices["taxi"][1]
    assert prices["local"][0] <= 5 and 15 <= prices["local"][1]
