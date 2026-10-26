"""Bengaluru's First Week in Kannada (frontend/content.js PACKS.bengaluru, SCENARIOS.blr_*, LOCAL_CONTENT.bengaluru.kn): written in Kannada
script, not Devanagari, with no Hindi in it; every roleplay complete and answering what the learner says; the catalogue, the server's checks
and the AI prompt agreeing; the fair-price ranges containing the sourced fares; and the content honestly marked as awaiting native review.
Deterministic checks only: they cannot tell whether a phrase is what a Bengalurean would say (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, KANNADA, LOCAL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACK = C["packs"]["bengaluru"]
SCENES = [d["scenario"] for d in PACK]
KN = LOCAL["bengaluru"]["kn"]
PHRASES = [p for d in PACK for p in d["phrases"]]
TUTOR_PHRASES = [p for it in KN["tutor"]["intents"] for p in it.get("phrases", [])] + KN["tutor"]["generic"]["phrases"]
TUTOR_PHRASES += [p for b in C["built"]["bengaluru"]["kn"] for p in b[0]["phrases"] + b[1]["phrases"][:2]]
READING_LINES = [l for r in KN["readings"] for l in r["lines"]]
HINDI_MARKERS = (" hai ", " hain ", " kya ", " kahan ", " mujhe ", " chahiye ", " kitna ", " kitne ", " mein ", " dijiye ", " bhaiya ", " accha ",
                 " achha ", " theek ", " aap ", " nahi ", " shukriya ", " chalo ", " yaar ")


def roman_text(items):
    return " " + " ".join(re.sub(r"[^\w\s]", " ", x).lower() for x in items) + " "


def test_bengaluru_is_learnt_in_kannada_and_english():
    city = next(c for c in C["cities"] if c["id"] == "bengaluru")
    assert city["langs"] == ["kn", "en"] and city["ready"] is True                    # Hindi is not offered: no Hindi content was written
    assert {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "tts": "kn-IN"} in C["languages"]
    assert "bengaluru" not in C["language_packs"]                                       # the city's own pack is the Kannada one


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["bengaluru"]["ready"] is True and cities["bengaluru"]["languages"] == ["kn", "en"]
    assert cities["mumbai"]["languages"] == ["hi", "mr", "en"] and cities["delhi"]["languages"] == ["hi", "hinglish", "en"]   # no other city changes
    assert [s for s, c in cities.items() if not c["ready"]] == []


def test_the_destination_card_has_its_other_name_an_introduction_and_a_preview():
    d = next(x for x in D if x["id"] == "bengaluru")
    assert d["status"] == "available" and d["alt"] == "Bangalore" and d["serves"] == [{"name": "Karnataka", "type": "state"}]
    assert "Kannada" in d["intro"] and len(d["preview"]) == len(PACK) == 7 and all(d["preview"])   # one line per day of the pack
    assert not any("intro" in x or "preview" in x or "alt" in x for x in D if x["id"] not in ("bengaluru", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "hyderabad", "bhopal", "srinagar-jammu", "shimla"))   # Delhi's and Mumbai's cards are unchanged


def test_the_pack_is_in_kannada_script_and_has_no_devanagari():
    for p in PHRASES:
        assert KANNADA.search(p["hi"]) and not DEVANAGARI.search(p["hi"]), p
        assert not re.search(r"[^\x00-ɏ‘’“”—–…₹]", p["roman"]), p                # the romanised form is plain Roman letters
    every_text = json.dumps([PACK, KN, [C["scenarios"][s] for s in SCENES]], ensure_ascii=False)
    assert not DEVANAGARI.search(every_text) and "।" not in every_text                 # no Hindi script or Hindi danda anywhere
    for p in TUTOR_PHRASES + READING_LINES:
        assert KANNADA.search(p["hi"]) and p["roman"], p


def test_the_pack_is_kannada_not_hindi():
    words = roman_text([p["roman"] for p in PHRASES])
    for marker in (" eshtu ", " ellide ", " kodi ", " maadi ", " swalpa ", " tumba ", " namaskara "):   # everyday Kannada, all through the pack
        assert marker in words, marker
    everything = roman_text([p["roman"] for p in PHRASES + TUTOR_PHRASES + READING_LINES]
                            + [x for s in SCENES for x in scene_lines(C["scenarios"][s]) + scene_suggestions(C["scenarios"][s])])
    assert [m for m in HINDI_MARKERS if m in everything] == []
    assert KN["tutor"]["glossaryOnly"] is True and "jugaad" not in KN["tutor"]["glossary"]


def test_a_romanised_word_is_spelled_one_way():
    """Learners copy the romanised form: the same word is never spelled two ways across the Bengaluru content."""
    words = set(roman_text([p["roman"] for p in PHRASES + TUTOR_PHRASES + READING_LINES]
                           + [x for s in SCENES for x in scene_lines(C["scenarios"][s]) + scene_suggestions(C["scenarios"][s])]).split())
    for pair in (("tagoli", "tagolli"), ("yenu", "enu"), ("hegidira", "hegiddira"), ("dhanyavadagalu", "dhanyavaadagalu"), ("namaskar", "namaskara"),
                 ("bengaluruge", "bengalurige"), ("kadimey", "kadime"), ("jasti", "jaasti"), ("sakath", "sakkath")):
        assert not set(pair) <= words, pair


def test_every_day_has_its_tip_situation_and_a_gendered_form_where_one_is_needed():
    assert [d["key"] for d in PACK] == [c["key"] for c in C["categories"]] and all(s.startswith("blr_") for s in SCENES)
    fem = [p for p in PHRASES if "fem" in p]
    assert [(p["roman"], p["fem"]["roman"]) for p in fem] == [("Naanu illi hosaba.", "Naanu illi hosabalu.")]   # Kannada's first-person verbs are not gendered
    assert KANNADA.search(fem[0]["fem"]["hi"])


def scene_lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def scene_suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


@pytest.mark.parametrize("sid", SCENES)
def test_a_bengaluru_roleplay_is_complete(sid):
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
            assert first_match(sc, rule["hint"]) == i, (rule["hint"], first_match(sc, rule["hint"]))   # the "say it like a local" tip answers the same way


@pytest.mark.parametrize("sid", SCENES)
def test_bengaluru_characters_do_not_assume_the_learners_gender(sid):
    sc = C["scenarios"][sid]
    said = roman_text(scene_lines(sc) + scene_suggestions(sc))
    for gendered in (" hosaba ", " hosabalu ", " anna ", " akka ", " sir ", " madam "):
        assert gendered not in said, (sid, gendered)


@pytest.mark.parametrize("text,expected", [("Indiranagarakke bartira?", "{place}? Sari, kootkolli."), ("Meter haaki.", "Meter haaktini"),
                                           ("Eshtu aagutte?", "Meter-alli suumaaru"), ("Beda, meter maatra.", "Sari sari, meter maatra"),
                                           ("Sari, meter mele twenty.", "Sari, kootkolli!"), ("Eshtu hottu aagutte?", "Ee time traffic"),
                                           ("Ille nillisi.", "Bantu!"), ("UPI aagutta?", "Dhanyavaadagalu!")])
def test_the_auto_driver_answers_what_was_asked(text, expected):
    sc = C["scenarios"]["blr_auto"]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


@pytest.mark.parametrize("sid,text,expected", [("blr_food", "Ondu coffee kodi.", "Ondu filter coffee"), ("blr_food", "Ondu masale dose kodi.", "Ondu masale dose!"),
                                               ("blr_directions", "Hattira medical shop ideya?", "Haudu, signal hattira"),
                                               ("blr_directions", "Illinda doora ideya?", "Nadkondu hattu nimisha"),
                                               ("blr_college", "Meeting eshtu hottige?", "Team meeting hattu gantege"),
                                               ("blr_smalltalk", "Weekend Nandi Hillsge hogonva?", "Sari! Bhanuvaara"), ("blr_smalltalk", "Ondu vaara aaytu.", "Ondu vaara aaytu andre")])
def test_the_other_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


def test_the_ai_is_asked_for_kannada_for_bengaluru(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    rp = {"mode": "roleplay", "city": "Bengaluru", "language": "Kannada", "level": "A1", "scenario": "blr_auto", "history": [{"role": "me", "text": "Namaskara"}]}
    tutor = {"mode": "tutor", "city": "Bengaluru", "language": "Kannada", "level": "A1", "history": [{"role": "me", "text": "How do I ask for the meter?"}]}
    assert client.post("/api/ai", json=rp).status_code == 200 and client.post("/api/ai", json=tutor).status_code == 200
    roleplay, tutor_prompt = model.calls
    assert "learn Kannada " in roleplay and "romanised Kannada" in roleplay and "Manju" in roleplay and "a real Bengaluru Auto driver" in roleplay
    assert "Hinglish" not in roleplay and "Hinglish" not in tutor_prompt
    assert "romanised Kannada" in tutor_prompt and "(Kannada script)" in tutor_prompt and "Devanagari" not in tutor_prompt


def test_a_marathi_tutor_prompt_still_asks_for_devanagari(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "tutor", "city": "Mumbai", "language": "Marathi", "level": "A1", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    assert "(Devanagari)" in model.calls[0] and "romanised Marathi" in model.calls[0]


@pytest.mark.parametrize("city,scenario", [("Delhi", "auto"), ("Mumbai", "mum_taxi")])
def test_a_city_that_does_not_offer_kannada_is_not_asked_for_in_kannada(client, monkeypatch, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "Kannada", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"] == [{"loc": ["body", "language"], "msg": "This city is not offered in Kannada", "type": "value_error"}]


def test_bengaluru_is_not_asked_for_in_marathi(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Bengaluru", "language": "Marathi", "level": "A1", "scenario": "blr_auto", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


@pytest.mark.parametrize("lang", ["kn", "en"])
def test_a_saved_state_keeps_bengaluru_in_a_language_it_offers(client, lang):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'bengaluru-{lang}@example.com')['handle']}"
    assert client.put(url, json={"v": 1, "city": "bengaluru", "language": lang, "packDays": {"bengaluru": [1]}}).json() == {"ok": True}
    assert client.get(url).json()["state"] == {"v": 1, "city": "bengaluru", "language": lang, "packDays": {"bengaluru": [1]}}


# the fair-price ranges, read from frontend/app.js
APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const BENGALURU_PRICES")[1].split("];")[0])}


def test_the_fare_ranges_contain_the_sourced_fares():
    """Autos: ₹36 for the first 2 km, then ₹18 a km (from 1 August 2025), so 5 km is ₹90. Namma Metro: ₹10 to ₹90 (February 2025), and up to 5% a
    year more from February 2026, so the range allows ₹95 (docs/CONTENT_REVIEW.md)."""
    lo, hi = PRICES["auto"]
    assert lo <= 36 + 3 * 18 <= hi
    assert PRICES["metro"] == (10, 95) and round(90 * 1.05) <= 95
    assert set(PRICES) == {"auto", "metro", "kurta", "tshirt", "dosa", "coffee"}
    assert all(0 < lo < hi for lo, hi in PRICES.values())
    assert "₹36 for the first 2 km, then ₹18 a km" in KN_TEXT and "₹10–90 in the 2025 table" in APP


KN_TEXT = (ROOT / "frontend" / "content.js").read_text()


def test_kannada_has_a_font():
    html = (ROOT / "frontend" / "index.html").read_text()
    css = (ROOT / "frontend" / "styles.css").read_text()
    assert "family=Noto+Sans+Kannada:" in html and '"Noto Sans Kannada"' in css.split("--deva:")[1].split(";")[0]


def test_bengaluru_content_is_marked_as_awaiting_native_review():
    r = C["review"]["bengaluru"]["kn"]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending")
    assert "not yet checked by a native Kannada speaker" in r["note"] and r["known_limitations"] and r["last_editorial_reviewed_at"] == "2026-10-18"


def test_the_documented_decision_matches_the_app():
    """docs/CONTENT_REVIEW.md records Bengaluru as Available (a product decision) with a pending native review, as the destination and the
    review record say."""
    doc = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text()
    section = doc.split("## Bengaluru (Kannada)")[1]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-18): Available" in section
    assert next(x for x in D if x["id"] == "bengaluru")["status"] == "available"
    assert C["review"]["bengaluru"]["kn"]["native_review_status"] == "pending"
