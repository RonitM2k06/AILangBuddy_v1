"""Jaipur and Lucknow (Hindi · English): their First Week packs (PACKS.jaipur, PACKS.lucknow), roleplays, local content, prices and review
records; the catalogue, the saved-state checks and the AI prompt. Deterministic checks only: they cannot tell whether a phrase is what a
Jaipur or Lucknow local would say (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
CITIES = {"jaipur": "jpr_", "lucknow": "lko_"}
PACK = {city: C["packs"][city] for city in CITIES}
SCENES = {city: [d["scenario"] for d in PACK[city]] for city in CITIES}
ALL_SCENES = SCENES["jaipur"] + SCENES["lucknow"]
OTHER_CITIES = ("Connaught", "Sarojini", "Rajiv Chowk", "Churchgate", "Bandra", "Marine Drive", "Majestic", "Marina", "White Town")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


# ---------------------------------------------------------------------------------------------------------------------
# the cities
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("city", CITIES)
def test_the_city_is_learnt_in_hindi_and_english(city):
    c = next(c for c in C["cities"] if c["id"] == city)
    assert c["langs"] == ["hi", "en"] and c["ready"] is True and c["tag"] == "Hindi"
    assert city not in C["language_packs"]                                             # its own pack is the Hindi one


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    for city in CITIES:
        assert cities[city]["ready"] is True and cities[city]["languages"] == ["hi", "en"]
    assert cities["delhi"]["languages"] == ["hi", "hinglish", "en"] and cities["mumbai"]["languages"] == ["hi", "mr", "en"]   # unchanged
    assert [s for s, c in cities.items() if not c["ready"]] == []


@pytest.mark.parametrize("city,alt,state", [("jaipur", "The Pink City", "Rajasthan"), ("lucknow", "The City of Nawabs", "Uttar Pradesh")])
def test_the_destination_card(city, alt, state):
    d = next(x for x in D if x["id"] == city)
    assert d["status"] == "available" and d["city"] == city and d["alt"] == alt and d["serves"] == [{"name": state, "type": "state"}]
    assert "Hindi" in d["intro"] and len(d["preview"]) == 7


# ---------------------------------------------------------------------------------------------------------------------
# the packs
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("city", CITIES)
def test_the_pack_is_hindi_in_devanagari(city):
    phrases = [p for d in PACK[city] for p in d["phrases"]]
    assert len(phrases) == 35
    for p in phrases:
        assert DEVANAGARI.search(p["hi"]) and not TAMIL.search(p["hi"]) and not KANNADA.search(p["hi"]) and p["roman"], p
    text = json.dumps([PACK[city], LOCAL[city]["hi"], [C["scenarios"][s] for s in SCENES[city]]], ensure_ascii=False)
    assert not TAMIL.search(text) and not KANNADA.search(text)


@pytest.mark.parametrize("city,own,local_words", [
    ("jaipur", ("Hawa Mahal", "Amer", "Johari Bazaar", "Bapu Bazaar", "Nahargarh", "Malviya Nagar"), ("khamma ghani", "padharo", "mojdi")),
    ("lucknow", ("Hazratganj", "Aminabad", "Chowk", "Charbagh", "Rumi Darwaza", "Gomti"), ("aadaab", "shukriya", "pehle aap", "tehzeeb")),
])
def test_the_pack_is_the_citys_own(city, own, local_words):
    text = json.dumps([PACK[city], [C["scenarios"][s] for s in SCENES[city]]], ensure_ascii=False)
    for place in own:
        assert place in text, place
    for other in OTHER_CITIES:
        assert other not in text, other
    lower = text.lower()
    for w in local_words:                                                              # the city's own flavour of Hindi
        assert w in lower, w
    assert all(s.startswith(CITIES[city]) for s in SCENES[city])


def test_the_two_packs_are_not_one_pack_twice():
    jaipur = {p["roman"] for d in PACK["jaipur"] for p in d["phrases"]}
    lucknow = {p["roman"] for d in PACK["lucknow"] for p in d["phrases"]}
    assert len(jaipur & lucknow) <= 2                                                 # only "Mera naam Alex hai." is shared
    delhi = {p["roman"] for d in C["packs"]["delhi"] for p in d["phrases"]}
    assert len(jaipur & delhi) <= 5 and len(lucknow & delhi) <= 5


@pytest.mark.parametrize("city,fem", [("jaipur", ["Main yahan nayi hoon."]), ("lucknow", ["Main Lucknow mein nayi hoon.", "Theek hai, le leti hoon."])])
def test_a_gendered_phrase_shows_the_feminine_form(city, fem):
    got = [p for d in PACK[city] for p in d["phrases"] if "fem" in p]
    assert [p["fem"]["roman"] for p in got] == fem
    assert all(DEVANAGARI.search(p["fem"]["hi"]) and p["fem"]["hi"] != p["hi"] for p in got)


# ---------------------------------------------------------------------------------------------------------------------
# the roleplays
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sid", ALL_SCENES)
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


@pytest.mark.parametrize("sid", ALL_SCENES)
def test_the_characters_do_not_assume_the_learner_is_male(sid):
    sc = C["scenarios"][sid]
    said_to = " " + " ".join(lines(sc)).lower() + " "
    for masc in (" saheb", "arre bhai", "naye aaye", "rahe ho", "aap naye", "tum naye", "ban jayega", "nahi bhaiya", "aaye ho"):
        assert masc not in said_to, (sid, masc)
    said_by = words(suggestions(sc))
    for masc in (" naya hoon", " aaya hoon", " doonga", " loonga", " de raha", " samajh gaya ", " le leta", " bhool gaya"):
        assert masc not in said_by, (sid, masc)


@pytest.mark.parametrize("sid,text,expected", [
    ("jpr_auto", "Hawa Mahal chaloge?", "{place}? Haan, chalo."), ("jpr_auto", "Kitne paise lagenge?", "Hawa Mahal? Dedh sau"),
    ("jpr_auto", "Sau rupaye mein chalo.", "Theek hai, sau mein"), ("jpr_auto", "Bahut zyaada hai, bhaiya.", "Achha, ek sau bees"),
    ("jpr_food", "Ek pyaaz kachori dena.", "Garam-garam pyaaz kachori"), ("jpr_shopping", "Ye mojdi kitne ki hai?", "Ye mojdi? Nau sau"),
    ("lko_auto", "Hazratganj chalenge?", "{place}? Ji, baithiye."), ("lko_auto", "Sharing waala auto kahan milega?", "Sharing auto bahar stand"),
    ("lko_food", "Main shaakaahaari hoon, veg kya hai?", "Veg mein dum aloo"), ("lko_shopping", "Ye haath ki kadhaai hai?", "Ji, poora haath ka kaam"),
    ("lko_smalltalk", "Yahan ke log bahut tehzeeb waale hain.", "Haha, “pehle aap”"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


# ---------------------------------------------------------------------------------------------------------------------
# local content, prices, review
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("city,greet", [("jaipur", "Khamma ghani"), ("lucknow", "Aadaab")])
def test_the_local_content_is_the_citys(city, greet):
    entry = LOCAL[city]["hi"]
    assert entry["tutor"]["greet"] == greet and "glossaryOnly" not in entry["tutor"]       # Hindi: the shared Hindi glossary still applies
    assert len(entry["rightNow"]) == 5 and all(slot[5] in SCENES[city] for slot in entry["rightNow"])
    hours = [(slot[0], slot[1]) for slot in entry["rightNow"]]
    assert hours == [(5, 11), (11, 15), (15, 18), (18, 22), (22, 29)]                     # every hour of the day is covered, once


APP = (ROOT / "frontend" / "app.js").read_text()


def prices(name):
    return {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split(f"const {name}")[1].split("];")[0])}


def test_the_fare_ranges():
    """Jaipur Metro ₹10–30, Lucknow Metro ₹10–60 (fixed fares); autos in both cities rarely use the meter, so the auto item is an agreed fare."""
    jaipur, lucknow = prices("JAIPUR_PRICES"), prices("LUCKNOW_PRICES")
    assert jaipur["metro"] == (10, 30) and lucknow["metro"] == (10, 60)
    assert set(jaipur) == {"auto", "metro", "mojdi", "kurta", "kachori", "lassi"} and set(lucknow) == {"auto", "shared", "metro", "chikan", "kebab", "chai"}
    for name in ("JAIPUR_PRICES", "LUCKNOW_PRICES"):
        auto = APP.split(f"const {name}")[1].split("\n")[1]
        assert "agreed fare" in auto and "meter: true" not in auto
    assert "jaipur: JAIPUR_PRICES, lucknow: LUCKNOW_PRICES" in APP


@pytest.mark.parametrize("city,who", [("jaipur", "Jaipur"), ("lucknow", "Lucknow")])
def test_the_content_is_marked_as_awaiting_native_review(city, who):
    r = C["review"][city]["hi"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and f"native speaker from {who}" in r["note"]


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Jaipur and Lucknow (Hindi)")[1].split("\n## ")[0]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-19): Available" in section


# ---------------------------------------------------------------------------------------------------------------------
# the server
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("city,scenario,partner", [("Jaipur", "jpr_auto", "Ramesh"), ("Lucknow", "lko_food", "Haji sahab")])
def test_the_roleplay_prompt_names_the_city(client, monkeypatch, city, scenario, partner):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "Hindi", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "Namaste"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert f"a real {city} " in system and partner in system and "Delhi" not in system


@pytest.mark.parametrize("language", ["Marathi", "Tamil", "French", "Kannada"])
def test_the_cities_are_not_asked_for_in_another_language(client, monkeypatch, language):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Jaipur", "language": language, "level": "A1", "scenario": "jpr_auto", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


@pytest.mark.parametrize("city", CITIES)
@pytest.mark.parametrize("lang,accepted", [("hi", True), ("en", True), ("hinglish", False), ("mr", False), ("ta", False)])
def test_a_saved_state_keeps_the_city_only_in_a_language_it_offers(client, city, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'{city}-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": city, "language": lang}).status_code == 200) is accepted
