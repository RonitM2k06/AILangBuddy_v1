"""Puducherry (Tamil · French · English): the Tamil First Week pack (PACKS.puducherry) and the French one (LANGUAGE_PACKS.puducherry.fr), their
roleplays, local content, prices and review records; the catalogue, the server's language checks and the AI prompt. Deterministic checks
only: they cannot tell whether a phrase is what a Puducherry local would say (docs/CONTENT_REVIEW.md)."""
import json
import re
import unicodedata
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, FRENCH, KANNADA, LOCAL, TAMIL, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
TA_PACK = C["packs"]["puducherry"]
FR_PACK = C["language_packs"]["puducherry"]["fr"]
TA_SCENES = [d["scenario"] for d in TA_PACK]
FR_SCENES = [d["scenario"] for d in FR_PACK]
HINDI_MARKERS = (" hai ", " hain ", " kya ", " kahan ", " mujhe ", " chahiye ", " kitna ", " mein ", " dijiye ", " bhaiya ", " theek ", " aap ", " nahi ")


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


def no_accents(text):
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if not "̀" <= ch <= "ͯ")


# ---------------------------------------------------------------------------------------------------------------------
# the city
# ---------------------------------------------------------------------------------------------------------------------
def test_puducherry_is_learnt_in_tamil_french_and_english():
    city = next(c for c in C["cities"] if c["id"] == "puducherry")
    assert city["langs"] == ["ta", "fr", "en"] and city["ready"] is True
    assert list(C["language_packs"]["puducherry"]) == ["fr"]                          # the city's own pack is the Tamil one


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["puducherry"]["ready"] is True and cities["puducherry"]["languages"] == ["ta", "fr", "en"]
    assert cities["chennai"]["languages"] == ["ta", "en"]                              # Chennai does not get French
    assert [s for s, c in cities.items() if not c["ready"]] == []


def test_the_destination_card():
    d = next(x for x in D if x["id"] == "puducherry")
    assert d["status"] == "available" and d["city"] == "puducherry" and d["alt"] == "Pondicherry" and d["serves"] == [{"name": "Puducherry", "type": "ut"}]
    assert "Tamil" in d["intro"] and "French" in d["intro"] and len(d["preview"]) == 7


# ---------------------------------------------------------------------------------------------------------------------
# the Tamil pack
# ---------------------------------------------------------------------------------------------------------------------
def test_the_tamil_pack_is_tamil():
    phrases = [p for d in TA_PACK for p in d["phrases"]]
    for p in phrases:
        assert TAMIL.search(p["hi"]) and not DEVANAGARI.search(p["hi"]) and not KANNADA.search(p["hi"]) and p["roman"], p
    text = json.dumps([TA_PACK, LOCAL["puducherry"]["ta"], [C["scenarios"][s] for s in TA_SCENES]], ensure_ascii=False)
    assert not DEVANAGARI.search(text) and "।" not in text
    everything = words([p["roman"] for p in phrases] + [x for s in TA_SCENES for x in lines(C["scenarios"][s]) + suggestions(C["scenarios"][s])])
    assert [m for m in HINDI_MARKERS if m in everything] == []
    for marker in (" evvalavu ", " enga ", " kudunga ", " vanakkam ", " romba "):
        assert marker in words([p["roman"] for p in phrases]), marker


def test_the_tamil_pack_is_puducherrys_not_chennais():
    text = json.dumps([TA_PACK, [C["scenarios"][s] for s in TA_SCENES]], ensure_ascii=False)
    for place in ("White Town", "Auroville", "Promenade", "Goubert", "Mission Street"):
        assert place in text, place
    for chennai_only in ("T. Nagar", "Mylapore", "OMR", "Marina", "Ranganathan"):
        assert chennai_only not in text, chennai_only
    chennai = {p["roman"] for d in C["packs"]["chennai"] for p in d["phrases"]}
    assert len([p for d in TA_PACK for p in d["phrases"] if p["roman"] in chennai]) == 0                         # its own phrases


# ---------------------------------------------------------------------------------------------------------------------
# the French pack
# ---------------------------------------------------------------------------------------------------------------------
def test_the_french_pack_is_french_with_accents_and_a_pronunciation_guide():
    phrases = [p for d in FR_PACK for p in d["phrases"]]
    assert [d["day"] for d in FR_PACK] == list(range(1, 8)) and len(phrases) == 35
    for p in phrases:
        assert FRENCH.search(p["hi"]) and not TAMIL.search(p["hi"]) and not DEVANAGARI.search(p["hi"]), p
        assert no_accents(p["hi"]) == p["roman"], p                                    # `roman` is the same French without its accents
        assert p["pron"] and p["pron"] != p["roman"], p                                # and a pronunciation guide for English speakers
    assert sum(1 for p in phrases if p["hi"] != p["roman"]) >= 15                       # accents are really there
    accented = " ".join(p["hi"] for p in phrases)
    for word in ("déjeuner", "vélo", "café", "épicé", "où", "à"):
        assert word in accented, word


def test_the_gendered_french_phrases_show_the_feminine_form():
    fem = [(p["roman"], p["fem"]["roman"]) for d in FR_PACK for p in d["phrases"] if "fem" in p]
    assert fem == [("Je suis nouveau ici.", "Je suis nouvelle ici."), ("Je suis vegetarien.", "Je suis vegetarienne.")]


def test_the_french_roleplays_never_assume_the_learners_gender():
    """A character may speak about herself in the feminine ("Enchantée"), but never assumes who the learner is, and no suggestion makes the
    learner use a masculine form."""
    for sid in FR_SCENES:
        sc = C["scenarios"][sid]
        said_to = words(lines(sc))
        for masc in (" tu es nouveau ", " vous etes nouveau ", " prudent ", " monsieur alex ", " cher ami "):
            assert masc not in " " + no_accents(said_to) + " ", (sid, masc)
        said_by = no_accents(words(suggestions(sc)))
        for masc in (" nouveau ", " vegetarien ", " perdu ", " ne ici ", " content "):
            assert masc not in said_by, (sid, masc)


def test_french_uses_vous_with_strangers_and_tu_with_friends():
    rosaline, sophie = C["scenarios"]["pdy_fr_greetings"], C["scenarios"]["pdy_fr_college"]
    assert "vous" in words(lines(rosaline)) and " tu " not in words(lines(rosaline))
    assert " tu " in words(lines(sophie)) or " te " in words(lines(sophie)) or "ton" in words(lines(sophie))


@pytest.mark.parametrize("sid", TA_SCENES + FR_SCENES)
def test_every_roleplay_is_complete_and_answers_every_suggestion(sid):
    sc = C["scenarios"][sid]
    for field in ("icon", "title", "partner", "role", "place", "goal"):
        assert sc[field], field
    assert sc["opening"]["text"] and sc["opening"]["en"] and len(sc["start"]) >= 2 and len(sc["rules"]) >= 5
    for rule in sc["rules"]:
        assert rule["m"] and all(k == no_accents(k).lower() and k.strip() for k in rule["m"]), rule["m"]   # keywords without accents
    assert sum(1 for rule in sc["rules"] if rule.get("end")) >= 1
    assert [s for s in set(suggestions(sc)) if first_match(sc, s) is None] == []
    for i, rule in enumerate(sc["rules"]):
        if rule.get("hint"):
            assert first_match(sc, rule["hint"]) == i, (rule["hint"], first_match(sc, rule["hint"]))


@pytest.mark.parametrize("sid,text,expected", [
    ("pdy_scooter", "Scooter vaadagaikku kidaikkumaa?", "Kidaikkum!"), ("pdy_scooter", "Oru naalaikku evvalavu?", "Oru naalaikku naanooru"),
    ("pdy_scooter", "Romba adhigam, konjam koraiyunga.", "Sari, ungalukku munnooru"), ("pdy_food", "Innikku enna fresh meen irukku?", "Innikku vanjiram"),
    ("pdy_fr_bike", "Je voudrais louer un velo.", "Bien sûr !"), ("pdy_fr_bike", "C'est combien pour la journée ?", "C'est cent cinquante"),
    ("pdy_fr_bike", "C'est loin d'ici ?", "À vélo"), ("pdy_fr_food", "Qu'est-ce que vous recommandez ?", "Le curry créole"),
    ("pdy_fr_directions", "Je cherche l'Alliance française.", "L'Alliance française ?"), ("pdy_fr_smalltalk", "Tu es d'ici ?", "Oui, je suis né ici"),
])
def test_the_roleplays_answer_what_was_asked_with_or_without_accents(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)
    assert first_match(sc, text) == first_match(sc, no_accents(text))


# ---------------------------------------------------------------------------------------------------------------------
# local content, prices, review
# ---------------------------------------------------------------------------------------------------------------------
def test_the_french_local_content_is_french():
    fr = LOCAL["puducherry"]["fr"]
    assert fr["tutor"]["language"] == "French" and fr["tutor"]["greet"] == "Bonjour" and fr["tutor"]["glossaryOnly"] is True
    phrases = [p for it in fr["tutor"]["intents"] for p in it.get("phrases", [])] + [l for r in fr["readings"] for l in r["lines"]]
    assert phrases and all(FRENCH.search(p["hi"]) and p["roman"] == p["hi"] for p in phrases)      # not graded: shown as written
    assert fr["achievements"]["first-words"][2] == "Said your first French phrase"


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const PUDUCHERRY_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """Scooter rental ₹300–700 a day (rental shops' published rates). Autos don't use meters, so the auto item is an agreed fare."""
    assert PRICES["scooter"] == (300, 700) and set(PRICES) == {"auto", "scooter", "bicycle", "bag", "fishmeal", "coffee"}
    auto = APP.split("const PUDUCHERRY_PRICES")[1].split("\n")[1]
    assert "agreed fare" in auto and "meter: true" not in auto


def test_both_languages_are_marked_as_awaiting_native_review():
    for lang, who in (("ta", "Tamil"), ("fr", "French")):
        r = C["review"]["puducherry"][lang]
        assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and f"native {who} speaker" in r["note"]


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Puducherry (Tamil and French)")[1]
    assert "native-speaker review pending" in section and "### Availability decision (2026-10-18): Available" in section


# ---------------------------------------------------------------------------------------------------------------------
# the server: who may be asked for French, and how
# ---------------------------------------------------------------------------------------------------------------------
def test_the_ai_is_asked_for_french_for_puducherry(client, monkeypatch):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    rp = {"mode": "roleplay", "city": "Puducherry", "language": "French", "level": "A1", "scenario": "pdy_fr_bike", "history": [{"role": "me", "text": "Bonjour"}]}
    tutor = {"mode": "tutor", "city": "Puducherry", "language": "French", "level": "A1", "history": [{"role": "me", "text": "How do I rent a bike?"}]}
    assert client.post("/api/ai", json=rp).status_code == 200 and client.post("/api/ai", json=tutor).status_code == 200
    roleplay, tutor_prompt = model.calls
    assert "learn French " in roleplay and "natural French" in roleplay and "romanised French" not in roleplay and "Monsieur Pierre" in roleplay
    assert "Hinglish" not in roleplay + tutor_prompt and "Devanagari" not in tutor_prompt and "romanised French" not in tutor_prompt


@pytest.mark.parametrize("city,scenario", [("Chennai", "chn_auto"), ("Delhi", "auto"), ("Mumbai", "mum_taxi")])
def test_only_puducherry_is_asked_for_in_french(client, monkeypatch, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "French", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == "This city is not offered in French"


def test_puducherry_may_be_asked_for_in_tamil_but_not_kannada(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    ok = {"mode": "roleplay", "city": "Puducherry", "language": "Tamil", "level": "A1", "scenario": "pdy_food", "history": [{"role": "me", "text": "Vanakkam"}]}
    assert client.post("/api/ai", json=ok).status_code == 200
    assert client.post("/api/ai", json={**ok, "language": "Kannada"}).status_code == 422


@pytest.mark.parametrize("lang,accepted", [("ta", True), ("fr", True), ("en", True), ("hi", False), ("kn", False)])
def test_a_saved_state_keeps_puducherry_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'pdy-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "puducherry", "language": lang}).status_code == 200) is accepted
