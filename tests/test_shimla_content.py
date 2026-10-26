"""Shimla (Hindi · English): its First Week pack (PACKS.shimla), roleplays, local content, prices and review record; the catalogue, the
saved-state checks and the AI prompt. Deterministic checks only: they cannot tell whether a phrase is what someone from Shimla would say
(docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACK = C["packs"]["shimla"]
SCENES = [d["scenario"] for d in PACK]
OTHER_CITIES = ("Connaught", "Sarojini", "Churchgate", "Majestic", "Marina", "White Town", "Hawa Mahal", "Hazratganj", "Park Street", "Charminar", "Bada Talab", "Chowk Bazaar")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


def test_shimla_is_learnt_in_hindi_and_english():
    c = next(c for c in C["cities"] if c["id"] == "shimla")
    assert c["langs"] == ["hi", "en"] and c["ready"] is True and c["tag"] == "Hindi"
    assert "shimla" not in C["language_packs"]


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["shimla"]["ready"] is True and cities["shimla"]["languages"] == ["hi", "en"]


def test_the_destination_card():
    d = next(x for x in D if x["id"] == "shimla")
    assert d["status"] == "in_development" and d["city"] == "shimla" and d["alt"] == "The Queen of the Hills" and d["serves"] == [{"name": "Himachal Pradesh", "type": "state"}]
    assert "Hindi" in d["intro"] and len(d["preview"]) == 7


def test_the_pack_is_hindi_in_devanagari():
    phrases = [p for d in PACK for p in d["phrases"]]
    assert len(phrases) == 35
    for p in phrases:
        assert DEVANAGARI.search(p["hi"]) and not TAMIL.search(p["hi"]) and not KANNADA.search(p["hi"]) and p["roman"], p


def test_the_pack_is_shimlas_own():
    text = json.dumps([PACK, [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    for place in ("Sanjauli", "Lift", "Lower Bazaar", "Lakkar Bazaar", "Scandal Point", "Jakhu", "Christ Church", "Ridge", "Summer Hill", "Kufri"):
        assert place in text, place
    for other in OTHER_CITIES:
        assert other not in text, other
    lower = text.lower()
    for w in ("ram ram", "bhaiji", "siddu", "dham", "topi", "madra"):                       # Shimla's own words
        assert w in lower, w
    assert all(s.startswith("shm_") for s in SCENES)


def test_the_gendered_phrase_shows_the_feminine_form():
    fem = [p for d in PACK for p in d["phrases"] if "fem" in p]
    assert [p["fem"]["roman"] for p in fem] == ["Main Shimla mein nayi hoon."] and all(DEVANAGARI.search(p["fem"]["hi"]) for p in fem)


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
    ("shm_taxi", "Lift tak chaloge?", "{place}? Haan, baitho."), ("shm_taxi", "Bus kahan se milegi?", "Local bus bahar stand"),
    ("shm_taxi", "Mall Road tak chaloge?", "Mall Road pe gaadi nahi"), ("shm_taxi", "Kitna loge?", "Lift tak? Chaar sau"),
    ("shm_food", "Siddu ke saath ghee dena.", "Haan ji! Siddu toh ghee"), ("shm_food", "Dham milega?", "Dham toh shaadi"),
    ("shm_shopping", "Ye haath ka kaam hai?", "Bilkul, Kullu ki oon"), ("shm_smalltalk", "Tum yahin ke ho?", "Haan, Chhota Shimla mein"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


def test_the_local_content_is_shimlas():
    entry = LOCAL["shimla"]["hi"]
    assert entry["tutor"]["greet"] == "Ram Ram" and "glossaryOnly" not in entry["tutor"] and "siddu" in entry["tutor"]["glossary"]
    assert len(entry["rightNow"]) == 5 and all(slot[5] in SCENES for slot in entry["rightNow"])


APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const SHIMLA_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """No autos in Shimla: a taxi at an agreed fare, the town bus and the Lift up to the Mall."""
    assert set(PRICES) == {"taxi", "bus", "lift", "topi", "siddu", "chai"} and "auto" not in PRICES
    assert "agreed fare" in APP.split("const SHIMLA_PRICES")[1].split("
")[1] and "shimla: SHIMLA_PRICES" in APP


def test_the_content_is_marked_as_awaiting_native_review():
    r = C["review"]["shimla"]["hi"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and "native speaker from Shimla" in r["note"]


def test_the_roleplay_prompt_names_the_city(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Shimla", "language": "Hindi", "level": "A1", "scenario": "shm_taxi", "history": [{"role": "me", "text": "Namaste"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert "a real Shimla " in system and "Pawan bhai" in system and "Delhi" not in system


@pytest.mark.parametrize("language", ["Urdu", "Telugu", "Bengali", "Marathi"])
def test_shimla_is_not_asked_for_in_another_language(client, monkeypatch, language):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Shimla", "language": language, "level": "A1", "scenario": "shm_taxi", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


@pytest.mark.parametrize("lang,accepted", [("hi", True), ("en", True), ("hinglish", False), ("ur", False)])
def test_a_saved_state_keeps_shimla_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'shm-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "shimla", "language": lang}).status_code == 200) is accepted
