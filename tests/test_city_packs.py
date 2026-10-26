"""City packs for "I'm New Here" (Mumbai added after Delhi, then Mumbai in Marathi): every city marked ready has a complete First Week pack
and its own roleplays, every pack in a city's other languages (LANGUAGE_PACKS) is just as complete,
the server's scene allowlist (backend/legacy/ai.py) carries exactly the same scenes, the catalogue agrees, and the AI prompt names the
learner's city. The content is read by running frontend/content.js itself (JavaScriptCore via osascript), not by parsing it."""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import pytest

from backend import main
from backend.legacy import ai as legacy_ai

ROOT = Path(__file__).resolve().parent.parent
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
KANNADA = re.compile(r"[ಀ-೿]")
TAMIL = re.compile(r"[\u0B80-\u0BFF]")
FRENCH = re.compile(r"[A-Za-zÀ-ÿ]")
BENGALI = re.compile(r"[\u0980-\u09FF]")
TELUGU = re.compile(r"[\u0C00-\u0C7F]")
URDU = re.compile(r"[\u0600-\u06FF]")
SCRIPTS = {"bengaluru": KANNADA, "chennai": TAMIL, "puducherry": TAMIL, "puducherry:fr": FRENCH, "kolkata": BENGALI, "hyderabad": TELUGU, "hyderabad:ur": URDU, "jk": URDU, "jk:doi": DEVANAGARI, "jk:ur": URDU}                                         # the script a city's `hi` field is written in; Devanagari elsewhere


def script(city):
    """The script of a pack's or a city's phrases ("mumbai:mr" is Mumbai's): Kannada in Bengaluru, Tamil in Chennai, Devanagari in Delhi and Mumbai."""
    return SCRIPTS.get(city) or SCRIPTS.get(city.split(":")[0], DEVANAGARI)


def _content():
    expr = ("var G = this; G.window = G; eval($.NSString.stringWithContentsOfFileEncodingError('" + str(ROOT / "frontend" / "content.js") + "', 4, null).js);"
            " JSON.stringify({cities: CITIES, categories: CATEGORIES, packs: PACKS, scenarios: SCENARIOS, languages: LANGUAGES,"
            " language_packs: typeof LANGUAGE_PACKS === 'undefined' ? {} : LANGUAGE_PACKS, review: typeof CONTENT_REVIEW === 'undefined' ? {} : CONTENT_REVIEW,"
            " local: typeof LOCAL_CONTENT === 'undefined' ? {} : LOCAL_CONTENT, delhi_tutor: TUTOR_INTENTS.map(function (it) { return it.m; }),"
            " built: typeof LOCAL_CONTENT === 'undefined' ? {} : Object.fromEntries(Object.entries(LOCAL_CONTENT).map(function (c) { return [c[0], Object.fromEntries("
            "   Object.entries(c[1]).map(function (l) { return [l[0], l[1].tutor.intents.filter(function (it) { return it.build; })"
            "   .map(function (it) { return [it.build(l[1].tutor.defaultPlace), it.build(l[1].tutor.places[1]), it.build('Somewhere')]; })]; }))]; }))})")
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", expr], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


C = _content()
READY = [c["id"] for c in C["cities"] if c["ready"]]
MUMBAI_SCENES = [d["scenario"] for d in C["packs"]["mumbai"]]
MARATHI_SCENES = [d["scenario"] for d in C["language_packs"].get("mumbai", {}).get("mr", [])]
# every First Week pack: a ready city's own, and each one in another of its languages
PACKS = {city: C["packs"][city] for city in READY} | {f"{city}:{lang}": pack for city, by in C["language_packs"].items() for lang, pack in by.items()}
DELHI_ONLY = ("Connaught", "Sarojini", "Kamla Nagar", "Laxmi Nagar", "Delhi University", "Dilli", "Kashmere", "Rajiv Chowk")


def first_match(scene, text):
    """The rule the offline roleplay engine (frontend/engine.js roleplayReply) picks first for `text`, or None (the fallback)."""
    t = " " + "".join(ch for ch in unicodedata.normalize("NFD", text.lower()) if not "\u0300" <= ch <= "\u036f") + " "   # accents ignored, as the engine does
    return next((i for i, rule in enumerate(scene["rules"]) if any(k in t for k in rule["m"])), None)


def test_the_ready_cities():
    assert READY == ["delhi", "mumbai", "bengaluru", "hyderabad", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "bhopal", "jk", "shimla"]


@pytest.mark.parametrize("city", PACKS)
def test_a_ready_city_has_a_complete_first_week(city):
    pack = PACKS[city]
    assert [d["day"] for d in pack] == list(range(1, 8))
    assert [d["key"] for d in pack] == [c["key"] for c in C["categories"]]          # one day per everyday situation, in the usual order
    for d in pack:
        assert d["title"] and d["desc"] and d["situation"] and d["tip"] and d["icon"]
        assert 4 <= len(d["phrases"]) <= 6
        for p in d["phrases"]:
            assert script(city).search(p["hi"]) and p["roman"] and p["en"] and p["natural"], p
        assert len({p["roman"] for p in d["phrases"]}) == len(d["phrases"])           # no repeated phrase within a day


@pytest.mark.parametrize("city", PACKS)
def test_each_day_has_its_own_roleplay_for_that_situation(city):
    pack = PACKS[city]
    scenes = [d["scenario"] for d in pack]
    assert len(set(scenes)) == 7
    for d in pack:
        sc = C["scenarios"][d["scenario"]]
        assert sc["category"] == d["key"], d["scenario"]


def test_mumbai_uses_its_own_roleplays_not_delhis():
    delhi = {d["scenario"] for d in C["packs"]["delhi"]}
    assert not delhi & set(MUMBAI_SCENES) and all(s.startswith("mum_") for s in MUMBAI_SCENES)
    text = json.dumps([C["packs"]["mumbai"], [C["scenarios"][s] for s in MUMBAI_SCENES]], ensure_ascii=False)
    for delhi_only in DELHI_ONLY:
        assert delhi_only not in text, delhi_only


def test_mumbai_can_be_learnt_in_marathi():
    """Marathi is a language of its own (not a way of showing the Hindi pack): in the catalogue, offered for Mumbai, with its own pack."""
    assert {"code": "mr", "name": "Marathi", "native": "मराठी", "tts": "mr-IN"} in C["languages"]
    mumbai = next(c for c in C["cities"] if c["id"] == "mumbai")
    assert mumbai["langs"] == ["hi", "mr", "en"] and list(C["language_packs"]) == ["mumbai", "puducherry", "hyderabad", "jk"] and list(C["language_packs"]["mumbai"]) == ["mr"]


def test_a_language_pack_is_only_for_a_ready_city_and_one_of_its_languages():
    langs = {c["id"]: c for c in C["cities"]}
    for city, by in C["language_packs"].items():
        assert langs[city]["ready"] is True, city
        for lang in by:
            assert lang in langs[city]["langs"] and lang in {l["code"] for l in C["languages"]}, (city, lang)


def test_the_marathi_pack_is_marathi_not_the_hindi_pack_again():
    hindi = {p["hi"] for d in C["packs"]["mumbai"] for p in d["phrases"]} | {p["roman"] for d in C["packs"]["mumbai"] for p in d["phrases"]}
    marathi = [p for d in PACKS["mumbai:mr"] for p in d["phrases"]]
    same = [p["roman"] for p in marathi if p["hi"] in hindi or p["roman"] in hindi]
    assert same == ["Kasa kay?", "Ekdum jhakaas!"]                                   # the two Marathi phrases the Hindi pack already borrows
    words = " ".join(p["roman"].lower() for p in marathi)
    for marker in ("aahe", "kuthe", "kiti", "dya", "mala"):                          # everyday Marathi, all through the pack
        assert marker in words, marker
    for hindi_only in (" hai", " kahan", " kitna", " dena", " mujhe"):
        assert hindi_only not in " " + words, hindi_only


def test_the_marathi_pack_has_its_own_roleplays():
    assert len(MARATHI_SCENES) == 7 and all(s.startswith("mum_mr_") for s in MARATHI_SCENES)
    assert not set(MARATHI_SCENES) & set(MUMBAI_SCENES)
    text = json.dumps([PACKS["mumbai:mr"], [C["scenarios"][s] for s in MARATHI_SCENES]], ensure_ascii=False)
    for delhi_only in DELHI_ONLY:
        assert delhi_only not in text, delhi_only


@pytest.mark.parametrize("sid", MUMBAI_SCENES + MARATHI_SCENES)
def test_a_mumbai_roleplay_is_complete(sid):
    sc = C["scenarios"][sid]
    for field in ("icon", "title", "partner", "role", "place", "goal"):
        assert sc[field], field
    assert sc["opening"]["text"] and sc["opening"]["en"] and len(sc["start"]) >= 2
    assert len(sc["rules"]) >= 6 and sc["fallback"]["text"] and sc["fallback"]["en"] and sc["fallback"]["s"]
    for rule in sc["rules"]:
        assert rule["m"] and all(k == k.lower() and k.strip() for k in rule["m"]), rule["m"]
        assert rule["text"] and rule["en"] and rule["s"]
        assert ("{place}" in rule["text"]) <= ("places" in sc)                       # a reply naming a place needs this scene's own places
    assert sum(1 for rule in sc["rules"] if rule.get("end")) >= 1                    # every conversation can come to a natural end


@pytest.mark.parametrize("sid", MUMBAI_SCENES + MARATHI_SCENES)
def test_every_suggested_reply_gets_a_real_answer(sid):
    """The learner can always tap a suggestion: each one (the opening ones and every reply's) leads to a rule, never to the "didn't get that"."""
    sc = C["scenarios"][sid]
    suggestions = set(sc["start"]) | set(sc["fallback"]["s"]) | {s for rule in sc["rules"] for s in rule["s"]}
    missed = [s for s in suggestions if first_match(sc, s) is None]
    assert missed == []


@pytest.mark.parametrize("text,expected", [("Churchgate jaana hai.", "{place}? Haan, chalo."), ("Bhaiya, Churchgate chaloge?", "{place}? Haan, chalo."),
                                           ("Bhaiya, meter se chaloge?", "Haan haan, meter se hi chalega."), ("Kitna lagega?", "Meter se jitna aaye"),
                                           ("Yahin rok do.", "Lo, aa gaye!")])
def test_the_mumbai_taxi_answers_what_was_asked(text, expected):
    sc = C["scenarios"]["mum_taxi"]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


@pytest.mark.parametrize("text,expected", [("Churchgatela jaaycha aahe.", "{place}? Ho, chala."), ("Dada, Churchgatela yenar ka?", "{place}? Ho, chala."),
                                           ("Dada, meterne yenar ka?", "Ho ho, meternech"), ("Kiti hotil?", "Meter je dakhvel te"),
                                           ("Kiti vel lagel?", "Ya veli traffic aahe"), ("Ithech thaamba.", "He ghya, aalo!")])
def test_the_marathi_taxi_answers_what_was_asked(text, expected):
    sc = C["scenarios"]["mum_mr_taxi"]
    assert sc["rules"][first_match(sc, text)]["text"].startswith(expected)


def test_the_server_allowlist_has_exactly_the_frontends_scenes():
    """The server only lets allowlisted scene text reach the model (Phase 14A): each scene must be there, word for word."""
    assert set(legacy_ai.SCENARIOS) == set(C["scenarios"])
    for sid, scene in legacy_ai.SCENARIOS.items():
        front = C["scenarios"][sid]
        assert scene == {k: front[k] for k in ("partner", "role", "place", "goal")}, sid


class Model:
    def __init__(self):
        self.calls = []

    async def __call__(self, system, messages):
        self.calls.append(system)
        return json.dumps({"reply": "Haan bolo!"})


@pytest.mark.parametrize("city,scenario,partner", [("Mumbai", "mum_taxi", "Sharma ji"), ("Delhi", "auto", "Raju bhaiya")])
def test_the_roleplay_prompt_names_the_learners_city(client, monkeypatch, city, scenario, partner):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": city, "language": "Hindi", "level": "A1", "scenario": scenario, "history": [{"role": "me", "text": "Namaste"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 200 and r.json()["ok"] is True
    (system,) = model.calls
    assert f"a real {city} " in system and partner in system and city in system
    assert ("Delhi" in system) == (city == "Delhi")


@pytest.mark.parametrize("language,style", [("Marathi", "romanised Marathi"), ("Hindi (Hinglish)", "romanised Hinglish")])
def test_a_marathi_roleplay_is_asked_for_in_marathi(client, monkeypatch, language, style):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Mumbai", "language": language, "level": "A1", "scenario": "mum_mr_taxi", "history": [{"role": "me", "text": "Namaskar"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert f"learn {language} " in system and style in system and "Shinde kaka" in system and "a real Mumbai Taxi driver" in system
    assert ("Hinglish" in system) == (language != "Marathi")


def test_a_language_the_endpoint_does_not_know_is_still_refused(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Mumbai", "language": "Klingon", "level": "A1", "scenario": "mum_mr_taxi", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


def test_a_city_that_does_not_offer_marathi_is_not_asked_for_in_marathi(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Delhi", "language": "Marathi", "level": "A1", "scenario": "auto", "history": [{"role": "me", "text": "hi"}]}
    r = client.post("/api/ai", json=body)
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["body", "language"]


VALID_PAIRS = [("delhi", "hi"), ("delhi", "hinglish"), ("delhi", "en"), ("mumbai", "hi"), ("mumbai", "mr"), ("mumbai", "en")]
INVALID_PAIRS = [("delhi", "mr"), ("mumbai", "hinglish"), ("bengaluru", "hi"), ("chennai", "mr"), ("delhi", "kn"), ("mumbai", "kn"), ("bengaluru", "mr")]


def test_the_pairs_are_the_catalogues(client):
    offered = {c["slug"]: c["languages"] for c in client.get("/api/cities").json()["cities"]}
    assert [(c, l) for c in ("delhi", "mumbai") for l in offered[c]] == VALID_PAIRS
    assert all(l not in offered[c] for c, l in INVALID_PAIRS)


@pytest.mark.parametrize("city,lang", VALID_PAIRS)
def test_a_saved_state_keeps_a_city_and_a_language_it_offers(client, city, lang):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'{city}-{lang}@example.com')['handle']}"
    assert client.put(url, json={"v": 1, "city": city, "language": lang}).json() == {"ok": True}
    assert client.get(url).json()["state"] == {"v": 1, "city": city, "language": lang}


@pytest.mark.parametrize("city,lang", INVALID_PAIRS)
def test_a_saved_state_refuses_a_language_its_city_does_not_offer(client, city, lang):
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, f'{city}-{lang}@example.com')['handle']}"
    assert client.put(url, json={"v": 1, "city": "delhi", "language": "hi", "xp": 7}).status_code == 200
    r = client.put(url, json={"v": 1, "city": city, "language": lang, "xp": 99})
    assert r.status_code == 422 and r.json()["detail"] == [{"loc": ["body", "language"], "msg": "language is not offered for this city", "type": "value_error"}]
    assert client.get(url).json()["state"] == {"v": 1, "city": "delhi", "language": "hi", "xp": 7}      # nothing of the refused write was kept


def test_a_partial_state_without_both_fields_is_still_accepted(client):
    """The frontend may write part of its state (Phase 14A); the pair is checked only when both are there."""
    from .test_legacy_hardening import register
    url = f"/api/state/{register(client, 'partial@example.com')['handle']}"
    assert client.put(url, json={"v": 1, "language": "mr"}).status_code == 200
    assert client.put(url, json={"v": 1, "city": "delhi"}).status_code == 200


def test_a_city_the_catalogue_does_not_know_is_still_refused(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "roleplay", "city": "Atlantis", "language": "Hindi", "level": "A1", "scenario": "mum_taxi", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422


def test_the_catalogue_marks_mumbai_ready(client):
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["mumbai"]["ready"] is True and [s for s, c in cities.items() if c["ready"]] == READY


def test_the_catalogue_offers_mumbai_in_marathi(client):
    """Migration 0030: the catalogue's languages and Mumbai's language list agree with the frontend's, in order."""
    cities = {c["slug"]: c for c in client.get("/api/cities").json()["cities"]}
    assert cities["mumbai"]["languages"] == next(c["langs"] for c in C["cities"] if c["id"] == "mumbai") == ["hi", "mr", "en"]
    assert cities["delhi"]["languages"] == ["hi", "hinglish", "en"]                   # no other city changes
    assert {"code": "mr", "name": "Marathi", "native_name": "मराठी", "tts_locale": "mr-IN"} in client.get("/api/languages").json()["languages"]


# =====================================================================================================================
# Mumbai beyond the First Week pack: the tutor, readings, the level check, achievements (content.js LOCAL_CONTENT)
# =====================================================================================================================
LOCAL = C["local"]
LOCAL_CASES = [(city, lang) for city, by in LOCAL.items() for lang in by]
TOPICS = {c["key"] for c in C["categories"]}
HINDI_MARKERS = (" hai", " hain", "kya ", "kahan", "mujhe", "chahiye", "kitna", "kitne", " mein ", "dijiye", "bhaiya")


def test_every_new_city_has_local_content_in_its_taught_languages():
    assert LOCAL_CASES == [("mumbai", "hi"), ("mumbai", "mr"), ("bengaluru", "kn"), ("chennai", "ta"), ("puducherry", "ta"), ("puducherry", "fr"),
                           ("jaipur", "hi"), ("lucknow", "hi"), ("kolkata", "bn"),
                           ("hyderabad", "te"), ("hyderabad", "ur"), ("bhopal", "hi"), ("shimla", "hi"),
                           ("jk", "ks"), ("jk", "doi"), ("jk", "ur")]  # the English view uses the city's own entry


@pytest.mark.parametrize("city,lang", LOCAL_CASES)
def test_the_local_tutor_is_complete(city, lang):
    tutor = LOCAL[city][lang]["tutor"]
    assert tutor["greet"] and tutor["defaultPlace"] in tutor["places"] and len(tutor["starters"]) == 5 and tutor["glossary"]
    topics = [it["topic"] for it in tutor["intents"]]
    assert set(topics) == TOPICS                                                       # an answer for every everyday situation
    assert len(tutor["intents"]) == len(C["delhi_tutor"])                              # as many answers as the shared tutor has
    for it in tutor["intents"]:
        assert it["m"] and all(k == k.lower() and k.strip() for k in it["m"]) and it["topic"] in TOPICS
    # each answer is either a fixed one (its phrases are data) or names a destination (a build function, absent from the JSON)
    fixed = [it for it in tutor["intents"] if it.get("phrases")]
    assert len(fixed) + len(C["built"][city][lang]) == len(tutor["intents"]) and len(C["built"][city][lang]) == 1
    for p in [p for it in tutor["intents"] for p in it.get("phrases", [])] + tutor["generic"]["phrases"]:
        assert script(f"{city}:{lang}").search(p["hi"]) and p["roman"] and p["en"], p
    for built in C["built"][city][lang]:                                               # built for the default place, the next one and an unknown one
        known, known2, unknown = built
        assert all(script(f"{city}:{lang}").search(p["hi"]) for p in known["phrases"]) and all(script(f"{city}:{lang}").search(p["hi"]) for p in known2["phrases"][:2])
        assert tutor["defaultPlace"] in known["phrases"][0]["en"] and "Somewhere" in unknown["phrases"][0]["roman"] and known["note"]
    starters = tutor["starters"]
    meaning = [q for q in starters if q.startswith("What does")]
    assert meaning and all(q.split("'")[1] in tutor["glossary"] for q in meaning)       # the starter's word is in this glossary


@pytest.mark.parametrize("city,lang", LOCAL_CASES)
def test_the_local_readings_and_level_check_are_complete(city, lang):
    entry = LOCAL[city][lang]
    assert len(entry["readings"]) >= 2 and len(entry["placement"]) == 5
    for r in entry["readings"]:
        assert r["title"] and r["level"] == "A1" and len(r["lines"]) >= 4 and len(r["questions"]) >= 2
        assert all(script(f"{city}:{lang}").search(l["hi"]) and l["roman"] and l["en"] for l in r["lines"])
        assert all(0 <= q["a"] < len(q["options"]) for q in r["questions"])
    assert all(0 <= q["a"] < len(q["options"]) == 4 for q in entry["placement"])
    assert set(entry["achievements"]) <= {"first-words", "auto-pro", "foodie", "first-chat", "bargainer", "local"}
    assert all(len(v) == 3 and all(v) for v in entry["achievements"].values())


@pytest.mark.parametrize("city,lang", LOCAL_CASES)
def test_mumbai_local_content_has_no_delhi_in_it(city, lang):
    text = json.dumps([LOCAL[city][lang], C["built"][city][lang]], ensure_ascii=False)
    for delhi_only in DELHI_ONLY + ("Huda City", "Chandni Chowk", "chhole", "India Gate", "Sarojini", "very Delhi"):
        assert delhi_only not in text, delhi_only


def test_the_marathi_local_content_is_marathi():
    entry = LOCAL["mumbai"]["mr"]
    phrases = [p for it in entry["tutor"]["intents"] for p in it.get("phrases", [])] + entry["tutor"]["generic"]["phrases"]
    phrases += [p for b in C["built"]["mumbai"]["mr"] for p in b[0]["phrases"]] + [l for r in entry["readings"] for l in r["lines"]]
    assert not [p["hi"] for p in phrases if "।" in p["hi"]]                              # Marathi ends a sentence with ".", not the Hindi danda
    romans = " " + " ".join(p["roman"].lower() for p in phrases) + " "
    assert [m for m in HINDI_MARKERS if m in romans] == []
    assert entry["tutor"]["glossaryOnly"] is True and "jugaad" not in entry["tutor"]["glossary"]
    assert entry["tutor"]["polite"]["rules"] and entry["achievements"]["first-words"][2] == "Said your first Marathi phrase"


# =====================================================================================================================
# content review status and feminine forms
# =====================================================================================================================
def test_mumbai_content_is_marked_as_awaiting_native_review():
    """Nobody fluent has reviewed it yet: an AI-assisted editorial pass is recorded as just that, the native review as pending, and
    docs/CONTENT_REVIEW.md agrees (no false claim of validation)."""
    assert {city: list(by) for city, by in C["review"].items()} == {"mumbai": ["hi", "mr"], "bengaluru": ["kn"], "chennai": ["ta"], "puducherry": ["ta", "fr"], "jaipur": ["hi"], "lucknow": ["hi"], "kolkata": ["bn"], "hyderabad": ["te", "ur"], "bhopal": ["hi"], "shimla": ["hi"], "jk": ["ks", "doi", "ur"]}
    for city, lang in (("mumbai", "hi"), ("mumbai", "mr"), ("bengaluru", "kn"), ("chennai", "ta"), ("puducherry", "ta"), ("puducherry", "fr"), ("jaipur", "hi"), ("lucknow", "hi"), ("kolkata", "bn"), ("hyderabad", "te"), ("hyderabad", "ur"), ("bhopal", "hi"), ("shimla", "hi"), ("jk", "ks"), ("jk", "doi"), ("jk", "ur")):
        r = C["review"][city][lang]
        assert (r["editorial_status"], r["native_review_status"]) == ("ai_assisted_review", "pending") and r["note"] and r["known_limitations"]
        assert "status" not in r                                                     # the old single field is gone: one vocabulary everywhere
    doc = (ROOT / "docs" / "CONTENT_REVIEW.md").read_text()
    assert "**Status: AI-assisted editorial review done; native-speaker review pending.**" in doc and "approved" in doc


@pytest.mark.parametrize("city", ["mumbai", "mumbai:mr", "bengaluru", "puducherry:fr"])
def test_a_gendered_phrase_shows_the_feminine_form(city):
    fem = [p for d in PACKS[city] for p in d["phrases"] if "fem" in p]
    assert fem, city
    for p in fem:
        assert script(city).search(p["fem"]["hi"]) and p["fem"]["roman"] and p["fem"]["hi"] != p["hi"] and p["fem"]["roman"] != p["roman"]
    assert any({"mumbai": "nayi aayi", "mumbai:mr": "aale aahe", "bengaluru": "hosabalu", "puducherry:fr": "nouvelle"}[city] in p["fem"]["roman"] for p in fem)


@pytest.mark.parametrize("sid", MUMBAI_SCENES + MARATHI_SCENES)
def test_mumbai_characters_do_not_assume_the_learner_is_male(sid):
    sc = C["scenarios"][sid]
    lines = [sc["opening"]["text"], sc["fallback"]["text"]] + [r["text"] for r in sc["rules"]]
    suggestions = list(sc["start"]) + list(sc["fallback"]["s"]) + [x for r in sc["rules"] for x in r["s"]]
    said_to_learner = " " + " ".join(lines).lower() + " "
    for masc in (" saheb", "arre bhai", "naye aaye", "rahe ho", "shodhtoys", "aap naye", "tum naye", "ban jayega", "nahi bhaiya"):
        assert masc not in said_to_learner, (sid, masc)
    said_by_learner = " " + " ".join(suggestions).lower() + " "
    for masc in ("naya hoon", "aaya hoon", "aalo aahe", "doonga", "loonga", "de raha", "samajh gaya", "deto.", "gheto.", "samajla."):
        assert masc not in said_by_learner, (sid, masc)


@pytest.mark.parametrize("language,style", [("Marathi", "romanised Marathi"), ("Hindi (Hinglish)", "romanised Hinglish")])
def test_the_tutor_is_asked_for_in_the_learners_language(client, monkeypatch, language, style):
    model = Model()
    monkeypatch.setattr(main, "provider", lambda: "groq")
    monkeypatch.setattr(main, "call_llm", model)
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "tutor", "city": "Mumbai", "language": language, "level": "A1", "history": [{"role": "me", "text": "How do I order a vada pav?"}]}
    assert client.post("/api/ai", json=body).status_code == 200
    (system,) = model.calls
    assert f"learn {language} " in system and f'"roman": str ({style})' in system
    if language != "Marathi":
        assert main.TUTOR in system                                                  # the Hindi tutor prompt is exactly as before


def test_the_tutor_is_not_asked_for_in_marathi_for_delhi(client, monkeypatch):
    monkeypatch.setenv("DEMO_LIVE_AI", "1")
    body = {"mode": "tutor", "city": "Delhi", "language": "Marathi", "level": "A1", "history": [{"role": "me", "text": "hi"}]}
    assert client.post("/api/ai", json=body).status_code == 422
