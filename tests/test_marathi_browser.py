"""Mumbai in Marathi, in a real browser (headless Google Chrome, tests/cdp.py): "I'm New Here" offers Hindi, Marathi and English for Mumbai,
picking Marathi builds the Marathi First Week pack, and its lessons, fair-price advice and roleplays are in Marathi. The content itself is
checked in tests/test_city_packs.py and the running app without a browser in tests/frontend/legacy_harness.js (mumbai_in_marathi_works)."""
import json
import time

import pytest

from .cdp import chrome_path
from .test_mobile_layout import browser, site, tap, visit  # noqa: F401  (browser, site: fixtures)

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")

LANGS = "[...document.querySelectorAll('.lang')].map(c => c.innerText.replace(/\\s+/g, ' ').trim())"


def build_marathi(browser, site, width):
    visit(browser, site, "adult", "#/new", width)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    browser.evaluate("A.pickLang('mr')")
    time.sleep(0.3)
    browser.evaluate("A.build()")
    assert browser.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Mumbai'", 10)


@pytest.mark.parametrize("width", (375, 1366))
def test_mumbai_offers_hindi_marathi_and_english(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Hindi", "Marathi", "English"]
    assert "मराठी Marathi · The city's own language" in langs[1] and browser.evaluate("document.querySelectorAll('.lang')[1].querySelector('.native.deva') !== null")
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")
    tap(browser, "[onclick=\"A.pickCity('delhi')\"]")                                                # Delhi is unchanged
    time.sleep(0.3)
    assert [l.split(" · ")[0].split(" ")[-1] for l in browser.evaluate(LANGS)] == ["Hindi", "Hinglish", "English"]


def test_picking_marathi_builds_the_marathi_pack(site, browser):
    build_marathi(browser, site, 1366)
    text = browser.evaluate("document.querySelector('#app').innerText")
    assert "settle into your building, in Marathi" in text and "Bargain politely at a Marathi market" in text      # the Marathi pack's days
    assert browser.evaluate("Engine.state.language") == "mr" and browser.evaluate("Engine.speechLang()") == "mr-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('मीटरने येणार का?')")
    assert "मीटर से चलोगे" not in browser.evaluate("document.querySelector('#app').innerText")


@pytest.mark.parametrize("item,quote,phrase", [("jacket", "2000", "Khup mahaag aahe, dada."), ("taxi", "999", "Dada, meterne chala."),
                                               ("local", "5", "Churchgatecha ek tikit dya.")])
def test_fair_price_advice_is_in_marathi(site, browser, item, quote, phrase):
    build_marathi(browser, site, 1366)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({phrase!r})")


def test_a_marathi_roleplay_answers_in_marathi(site, browser):
    build_marathi(browser, site, 1366)
    browser.evaluate("location.hash = '#/roleplay/mum_mr_taxi'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Shinde kaka')")
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith("Type in Marathi (or English)")
    browser.evaluate("A.rpSend('Dada, meterne yenar ka?')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Ho ho, meternech jaaycha. Basa!')", 8)


def test_switching_city_drops_a_language_the_new_city_does_not_offer(site, browser):
    """Picking Mumbai and Marathi, then changing your mind to Delhi, must not build Delhi "in Marathi" (Delhi offers Hindi, Hinglish and
    English): the language choice is cleared, so Build asks for a language again, and nothing of Marathi reaches Delhi."""
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    browser.evaluate("A.pickLang('mr')")
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('delhi')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 0
    saved = browser.evaluate("JSON.stringify([Engine.state.city, Engine.state.language])")
    browser.evaluate("A.build()")
    time.sleep(0.6)
    assert browser.evaluate("location.hash") == "#/new"                                              # nothing was built
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Hindi, Hinglish or English."
    assert browser.evaluate("JSON.stringify([Engine.state.city, Engine.state.language])") == saved   # and nothing was saved
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")                                               # Mumbai's own languages are asked for
    time.sleep(0.3)
    browser.evaluate("A.build()")
    time.sleep(0.4)
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Hindi, Marathi or English."
    browser.evaluate("A.pickLang('hi')")                                                            # a language both offer is kept
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('delhi')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 1


@pytest.mark.parametrize("city,lang,expect", [("delhi", "mr", "hi"), ("mumbai", "hinglish", "hi"), ("mumbai", "mr", "mr"), ("delhi", "hinglish", "hinglish")])
def test_a_saved_combination_the_city_does_not_offer_falls_back_to_its_first_language(site, browser, city, lang, expect):
    """A saved state from before (or edited by hand) can hold a city and a language that do not go together: the app then uses the city's
    first language, so Marathi never reaches Delhi and Mumbai never gets a Hinglish mode it was not written for."""
    visit(browser, site, "adult", "#/", 1366)
    browser.evaluate(f"Engine.state.city = '{city}'; Engine.state.language = '{lang}'")              # as loaded, before anything is saved
    assert browser.evaluate("Engine.language()") == expect
    assert browser.evaluate("Engine.speechLang()") == ("mr-IN" if expect == "mr" else "hi-IN")
    marathi_pack = browser.evaluate("Engine.pack() === LANGUAGE_PACKS.mumbai.mr")
    assert marathi_pack == (city == "mumbai" and expect == "mr")
    browser.evaluate("location.hash = '#/roleplay/' + Engine.pack()[1].scenario")
    assert browser.wait_for("!!document.querySelector('#rp-input')")
    hint = browser.evaluate("document.querySelector('#rp-input').placeholder")
    assert hint.startswith("Type in Marathi") == (expect == "mr")


@pytest.mark.parametrize("city,lang,expect", [("delhi", "mr", "hi"), ("mumbai", "hinglish", "hi")])
def test_saving_repairs_a_combination_the_city_does_not_offer(site, browser, city, lang, expect):
    """The next save keeps only a language the city offers (the server refuses any other), so the learner's progress keeps saving."""
    visit(browser, site, "adult", "#/", 1366)
    browser.evaluate(f"Engine.state.city = '{city}'; Engine.state.language = '{lang}'; Engine.save()")
    assert browser.evaluate("Engine.state.language") == expect
    time.sleep(1.2)                                                                                 # the save reaches the server
    state = browser.evaluate("fetch('/api/auth/me').then(r => r.json()).then(j => fetch('/api/state/' + j.user.handle)).then(r => r.json()).then(j => JSON.stringify([j.state.city, j.state.language]))")
    assert json.loads(state) == [city, expect]


@pytest.mark.parametrize("city,lang,title,marathi", [("delhi", "hi", "Delhi", False), ("delhi", "hinglish", "Delhi", False), ("delhi", "en", "Delhi", False),
                                                    ("mumbai", "hi", "Mumbai", False), ("mumbai", "mr", "Mumbai", True), ("mumbai", "en", "Mumbai", False)])
def test_every_language_a_city_offers_builds_its_pack(site, browser, city, lang, title, marathi):
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, f"[onclick=\"A.pickCity('{city}')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    browser.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    browser.evaluate("A.build()")
    assert browser.wait_for(f"location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in {title}'", 10)
    assert json.loads(browser.evaluate("JSON.stringify([Engine.state.city, Engine.state.language, Engine.language()])")) == [city, lang, lang]
    assert browser.evaluate("Engine.pack() === LANGUAGE_PACKS.mumbai.mr") is marathi
    assert browser.evaluate("Engine.speechLang()") == ("mr-IN" if marathi else "hi-IN")


def test_an_offered_language_cannot_be_forced_onto_another_city(site, browser):
    """Even a language code set by hand (the console) is checked against the chosen city before anything is built."""
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    saved = browser.evaluate("JSON.stringify([Engine.state.city, Engine.state.language])")
    browser.evaluate("A.pickLang('hinglish')")                                                      # Delhi's, not Mumbai's
    time.sleep(0.3)
    browser.evaluate("A.build()")
    time.sleep(0.6)
    assert browser.evaluate("location.hash") == "#/new"
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Hindi, Marathi or English."
    assert browser.evaluate("JSON.stringify([Engine.state.city, Engine.state.language])") == saved


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("city,lang,fem", [("mumbai", "hi", "Main yahan nayi aayi hoon"), ("mumbai", "mr", "Mi ithe navin aale aahe"), ("delhi", "hi", None)])
def test_mumbai_lessons_show_the_review_note_and_the_feminine_form(site, browser, width, city, lang, fem):
    """Mumbai's content says it awaits a native review, and a gendered phrase shows the feminine form; Delhi's lessons are unchanged."""
    visit(browser, site, "adult", "#/", width)
    browser.evaluate(f"Engine.state.city = '{city}'; Engine.state.language = '{lang}'; Engine.save(); location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app h1') && document.querySelector('#app h1').textContent.startsWith('Day 1')")
    text = browser.evaluate("document.querySelector('#app').innerText")
    if fem:
        assert "Early version" in text and "AI-assisted editorial review only, not yet checked by a native" in text
        assert "WOMEN SAY" in text.upper() and fem in text
        assert browser.evaluate("!!document.querySelector('.fem-note button')")
    else:
        assert "Early version" not in text and not browser.evaluate("!!document.querySelector('.fem-note')")
    browser.evaluate("location.hash = '#/pack'")
    assert browser.wait_for("document.querySelector('#app h1').textContent.startsWith('Your First Week')")
    assert ("Early version" in browser.evaluate("document.querySelector('#app').innerText")) is bool(fem)
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")
