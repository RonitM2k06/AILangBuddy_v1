"""Kolkata (Bengali · English): the Bengali First Week pack (PACKS.kolkata), its roleplays, local content, prices and review record; the
catalogue, the server's language checks and the AI prompt. Deterministic checks only: they cannot tell whether a phrase is what a Kolkata
local would say (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import BENGALI, C, DEVANAGARI, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACK = C["packs"]["kolkata"]
SCENES = [d["scenario"] for d in PACK]
HINDI_MARKERS = (" hai ", " hain ", " kya ", " kahan ", " mujhe ", " chahiye ", " kitna ", " mein ", " dijiye ", " bhaiya ", " theek ", " aap ", " nahi ")
OTHER_CITIES = ("Connaught", "Churchgate", "Majestic", "Marina", "White Town", "Hawa Mahal", "Hazratganj")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


# ---------------------------------------------------------------------------------------------------------------------
# the city
# ---------------------------------------------------------------------------------------------------------------------
def test_kolkata_is_learnt_in_bengali_and_english():
    city = next(c for c in C["cities"] if c["id"] == "kolkata")
    assert city["langs"] == ["bn", "en"] and city["ready"] is True and city["tag"] == "Bengali"
    assert {"code": "bn", "name": "Bengali", "native": "বাংলা", "tts": "bn-IN"} in C["languages"]
    assert "kolkata" not in C["language_packs"]                                         # its own pack is the Bengali one


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["kolkata"]["ready"] is True and cities["kolkata"]["languages"] == ["bn", "en"]
    assert [s for s, c in cities.items() if not c["ready"]] == []
    assert {"code": "bn", "name": "Bengali", "native_name": "বাংলা", "tts_locale": "bn-IN"} in client.get("/api/languages").json()["languages"]


def test_the_destination_card():
    d = next(x for x in D if x["id"] == "kolkata")
    assert d["status"] == "available" and d["city"] == "kolkata" and d["alt"] == "Calcutta" and d["serves"] == [{"name": "West Bengal", "type": "state"}]
    assert "Bengali" in d["intro"] and len(d["preview"]) == 7


# ---------------------------------------------------------------------------------------------------------------------
# the pack
# ---------------------------------------------------------------------------------------------------------------------
def test_the_pack_is_bengali():
    phrases = [p for d in PACK for p in d["phrases"]]
    assert len(phrases) == 35
    for p in phrases:
        assert BENGALI.search(p["hi"]) and not DEVANAGARI.search(p["hi"].replace("।", "")) and not TAMIL.search(p["hi"]) and not KANNADA.search(p["hi"]) and p["roman"], p
    text = json.dumps([PACK, LOCAL["kolkata"]["bn"], [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    assert not DEVANAGARI.search(text.replace("।", ""))                                 # the danda is shared by Bengali; no Devanagari letter
    everything = words([p["roman"] for p in phrases] + [x for s in SCENES for x in lines(C["scenarios"][s]) + suggestions(C["scenarios"][s])])
    assert [m for m in HINDI_MARKERS if m in everything] == []
    for marker in (" koto ", " kothay ", " din ", " nomoshkar ", " achhe ", " korun "):          # everyday Bengali, all through the pack
        assert marker in words([p["roman"] for p in phrases]), marker


def test_bengali_has_no_feminine_forms_because_its_verbs_do_not_change():
    assert [p for d in PACK for p in d["phrases"] if "fem" in p] == []


def test_the_pack_is_kolkatas_own():
    text = json.dumps([PACK, [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    for place in ("Howrah", "Park Street", "Gariahat", "Esplanade", "Victoria Memorial", "Jadavpur", "Prinsep Ghat", "College Street", "Salt Lake"):
        assert place in text, place
    for other in OTHER_CITIES:
        assert other not in text, other
    assert all(s.startswith("kol_") for s in SCENES)
    for word in ("adda", "bhaar", "taant", "phuchka", "roshogolla"):
        assert word in text.lower(), word


# ---------------------------------------------------------------------------------------------------------------------
# the roleplays
# ---------------------------------------------------------------------------------------------------------------------
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


@pytest.mark.parametrize("sid,text,expected", [
    ("kol_taxi", "Park Street jaben?", "{place}? Hyan, cholun."), ("kol_taxi", "Meter-e jaben to?", "Meter-e jabo, kintu"),
    ("kol_taxi", "Na, meter-er beshi debo na.", "Thik achhe, meter-ei jabo."), ("kol_taxi", "Kotokkhon lagbe?", "Jaam thakle"),
    ("kol_taxi", "Koto lagbe?", "Meter-e jabo, eksho-r moto"), ("kol_food", "Ekta egg roll din.", "Garam garam egg roll"),
    ("kol_food", "Jhal kom deben.", "Thik achhe, jhal kom."), ("kol_shopping", "Panch sho hobe?", "Accha, apnar jonno chhoy sho"),
    ("kol_directions", "Metro-te jawa jay?", "Metro-te Maidan station"), ("kol_smalltalk", "Tumi ki Kolkatar-i?", "Hyan, ami Uttar Kolkatay"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


# ---------------------------------------------------------------------------------------------------------------------
# local content, prices, review
# ---------------------------------------------------------------------------------------------------------------------
def test_the_local_content_is_bengali():
    entry = LOCAL["kolkata"]["bn"]
    tutor = entry["tutor"]
    assert tutor["language"] == "Bengali" and tutor["greet"] == "Nomoshkar" and tutor["glossaryOnly"] is True and "jugaad" not in tutor["glossary"]
    assert tutor["polite"]["rules"] and entry["achievements"]["first-words"][2] == "Said your first Bengali phrase"
    phrases = [p for it in tutor["intents"] for p in it.get("phrases", [])] + tutor["generic"]["phrases"] + [l for r in entry["readings"] for l in r["lines"]]
    assert phrases and all(BENGALI.search(p["hi"]) for p in phrases)
    assert [m for m in HINDI_MARKERS if m in words([p["roman"] for p in phrases])] == []
    assert len(entry["rightNow"]) == 5 and all(slot[5] in SCENES for slot in entry["rightNow"])


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const KOLKATA_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """Kolkata Metro Blue Line ₹5–25 (fixed fares); yellow taxis go by the meter (the range is an estimate)."""
    assert PRICES["metro"] == (5, 25) and set(PRICES) == {"taxi", "metro", "saree", "kurta", "roll", "cha"}
    taxi = APP.split("const KOLKATA_PRICES")[1].split("\n")[1]
    assert "by meter" in taxi and "meter: true" in taxi
    assert "kolkata: KOLKATA_PRICES" in APP


def test_the_content_is_marked_as_awaiting_native_review():
    r = C["review"]["kolkata"]["bn"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and "native Bengali speaker" in r["note"]


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Kolkata (Bengali)")[1].split("\n## ")[0]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-19): Available" in section


# ---------------------------------------------------------------------------------------------------------------------
# the server: who may be asked for Bengali, and how
# ---------------------------------------------------------------------------------------------------------------------
def test_the_ai_is_asked_for_bengali_for_kolkata(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    rp = {"mode": "roleplay", "city": "Kolkata", "language": "Bengali", "level": "A1", "scenario": "kol_taxi", "history": [{"role": "me", "text": "Nomoshkar"}]}
    tutor = {"mode": "tutor", "city": "Kolkata", "language": "Bengali", "level": "A1", "history": [{"role": "me", "text": "How do I order a roll?"}]}
    assert client.post("/api/ai", json=rp).status_code == 200 and client.post("/api/ai", json=tutor).status_code == 200
    roleplay, tutor_prompt = model.calls
    assert "learn Bengali " in roleplay and "romanised Bengali" in roleplay and "Bapi da" in roleplay and "a real Kolkata " in roleplay
    assert "Hinglish" not in roleplay + tutor_prompt and "Bengali script" in tutor_prompt and "Devanagari" not in tutor_prompt


@pytest.mark.parametrize("city,scenario", [("Delhi", "auto"), ("Chennai", "chn_auto"), ("Jaipur", "jpr_auto")])
def test_only_kolkata_is_asked_for_in_bengali(client, monkeypatch, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "Bengali", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == "This city is not offered in Bengali"


@pytest.mark.parametrize("lang,accepted", [("bn", True), ("en", True), ("hi", False), ("ta", False), ("hinglish", False)])
def test_a_saved_state_keeps_kolkata_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'kol-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "kolkata", "language": lang}).status_code == 200) is accepted


def test_the_bengali_font_is_loaded_with_the_others():
    html = (ROOT / "frontend" / "index.html").read_text()
    css = (ROOT / "frontend" / "styles.css").read_text()
    assert "family=Noto+Sans+Bengali:" in html and '"Noto Sans Bengali"' in css.split("--deva:")[1].split(";")[0]
