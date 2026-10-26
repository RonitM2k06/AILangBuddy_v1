"""Hyderabad (Telugu · Urdu · English): the Telugu First Week pack (PACKS.hyderabad) and the Urdu one (LANGUAGE_PACKS.hyderabad.ur), their
roleplays, local content, prices and review records; right-to-left Urdu; the catalogue, the server's language checks and the AI prompt.
Deterministic checks only: they cannot tell whether a phrase is what a Hyderabadi would say (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import BENGALI, C, DEVANAGARI, KANNADA, LOCAL, TAMIL, TELUGU, URDU, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
TE_PACK = C["packs"]["hyderabad"]
UR_PACK = C["language_packs"]["hyderabad"]["ur"]
TE_SCENES = [d["scenario"] for d in TE_PACK]
UR_SCENES = [d["scenario"] for d in UR_PACK]
HINDI_MARKERS = (" hai ", " hain ", " kya ", " kahan ", " mujhe ", " chahiye ", " kitna ", " mein ", " dijiye ", " bhaiya ", " theek ", " aap ", " nahi ")
OTHER_CITIES = ("Connaught", "Churchgate", "Majestic", "Marina", "White Town", "Hawa Mahal", "Hazratganj", "Park Street")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


# ---------------------------------------------------------------------------------------------------------------------
# the city
# ---------------------------------------------------------------------------------------------------------------------
def test_hyderabad_is_learnt_in_telugu_urdu_and_english():
    city = next(c for c in C["cities"] if c["id"] == "hyderabad")
    assert city["langs"] == ["te", "ur", "en"] and city["ready"] is True and city["tag"] == "Telugu · Urdu"
    assert {"code": "te", "name": "Telugu", "native": "తెలుగు", "tts": "te-IN"} in C["languages"]
    assert {"code": "ur", "name": "Urdu", "native": "اردو", "tts": "ur-IN"} in C["languages"]
    assert list(C["language_packs"]["hyderabad"]) == ["ur"]                               # the city's own pack is the Telugu one


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["hyderabad"]["ready"] is True and cities["hyderabad"]["languages"] == ["te", "ur", "en"]
    assert [s for s, c in cities.items() if not c["ready"]] == []                         # every city in the catalogue is now ready
    assert cities["lucknow"]["languages"] == ["hi", "en"]                                 # Lucknow does not get Urdu


def test_the_destination_card():
    d = next(x for x in D if x["id"] == "hyderabad")
    assert d["status"] == "available" and d["city"] == "hyderabad" and d["alt"] == "The City of Pearls" and d["serves"] == [{"name": "Telangana", "type": "state"}]
    assert "Telugu" in d["intro"] and "Urdu" in d["intro"] and len(d["preview"]) == 7


# ---------------------------------------------------------------------------------------------------------------------
# the Telugu pack
# ---------------------------------------------------------------------------------------------------------------------
def test_the_telugu_pack_is_telugu():
    phrases = [p for d in TE_PACK for p in d["phrases"]]
    assert len(phrases) == 35
    for p in phrases:
        assert TELUGU.search(p["hi"]) and not any(s.search(p["hi"]) for s in (DEVANAGARI, KANNADA, TAMIL, BENGALI, URDU)) and p["roman"], p
    everything = words([p["roman"] for p in phrases] + [x for s in TE_SCENES for x in lines(C["scenarios"][s]) + suggestions(C["scenarios"][s])])
    assert [m for m in HINDI_MARKERS if m in everything] == []
    for marker in (" entha ", " ekkada ", " ivvandi ", " namaskaram ", " undaa ", " chaala "):
        assert marker in words([p["roman"] for p in phrases]), marker
    assert [p for p in phrases if "fem" in p] == []                                      # Telugu's "I" and "you" verbs do not change for gender


def test_the_telugu_pack_is_hyderabads_own():
    text = json.dumps([TE_PACK, [C["scenarios"][s] for s in TE_SCENES]], ensure_ascii=False)
    for place in ("Secunderabad", "Banjara Hills", "Charminar", "Laad Bazaar", "Chowmahalla", "HITEC City", "Tank Bund", "Golconda", "Madhapur"):
        assert place in text, place
    for other in OTHER_CITIES:
        assert other not in text, other
    assert all(s.startswith("hyd_") and not s.startswith("hyd_ur_") for s in TE_SCENES)


# ---------------------------------------------------------------------------------------------------------------------
# the Urdu pack
# ---------------------------------------------------------------------------------------------------------------------
def test_the_urdu_pack_is_urdu_in_urdu_script():
    phrases = [p for d in UR_PACK for p in d["phrases"]]
    assert [d["day"] for d in UR_PACK] == list(range(1, 8)) and len(phrases) == 35
    for p in phrases:
        assert URDU.search(p["hi"]) and not DEVANAGARI.search(p["hi"]) and not TELUGU.search(p["hi"]) and p["roman"] and not URDU.search(p["roman"]), p
    assert sum(1 for p in phrases if p["hi"].endswith("۔")) >= 10                         # Urdu's own full stop, not the Hindi danda
    assert not any("।" in p["hi"] for p in phrases)
    romans = words([p["roman"] for p in phrases])
    for hyderabadi in (" hau ", " kya re ", " idhar "):                                    # Hyderabad's own Urdu
        assert hyderabadi in romans, hyderabadi
    assert all(s.startswith("hyd_ur_") for s in UR_SCENES)


def test_the_gendered_urdu_phrase_shows_the_feminine_form():
    fem = [(p["roman"], p["fem"]["roman"]) for d in UR_PACK for p in d["phrases"] if "fem" in p]
    assert fem == [("Main yahan naya hoon.", "Main yahan nayi hoon.")]
    assert all(URDU.search(p["fem"]["hi"]) for d in UR_PACK for p in d["phrases"] if "fem" in p)


@pytest.mark.parametrize("sid", UR_SCENES)
def test_the_urdu_characters_do_not_assume_the_learner_is_male(sid):
    sc = C["scenarios"][sid]
    said_to = " " + " ".join(lines(sc)).lower() + " "
    for masc in (" saheb", "naye aaye", "rahe ho", "aap naye", "tum naye", "dhoond rahe", "aaye ho"):
        assert masc not in said_to, (sid, masc)
    said_by = words(suggestions(sc) + [r["hint"] for r in sc["rules"] if r.get("hint")])
    for masc in (" naya hoon", " aaya hoon", " doonga", " loonga", " de raha", " samajh gaya ", " bhool gaya"):
        assert masc not in said_by, (sid, masc)


def test_urdu_is_shown_right_to_left():
    css = (ROOT / "frontend" / "styles.css").read_text()
    deva = next(l for l in css.splitlines() if l.startswith(".deva {"))
    assert "unicode-bidi: plaintext" in deva                                                # each line takes the direction of its own text
    stack = css.split("--deva:")[1].split(";")[0]
    html = (ROOT / "frontend" / "index.html").read_text()
    for font in ("Noto Sans Telugu", "Noto Nastaliq Urdu"):
        assert f'"{font}"' in stack and "family=" + font.replace(" ", "+") + ":" in html, font


# ---------------------------------------------------------------------------------------------------------------------
# the roleplays
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sid", TE_SCENES + UR_SCENES)
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
    ("hyd_auto", "Banjara Hills vastaaraa?", "{place}? Sare, ekkandi."), ("hyd_auto", "Meter veyandi.", "Meter vestaanu, kaani"),
    ("hyd_auto", "Vaddu, meter meeda ekkuva ivvanu.", "Sare, meter meedane vastaanu."), ("hyd_auto", "Entha sepu padutundi?", "Traffic unte"),
    ("hyd_auto", "Entha avutundi?", "Banjara Hills aa?"), ("hyd_food", "Kaaram takkuva veyandi.", "Sare, kaaram takkuva."),
    ("hyd_shopping", "Ivi lakk gaajulaa?", "Avunu, ivi lakk gaajulu"),
    ("hyd_ur_auto", "Metro station kidhar hai?", "Metro chahiye toh"), ("hyd_ur_auto", "Bas, idhar roko.", "Lo, aa gaye Charminar!"),
    ("hyd_ur_auto", "Nakko, meter se zyaada nahi.", "Achha, achha, meter se hi"), ("hyd_ur_shopping", "Asli moti hain?", "Bilkul asli!"),
    ("hyd_ur_smalltalk", "Hyderabad ki biryani ka jawaab nahi!", "Bilkul! Aur Ramzan mein haleem"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


# ---------------------------------------------------------------------------------------------------------------------
# local content, prices, review
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang,name,greet,script", [("te", "Telugu", "Namaskaram", TELUGU), ("ur", "Urdu", "Assalaam alaikum", URDU)])
def test_the_local_content_is_in_its_language(lang, name, greet, script):
    entry = LOCAL["hyderabad"][lang]
    tutor = entry["tutor"]
    assert tutor["language"] == name and tutor["greet"] == greet and tutor["glossaryOnly"] is True and "jugaad" not in tutor["glossary"]
    assert tutor["polite"]["rules"] and entry["achievements"]["first-words"][2] == f"Said your first {name} phrase"
    phrases = [p for it in tutor["intents"] for p in it.get("phrases", [])] + tutor["generic"]["phrases"] + [l for r in entry["readings"] for l in r["lines"]]
    assert phrases and all(script.search(p["hi"]) for p in phrases)
    scenes = TE_SCENES if lang == "te" else UR_SCENES
    assert len(entry["rightNow"]) == 5 and all(slot[5] in scenes for slot in entry["rightNow"])


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const HYDERABAD_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """Hyderabad Metro ₹11–69 (fixed, from 24 May 2025); autos are an agreed fare."""
    assert PRICES["metro"] == (11, 69) and set(PRICES) == {"auto", "metro", "bangles", "pearls", "biryani", "chai"}
    auto = APP.split("const HYDERABAD_PRICES")[1].split("\n")[1]
    assert "agreed fare" in auto and "meter: true" not in auto
    assert "hyderabad: HYDERABAD_PRICES" in APP


@pytest.mark.parametrize("lang,who", [("te", "Telugu"), ("ur", "Urdu")])
def test_both_languages_are_marked_as_awaiting_native_review(lang, who):
    r = C["review"]["hyderabad"][lang]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and f"native {who} speaker" in r["note"]


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Hyderabad (Telugu and Urdu)")[1].split("\n## ")[0]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-19): Available" in section


# ---------------------------------------------------------------------------------------------------------------------
# the server: who may be asked for Telugu and Urdu, and how
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("language,scenario,partner,script", [("Telugu", "hyd_auto", "Srinu", "Telugu script"), ("Urdu", "hyd_ur_auto", "Salim bhai", "Urdu script")])
def test_the_ai_is_asked_for_telugu_or_urdu_for_hyderabad(client, monkeypatch, language, scenario, partner, script):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    rp = {"mode": "roleplay", "city": "Hyderabad", "language": language, "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    tutor = {"mode": "tutor", "city": "Hyderabad", "language": language, "level": "A1", "history": [{"role": "me", "text": "How do I order biryani?"}]}
    assert client.post("/api/ai", json=rp).status_code == 200 and client.post("/api/ai", json=tutor).status_code == 200
    roleplay, tutor_prompt = model.calls
    assert f"learn {language} " in roleplay and f"romanised {language}" in roleplay and partner in roleplay and "a real Hyderabad " in roleplay
    assert "Hinglish" not in roleplay + tutor_prompt and script in tutor_prompt and "Devanagari" not in tutor_prompt


@pytest.mark.parametrize("language", ["Telugu", "Urdu"])
@pytest.mark.parametrize("city,scenario", [("Lucknow", "lko_auto"), ("Chennai", "chn_auto"), ("Delhi", "auto")])
def test_only_hyderabad_is_asked_for_in_telugu_or_urdu(client, monkeypatch, language, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": language, "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == f"This city is not offered in {language}"


@pytest.mark.parametrize("lang,accepted", [("te", True), ("ur", True), ("en", True), ("hi", False), ("ta", False), ("hinglish", False)])
def test_a_saved_state_keeps_hyderabad_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'hyd-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "hyderabad", "language": lang}).status_code == 200) is accepted
