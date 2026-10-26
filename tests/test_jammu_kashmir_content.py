"""Jammu & Kashmir (Kashmiri · Dogri · Urdu · English): the Kashmiri First Week pack (PACKS.jk), the Dogri and Urdu ones
(LANGUAGE_PACKS.jk), their roleplays, local content, prices and review records; the In Development status and the draft labels; the
catalogue, the server's language checks and the AI prompt. Deterministic checks only: they cannot tell whether a phrase is right, which matters
more here than anywhere, since the Kashmiri and Dogri are a lower-confidence draft (docs/CONTENT_REVIEW.md)."""
import json
import re
from pathlib import Path

import pytest

from backend import main

from .test_city_packs import C, DEVANAGARI, LOCAL, TELUGU, URDU, Model, first_match
from .test_destinations import D

ROOT = Path(__file__).resolve().parent.parent
PACKS = {"ks": C["packs"]["jk"], "doi": C["language_packs"]["jk"]["doi"], "ur": C["language_packs"]["jk"]["ur"]}
SCENES = {lang: [d["scenario"] for d in pack] for lang, pack in PACKS.items()}
SCRIPT = {"ks": URDU, "doi": DEVANAGARI, "ur": URDU}
KASHMIRI_ONLY = re.compile("[ؠٕٚٛٲۄ]")                          # letters and vowel signs Urdu does not use
NAMES = {"ks": "Kashmiri", "doi": "Dogri", "ur": "Urdu"}


def lines(sc):
    return [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]


def suggestions(sc):
    return list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]


def words(items):
    return " " + " ".join(re.sub(r"[^\w\s']", " ", x).lower() for x in items) + " "


# ---------------------------------------------------------------------------------------------------------------------
# the city
# ---------------------------------------------------------------------------------------------------------------------
def test_jk_is_learnt_in_kashmiri_dogri_urdu_and_english():
    city = next(c for c in C["cities"] if c["id"] == "jk")
    assert city["langs"] == ["ks", "doi", "ur", "en"] and city["ready"] is True and city["name"] == "Jammu & Kashmir"
    assert {"code": "ks", "name": "Kashmiri", "native": "کٲشُر", "tts": "ks-IN"} in C["languages"]
    assert {"code": "doi", "name": "Dogri", "native": "डोगरी", "tts": "doi-IN"} in C["languages"]
    assert list(C["language_packs"]["jk"]) == ["doi", "ur"]


def test_the_catalogue_agrees(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["jk"]["ready"] is True and cities["jk"]["languages"] == ["ks", "doi", "ur", "en"]
    assert cities["hyderabad"]["languages"] == ["te", "ur", "en"]                          # Hyderabad keeps its own Urdu pack


def test_the_destination_is_in_development_not_available():
    """The Kashmiri and Dogri are a lower-confidence draft: the card says In Development and the introduction says it is a draft."""
    d = next(x for x in D if x["id"] == "srinagar-jammu")
    assert d["status"] == "in_development" and d["city"] == "jk" and d["serves"] == [{"name": "Jammu and Kashmir", "type": "ut"}]
    assert "draft" in d["intro"] and all(w in d["intro"] for w in ("Kashmiri", "Dogri", "Urdu")) and len(d["preview"]) == 7


# ---------------------------------------------------------------------------------------------------------------------
# the packs
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang", PACKS)
def test_each_pack_is_in_its_own_script(lang):
    phrases = [p for d in PACKS[lang] for p in d["phrases"]]
    assert [d["day"] for d in PACKS[lang]] == list(range(1, 8)) and len(phrases) == 35
    for p in phrases:
        assert SCRIPT[lang].search(p["hi"]) and not TELUGU.search(p["hi"]) and p["roman"] and not SCRIPT[lang].search(p["roman"]), p
    if lang == "ks":
        assert sum(1 for p in phrases if KASHMIRI_ONLY.search(p["hi"])) >= 10                # Kashmiri's own letters, not just Urdu spelling
    if lang == "ur":
        assert not any(KASHMIRI_ONLY.search(p["hi"]) for p in phrases)
    if lang == "doi":
        assert not URDU.search(json.dumps(PACKS[lang], ensure_ascii=False))


@pytest.mark.parametrize("lang,fem", [("ks", [("Bu chhus yeti nov.", "Bu chhes yeti nev.")]), ("doi", [("Main itthen namaan aan.", "Main itthen nameen aan.")]),
                                      ("ur", [("Main yahan naya hoon.", "Main yahan nayi hoon.")])])
def test_each_gendered_phrase_shows_its_feminine_form(lang, fem):
    assert [(p["roman"], p["fem"]["roman"]) for d in PACKS[lang] for p in d["phrases"] if "fem" in p] == fem


def test_the_packs_are_set_where_their_language_is_spoken():
    text = {lang: json.dumps([PACKS[lang], [C["scenarios"][s] for s in SCENES[lang]]], ensure_ascii=False) for lang in PACKS}
    for place in ("Dal", "Lal Chowk", "Nishat Bagh", "University of Kashmir", "shikara"):
        assert place in text["ks"], place
    for place in ("Jammu Tawi", "Raghunath", "Bagh-e-Bahu", "University of Jammu", "Katra", "matador"):
        assert place in text["doi"], place
    assert "Srinagar" in text["ur"] and "Jammu" in text["ur"]                               # Urdu covers both capitals
    assert "Raghunath" not in text["ks"] and "Dal Lake" not in text["doi"]
    for other in ("Charminar", "Hazratganj", "Connaught", "Laad Bazaar", "hau,", "nakko"):  # no Hyderabadi Urdu in J&K
        assert other not in text["ur"], other


# ---------------------------------------------------------------------------------------------------------------------
# the roleplays
# ---------------------------------------------------------------------------------------------------------------------
ALL_SCENES = SCENES["ks"] + SCENES["doi"] + SCENES["ur"]


@pytest.mark.parametrize("sid", ALL_SCENES)
def test_every_roleplay_is_complete_and_answers_every_suggestion(sid):
    sc = C["scenarios"][sid]
    for field in ("icon", "title", "partner", "role", "place", "goal"):
        assert sc[field], field
    assert sc["opening"]["text"] and sc["opening"]["en"] and len(sc["start"]) >= 2 and len(sc["rules"]) >= 5
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
def test_no_suggestion_makes_the_learner_use_a_masculine_form(sid):
    sc = C["scenarios"][sid]
    said_by = words(suggestions(sc) + [r["hint"] for r in sc["rules"] if r.get("hint")])
    for masc in (" bu chhus ", " namaan aan", " naya hoon", " aaya hoon", " doonga", " loonga", " samajh gaya ", " bhool gaya"):
        assert masc not in said_by, (sid, masc)
    said_to = " " + " ".join(lines(sc)).lower() + " "
    for masc in ("naye aaye", "rahe ho", "aap naye", "tum naye", "naye ho", "dhoond rahe"):
        assert masc not in said_to, (sid, masc)


@pytest.mark.parametrize("sid,text,expected", [
    ("jk_auto", "Kotah poonsa?", "Nishat Bagh? Doyi hath."), ("jk_auto", "Shikaara kati meli?", "Shikaara meli Dal Gate"), ("jk_auto", "Aa, gwodaniuk lati.", "Khosh aamdeed!"),
    ("jk_food", "Noon chai chha?", "Aa, garam noon chai!"), ("jk_shopping", "Yi chha asal pashmina?", "Aa, asal!"),
    ("jk_doi_auto", "Matador kutthen thammdi ai?", "Matador baahar stand"), ("jk_doi_food", "Rajmah-chaul bi deo.", "Rajmah-chaul garam ai!"),
    ("jk_doi_directions", "Raghunath Mandar kutthen ai?", "Siddhe jao, phi sajje mudo."),
    ("jk_ur_auto", "Shikaara kahan milega?", "Shikaara Dal Gate ke ghaat par"), ("jk_ur_greetings", "Raat ko heater milega?", "Ji, heater hai"),
])
def test_the_roleplays_answer_what_was_asked(sid, text, expected):
    sc = C["scenarios"][sid]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


# ---------------------------------------------------------------------------------------------------------------------
# local content, prices, review
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lang", PACKS)
def test_the_local_content_is_in_its_language(lang):
    entry = LOCAL["jk"][lang]
    tutor = entry["tutor"]
    assert tutor["language"] == NAMES[lang] and tutor["glossaryOnly"] is True and "jugaad" not in tutor["glossary"]
    assert entry["achievements"]["first-words"][2] == f"Said your first {NAMES[lang]} phrase"
    phrases = [p for it in tutor["intents"] for p in it.get("phrases", [])] + tutor["generic"]["phrases"] + [l for r in entry["readings"] for l in r["lines"]]
    assert phrases and all(SCRIPT[lang].search(p["hi"]) for p in phrases)
    assert len(entry["rightNow"]) == 5 and all(slot[5] in SCENES[lang] for slot in entry["rightNow"])


@pytest.mark.parametrize("lang,draft", [("ks", True), ("doi", True), ("ur", False)])
def test_the_review_records_say_draft_where_it_is_one(lang, draft):
    r = C["review"]["jk"][lang]
    assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and f"native {NAMES[lang]} speaker" in r["note"]
    assert ("draft" in r["note"]) is draft and (any(l.startswith("Draft:") for l in r["known_limitations"])) is draft
    if lang != "ur":
        assert any(f"no {NAMES[lang]} voice" in l for l in r["known_limitations"])


APP = (ROOT / "frontend" / "app.js").read_text()
PRICES = {m[0]: (int(m[1]), int(m[2])) for m in re.findall(r'\{ id: "(\w+)", label: "[^"]*", min: (\d+), max: (\d+)', APP.split("const JK_PRICES")[1].split("];")[0])}


def test_the_fare_ranges():
    """The official Dal Lake shikara rate (about ₹770 for the first hour per boat); autos an agreed fare; matadors per seat."""
    assert PRICES["shikara"] == (700, 800) and set(PRICES) == {"auto", "shikara", "matador", "pashmina", "kahwa", "kalari"}
    auto = APP.split("const JK_PRICES")[1].split("\n")[1]
    assert "agreed fare" in auto and "jk: JK_PRICES" in APP and "₹770" in APP


def test_the_documented_decision_matches_the_app():
    section = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text().split("## Jammu & Kashmir (Kashmiri, Dogri and Urdu)")[1].split("\n## ")[0]
    assert "native-speaker review pending" in section and "### Status decision (2026-10-19): In Development" in section and "lower confidence" in section


# ---------------------------------------------------------------------------------------------------------------------
# the server: who may be asked for Kashmiri and Dogri, and how
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("language,scenario,partner", [("Kashmiri", "jk_auto", "Mushtaq"), ("Dogri", "jk_doi_auto", "Kuldeep"), ("Urdu", "jk_ur_auto", "Farooq")])
def test_the_ai_is_asked_for_each_language_for_jk(client, monkeypatch, language, scenario, partner):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Jammu & Kashmir", "language": language, "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert f"learn {language} " in system and f"romanised {language}" in system and partner in system and "Hinglish" not in system


@pytest.mark.parametrize("language", ["Kashmiri", "Dogri"])
@pytest.mark.parametrize("city,scenario", [("Hyderabad", "hyd_ur_auto"), ("Delhi", "auto"), ("Lucknow", "lko_auto")])
def test_only_jk_is_asked_for_in_kashmiri_or_dogri(client, monkeypatch, language, city, scenario):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": language, "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == f"This city is not offered in {language}"


@pytest.mark.parametrize("lang,accepted", [("ks", True), ("doi", True), ("ur", True), ("en", True), ("hi", False), ("te", False)])
def test_a_saved_state_keeps_jk_only_in_a_language_it_offers(client, lang, accepted):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'jk-{lang}@example.com')['handle']}"
    assert (client.put(url, json={"v": 1, "city": "jk", "language": lang}).status_code == 200) is accepted
