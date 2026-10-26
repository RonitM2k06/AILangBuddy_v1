"""Chennai's First Week in Tamil (frontend/content.js PACKS.chennai, SCENARIOS.chn_*, LOCAL_CONTENT.chennai.ta): written in Tamil script, not
Devanagari, with no Hindi in it; every roleplay complete and answering what the learner says; the catalogue, the server's checks and the AI
prompt agreeing; the fair-price ranges containing the sourced fares; and the content honestly marked as awaiting native review.
Deterministic checks only: they cannot tell whether a phrase is what a Chennai local would say (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACK = C["packs"]["chennai"]
SCENES = [d["scenario"] for d in PACK]
TA = LOCAL["chennai"]["ta"]
PHRASES = [p for d in PACK for p in d["phrases"]]
TUTOR_PHRASES = [p for it in TA["tutor"]["intents"] for p in it.get("phrases", [])] + TA["tutor"]["generic"]["phrases"]
TUTOR_PHRASES += [p for b in C["built"]["chennai"]["ta"] for p in b[0]["phrases"] + b[1]["phrases"][:2]]
READING_LINES = [l for r in TA["readings"] for l in r["lines"]]
HINDI_MARKERS = (" hai ", " hain ", " kya ", " kahan ", " mujhe ", " chahiye ", " kitna ", " kitne ", " mein ", " dijiye ", " bhaiya ", " accha ",
                 " achha ", " theek ", " aap ", " nahi ", " shukriya ", " chalo ", " yaar ")


def roman_text(items):
    return " " + " ".join(re.sub(r"[^\w\s]", " ", x).lower() for x in items) + " "


def scene_lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def scene_suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


def test_chennai_is_learnt_in_tamil_and_english():
    city = next(c for c in C["cities"] if c["id"] == "chennai")
    assert city["langs"] == ["ta", "en"] and city["ready"] is True                    # Hindi is not offered: no Hindi content was written
    assert {"code": "ta", "name": "Tamil", "native": "தமிழ்", "tts": "ta-IN"} in C["languages"]
    assert "chennai" not in C["language_packs"]


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["chennai"]["ready"] is True and cities["chennai"]["languages"] == ["ta", "en"]
    assert cities["bengaluru"]["languages"] == ["kn", "en"] and cities["mumbai"]["languages"] == ["hi", "mr", "en"]   # no other city changes
    assert [s for s, c in cities.items() if not c["ready"]] == []


def test_the_destination_card_has_its_other_name_an_introduction_and_a_preview():
    d = next(x for x in D if x["id"] == "chennai")
    assert d["status"] == "available" and d["alt"] == "Madras" and d["serves"] == [{"name": "Tamil Nadu", "type": "state"}]
    assert "Tamil" in d["intro"] and len(d["preview"]) == len(PACK) == 7 and all(d["preview"])


def test_the_pack_is_in_tamil_script_and_nothing_else():
    for p in PHRASES:
        assert TAMIL.search(p["hi"]) and not DEVANAGARI.search(p["hi"]) and not KANNADA.search(p["hi"]), p
        assert not re.search(r"[^\x00-ɏ‘’“”—–…₹]", p["roman"]), p
        assert "fem" not in p                                                            # Tamil's first-person verbs are not gendered
    every_text = json.dumps([PACK, TA, [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    assert not DEVANAGARI.search(every_text) and not KANNADA.search(every_text) and "।" not in every_text
    for p in TUTOR_PHRASES + READING_LINES:
        assert TAMIL.search(p["hi"]) and p["roman"], p


def test_the_pack_is_tamil_not_hindi():
    words = roman_text([p["roman"] for p in PHRASES])
    for marker in (" evvalavu ", " enga ", " kudunga ", " podunga ", " konjam ", " romba ", " vanakkam "):
        assert marker in words, marker
    everything = roman_text([p["roman"] for p in PHRASES + TUTOR_PHRASES + READING_LINES]
                            + [x for s in SCENES for x in scene_lines(C["scenarios"][s]) + scene_suggestions(C["scenarios"][s])])
    assert [m for m in HINDI_MARKERS if m in everything] == []
    assert TA["tutor"]["glossaryOnly"] is True and "jugaad" not in TA["tutor"]["glossary"]


def test_a_romanised_word_is_spelled_one_way():
    words = set(roman_text([p["roman"] for p in PHRASES + TUTOR_PHRASES + READING_LINES]
                           + [x for s in SCENES for x in scene_lines(C["scenarios"][s]) + scene_suggestions(C["scenarios"][s])]).split())
    for pair in (("evlo", "evvalavu"), ("enge", "enga"), ("kodunga", "kudunga"), ("nanri", "nandri"), ("vanakam", "vanakkam"), ("tanni", "thanni"),
                 ("aama", "aamaa"), ("paakalaam", "paakkalaam"), ("pudhusa", "pudhusaa")):
        assert not set(pair) <= words, pair


@pytest.mark.parametrize("sid", SCENES)
def test_a_chennai_roleplay_is_complete(sid):
    sc = C["scenarios"][sid]
    for field in ("icon", "title", "partner", "role", "place", "goal"):
        assert sc[field], field
    assert sc["opening"]["text"] and sc["opening"]["en"] and len(sc["start"]) >= 2
    assert len(sc["rules"]) >= 5 and sc["fallback"]["text"] and sc["fallback"]["en"] and sc["fallback"]["s"]
    for rule in sc["rules"]:
        assert rule["m"] and all(k == k.lower() and k.strip() for k in rule["m"]), rule["m"]
        assert rule["text"] and rule["en"] and rule["s"]
        assert ("{place}" in rule["text"]) <= ("places" in sc)
    assert sum(1 for rule in sc["rules"] if rule.get("end")) >= 1


@pytest.mark.parametrize("sid", SCENES)
def test_every_suggested_reply_gets_a_real_answer_and_every_hint_its_own(sid):
    sc = C["scenarios"][sid]
    assert [s for s in set(scene_suggestions(sc)) if first_match(sc, s) is None] == []
    for i, rule in enumerate(sc["rules"]):
        if rule.get("hint") and "{place}" not in rule["hint"]:
            assert first_match(sc, rule["hint"]) == i, (rule["hint"], first_match(sc, rule["hint"]))


@pytest.mark.parametrize("sid", SCENES)
def test_chennai_characters_do_not_assume_the_learners_gender(sid):
    sc = C["scenarios"][sid]
    said = roman_text(scene_lines(sc) + scene_suggestions(sc))
    for gendered in (" anna ", " akka ", " sir ", " madam ", " thambi ", " thangachi "):
        assert gendered not in said, (sid, gendered)


@pytest.mark.parametrize("text,expected", [("T. Nagar pogumaa?", "{place}? Sari, ukkaarunga."), ("Meter podunga.", "Meter podren"),
                                           ("Evvalavu aagum?", "Sumaar nooru"), ("Venaam, meter mattum.", "Sari sari, meter mattum"),
                                           ("Sari, meter-ku mela fifty.", "Sari, ukkaarunga!"), ("Evvalavu neram aagum?", "Indha neram traffic"),
                                           ("Inga niruthunga.", "Vandhaachu!"), ("GPay pannalaamaa?", "Nandri!")])
def test_the_auto_driver_answers_what_was_asked(text, expected):
    sc = C["scenarios"]["chn_auto"]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


@pytest.mark.parametrize("sid,text,expected", [("chn_food", "Oru filter coffee kudunga.", "Oru filter coffee"), ("chn_food", "Rendu idli kudunga.", "Rendu idli!"),
                                               ("chn_directions", "Pakkathula medical shop irukkaa?", "Aamaa, signal pakkathula"),
                                               ("chn_directions", "Ingirundhu dhooramaa?", "Nadandhaa pathu nimisham"),
                                               ("chn_college", "Meeting ethanai manikku?", "Team meeting pathu manikku"),
                                               ("chn_smalltalk", "Weekend Mahabalipuram polaamaa?", "Sari! Sunday"), ("chn_smalltalk", "Oru vaaram aachu.", "Oru vaaram dhaanaa")])
def test_the_other_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


def test_the_ai_is_asked_for_tamil_for_chennai(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    rp = {"mode": "roleplay", "city": "Chennai", "language": "Tamil", "level": "A1", "scenario": "chn_auto", "history": [{"role": "me", "text": "Vanakkam"}]}
    tutor = {"mode": "tutor", "city": "Chennai", "language": "Tamil", "level": "A1", "history": [{"role": "me", "text": "How do I ask for the meter?"}]}
    assert client.post("/api/ai", json=rp).status_code == 200 and client.post("/api/ai", json=tutor).status_code == 200
    roleplay, tutor_prompt = model.calls
    assert "learn Tamil " in roleplay and "romanised Tamil" in roleplay and "Murugan" in roleplay and "a real Chennai Auto driver" in roleplay
    assert "Hinglish" not in roleplay and "Hinglish" not in tutor_prompt
    assert "romanised Tamil" in tutor_prompt and "(Tamil script)" in tutor_prompt and "Devanagari" not in tutor_prompt


@pytest.mark.parametrize("city,scenario", [("Delhi", "auto"), ("Mumbai", "mum_taxi"), ("Bengaluru", "blr_auto")])
def test_a_city_that_does_not_offer_tamil_is_not_asked_for_in_tamil(client, monkeypatch, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "Tamil", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"] == [{"loc": ["body", "language"], "msg": "This city is not offered in Tamil", "type": "value_error"}]


def test_chennai_is_not_asked_for_in_kannada(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Chennai", "language": "Kannada", "level": "A1", "scenario": "chn_auto", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


@pytest.mark.parametrize("lang,ok_", [("ta", True), ("en", True), ("hi", False), ("kn", False)])
def test_a_saved_state_keeps_chennai_only_in_a_language_it_offers(client, lang, ok_):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'chennai-{lang}@example.com')['handle']}"
    r = client.put(url, json={"v": 1, "city": "chennai", "language": lang})
    assert (r.status_code == 200) is ok_


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const CHENNAI_PRICES")[1].split("];")[0])}


def test_the_fare_ranges_contain_the_sourced_fares():
    """Chennai Metro tokens cost ₹10 to ₹50 (CMRL). The official auto meter fare dates from 2013 (₹25 for 1.8 km, then ₹12 a km) and drivers
    quote their own, so the auto item is an agreed fare, never "by meter" (docs/CONTENT_REVIEW.md)."""
    assert PRICES["metro"] == (10, 50) and set(PRICES) == {"auto", "metro", "kurta", "tshirt", "idli", "coffee"}
    assert all(0 < lo < hi for lo, hi in PRICES.values())
    auto = APP.split("const CHENNAI_PRICES")[1].split("\n")[1]
    assert "agreed fare" in auto and "meter: true" not in auto
    assert "₹25 for the first 1.8 km, then ₹12 a km" in (ROOT / "frontend" / "content.js").read_text()


def test_tamil_has_a_font():
    html = (ROOT / "frontend" / "index.html").read_text()
    css = (ROOT / "frontend" / "styles.css").read_text()
    assert "family=Noto+Sans+Tamil:" in html and '"Noto Sans Tamil"' in css.split("--deva:")[1].split(";")[0]


def test_chennai_content_is_marked_as_awaiting_native_review():
    r = C["review"]["chennai"]["ta"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending")
    assert "not yet checked by a native Tamil speaker" in r["note"] and r["known_limitations"] and r["last_editorial_reviewed_at"] == "2026-10-18"


def test_the_documented_decision_matches_the_app():
    doc = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text()
    section = doc.split("## Chennai (Tamil)")[1]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-18): Available" in section
    assert next(x for x in D if x["id"] == "chennai")["status"] == "available"
