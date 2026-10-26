"""Bhopal (Hindi · English): its First Week pack (PACKS.bhopal), roleplays, local content, prices and review record; the catalogue, the
saved-state checks and the AI prompt. Deterministic checks only: they cannot tell whether a phrase is what a Bhopali would say
(docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACK = C["packs"]["bhopal"]
SCENES = [d["scenario"] for d in PACK]
OTHER_CITIES = ("Connaught", "Sarojini", "Churchgate", "Majestic", "Marina", "White Town", "Hawa Mahal", "Hazratganj", "Park Street", "Charminar")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


def test_bhopal_is_learnt_in_hindi_and_english():
    c = next(c for c in C["cities"] if c["id"] == "bhopal")
    assert c["langs"] == ["hi", "en"] and c["ready"] is True and c["tag"] == "Hindi"
    assert "bhopal" not in C["language_packs"]


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["bhopal"]["ready"] is True and cities["bhopal"]["languages"] == ["hi", "en"]
    assert [s for s, c in cities.items() if not c["ready"]] == []


def test_the_destination_card():
    d = next(x for x in D if x["id"] == "bhopal")
    assert d["status"] == "available" and d["city"] == "bhopal" and d["alt"] == "The City of Lakes" and d["serves"] == [{"name": "Madhya Pradesh", "type": "state"}]
    assert "Hindi" in d["intro"] and len(d["preview"]) == 7


def test_the_pack_is_hindi_in_devanagari():
    phrases = [p for d in PACK for p in d["phrases"]]
    assert len(phrases) == 35
    for p in phrases:
        assert DEVANAGARI.search(p["hi"]) and not TAMIL.search(p["hi"]) and not KANNADA.search(p["hi"]) and p["roman"], p


def test_the_pack_is_bhopals_own():
    text = json.dumps([PACK, [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    for place in ("Rani Kamlapati", "New Market", "MP Nagar", "Chowk Bazaar", "Taj-ul-Masajid", "Peer Gate", "Boat Club", "Bada Talab", "Saanchi", "Arera Colony"):
        assert place in text, place
    for other in OTHER_CITIES:
        assert other not in text, other
    lower = text.lower()
    for w in ("khan", "miyan", "patiya", "poha", "batua", "magic"):                       # Bhopal's own words
        assert w in lower, w
    assert all(s.startswith("bpl_") for s in SCENES)


def test_the_gendered_phrase_shows_the_feminine_form():
    fem = [p for d in PACK for p in d["phrases"] if "fem" in p]
    assert [p["fem"]["roman"] for p in fem] == ["Main Bhopal mein nayi hoon."] and all(DEVANAGARI.search(p["fem"]["hi"]) for p in fem)


@pytest.mark.parametrize("sid", SCENES)
def test_every_roleplay_is_complete_and_answers_every_suggestion(sid):
    sc = C["scenarios"][sid]
    for field in ("icon", "title", "partner", "role", "place", "goal"):
        assert sc[field], field
    assert sc["opening"]["text"] and sc["opening"]["en"] and len(sc["start"]) >= 2 and len(sc["rules"]) >= 5
    assert sc["fallback"]["text"] and sc["fallback"]["en"] and sc["fallback"]["s"]
    for rule in sc["rules"]:
        assert rule["m"] and all(k == k.lower() and k.strip() for k in rule["m"]), rule["m"]
        assert rule["text"] and rule["en"] and rule["s"]
        assert ("{place}" in rule["text"]) <= ("places" in sc)
    assert sum(1 for rule in sc["rules"] if rule.get("end")) >= 1
    assert [s for s in set(suggestions(sc)) if first_match(sc, s) is None] == []
    for i, rule in enumerate(sc["rules"]):
        if rule.get("hint"):
            assert first_match(sc, rule["hint"]) == i, (rule["hint"], first_match(sc, rule["hint"]))


@pytest.mark.parametrize("sid", SCENES)
def test_the_characters_do_not_assume_the_learner_is_male(sid):
    sc = C["scenarios"][sid]
    said_to = " " + " ".join(lines(sc)).lower() + " "
    for masc in (" saheb", "arre bhai", "naye aaye", "rahe ho", "aap naye", "tum naye", "naye ho", "aaye ho", "naye padosi"):
        assert masc not in said_to, (sid, masc)
    said_by = words(suggestions(sc) + [r["hint"] for r in sc["rules"] if r.get("hint")])
    for masc in (" naya hoon", " aaya hoon", " doonga", " loonga", " de raha", " samajh gaya ", " bhool gaya"):
        assert masc not in said_by, (sid, masc)


@pytest.mark.parametrize("sid,text,expected", [
    ("bpl_auto", "New Market chaloge?", "{place}? Haan, baitho."), ("bpl_auto", "Magic kahan se milegi?", "Magic bahar stand se"),
    ("bpl_auto", "Kitni der lagegi?", "Pandrah minute"), ("bpl_auto", "Kitna kiraaya loge?", "New Market? Ek sau bees"),
    ("bpl_food", "Pohe mein sev zyaada daalna.", "Sev bhi, nimbu bhi!"), ("bpl_food", "Ek sulemani chai bhi.", "Sulemani chai toh raat ko"),
    ("bpl_shopping", "Ye haath ka kaam hai?", "Bilkul, ghar ki auraton"), ("bpl_smalltalk", "Tum puraane Bhopal ke ho?", "Haan, Peer Gate ke paas"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


def test_the_local_content_is_bhopals():
    entry = LOCAL["bhopal"]["hi"]
    assert entry["tutor"]["greet"] == "Namaste" and "glossaryOnly" not in entry["tutor"] and "khan" in entry["tutor"]["glossary"]
    assert len(entry["rightNow"]) == 5 and all(slot[5] in SCENES for slot in entry["rightNow"])


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const BHOPAL_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """Bhopal Metro (Orange Line) ₹20–40, fixed; autos an agreed fare; shared 'magic' vans per seat."""
    assert PRICES["metro"] == (20, 40) and set(PRICES) == {"auto", "magic", "metro", "batua", "poha", "chai"}
    auto = APP.split("const BHOPAL_PRICES")[1].split("\n")[1]
    assert "agreed fare" in auto and "meter: true" not in auto and "bhopal: BHOPAL_PRICES" in APP


def test_the_content_is_marked_as_awaiting_native_review():
    r = C["review"]["bhopal"]["hi"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and "native speaker from Bhopal" in r["note"]


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Bhopal (Hindi)")[1].split("\n## ")[0]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-19): Available" in section


def test_the_roleplay_prompt_names_the_city(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Bhopal", "language": "Hindi", "level": "A1", "scenario": "bpl_auto", "history": [{"role": "me", "text": "Namaste"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert "a real Bhopal " in system and "Rafiq bhai" in system and "Delhi" not in system


@pytest.mark.parametrize("language", ["Urdu", "Telugu", "Bengali", "Marathi"])
def test_bhopal_is_not_asked_for_in_another_language(client, monkeypatch, language):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Bhopal", "language": language, "level": "A1", "scenario": "bpl_auto", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


@pytest.mark.parametrize("lang,accepted", [("hi", True), ("en", True), ("hinglish", False), ("ur", False)])
def test_a_saved_state_keeps_bhopal_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'bpl-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "bhopal", "language": lang}).status_code == 200) is accepted
