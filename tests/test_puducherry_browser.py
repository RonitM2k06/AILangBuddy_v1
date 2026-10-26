"""Puducherry in a real browser (headless Google Chrome, tests/cdp.py) at phone (375, 390) and laptop (1366) widths: the card and preview,
Tamil, French and English offered, the Tamil and French packs, French with its accents and a pronunciation guide, the French voice used only if
the device has one, practice that never invents a score, accent-blind French roleplays, fair prices, switching city, and the server's French
pages for a learner whose profile targets French. Voices are a controlled list (tests/test_marathi_flows_browser.py VOICES)."""
import json
import time

import pytest

from .cdp import chrome_path
from .test_marathi_flows_browser import VOICES
from .test_mobile_layout import PASSWORD, browser, http, site, tap, visit  # noqa: F401  (browser, site: fixtures)

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")

LANGS = "[...document.querySelectorAll('.lang')].map(c => c.innerText.replace(/\\s+/g, ' ').trim())"
WIDTHS = (375, 390, 1366)


def text(b, sel="#app"):
    return b.evaluate(f"(document.querySelector({json.dumps(sel)}) || {{}}).innerText || ''")


def no_sideways_scroll(b):
    return b.evaluate("document.documentElement.scrollWidth <= innerWidth")


def build(b, site, lang, width=1366):
    visit(b, site, "adult", "#/new", width)
    tap(b, "[onclick=\"A.pickCity('puducherry')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === 3")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Puducherry'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_puducherry_offers_tamil_french_and_english_with_a_preview(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, "[onclick=\"A.pickCity('puducherry')\"]")
    assert "Puducherry" in card and "Also called Pondicherry" in card and "Available" in card and "Native-speaker review pending" in card
    tap(browser, "[onclick=\"A.pickCity('puducherry')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Tamil", "French", "English"]
    assert "Français French · The language of White Town" in langs[1]
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")
    assert "About Puducherry (Pondicherry)" in preview and browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_tamil_pack(site, browser, width):
    build(browser, site, "ta", width)
    assert "not yet checked by a native Tamil speaker" in text(browser) and browser.evaluate("Engine.speechLang()") == "ta-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('ஸ்கூட்டர் வாடகைக்கு கிடைக்குமா?')", 10)
    page = text(browser)
    assert "Scooter vaadagaikku kidaikkumaa?" in page and "Puducherry · approx." in page and "Scooter rental" in page and no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_french_pack_shows_accents_a_pronunciation_guide_and_the_feminine_form(site, browser, width):
    build(browser, site, "fr", width)
    assert "not yet checked by a native French speaker" in text(browser) and browser.evaluate("Engine.speechLang()") == "fr-FR"
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Le petit-déjeuner est à quelle heure ?')", 10)
    page = text(browser)
    assert "luh puh-TEE day-zhuh-NAY" in page and "Le petit-dejeuner est a quelle heure ?" not in page   # the guide, not the same text without accents
    assert "WOMEN SAY" in page.upper() and "Je suis nouvelle ici." in page and "noo-VEL" in page
    assert no_sideways_scroll(browser)


def test_without_a_french_voice_nothing_is_played_and_with_one_french_is(site, browser):
    build(browser, site, "fr")
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN', 'ta-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    assert browser.wait_for("document.querySelector('#toast').textContent.includes('no French voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate(VOICES + "(['en-US', 'fr-FR'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "fr-FR" and spoken[0]["text"] == "Un café et un croissant, s'il vous plaît."   # read as written, accents and all


def test_french_practice_never_invents_a_score(site, browser):
    build(browser, site, "fr")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    assert "nothing was assessed" in text(browser, "[data-no-score]") and "%" not in text(browser, "[data-no-score]")


@pytest.mark.parametrize("width", (375, 1366))
def test_a_french_roleplay_answers_with_or_without_accents(site, browser, width):
    build(browser, site, "fr", width)
    browser.evaluate("location.hash = '#/roleplay/pdy_fr_bike'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Monsieur Pierre')")
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith("Type in French (or English)")
    browser.evaluate("A.rpSend('Je voudrais louer un velo.')")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps("Bien sûr ! J'ai un très bon vélo")})", 8)
    browser.evaluate("A.rpSend('C’est combien pour la journée ?')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('cent cinquante roupies')", 8)
    assert no_sideways_scroll(browser)


def test_a_tamil_roleplay_runs(site, browser):
    build(browser, site, "ta", 390)
    browser.evaluate("location.hash = '#/roleplay/pdy_scooter'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Velu')")
    browser.evaluate("A.rpSend('Oru naalaikku evvalavu?')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Oru naalaikku naanooru rupaai')", 8)


@pytest.mark.parametrize("item,quote,phrase", [("scooter", "2000", "C'est trop cher."), ("coffee", "20", "D'accord, je le prends.")])
def test_fair_price_advice_is_in_french_for_a_french_learner(site, browser, item, quote, phrase):
    build(browser, site, "fr")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({json.dumps(phrase)})")


def test_switching_from_puducherry_french_to_chennai_drops_french(site, browser):
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, "[onclick=\"A.pickCity('puducherry')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    browser.evaluate("A.pickLang('fr')")
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('chennai')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 0
    browser.evaluate("A.build()")
    time.sleep(0.6)
    assert browser.evaluate("location.hash") == "#/new"
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Tamil or English."


def test_each_language_keeps_its_own_first_week_progress(site, browser):
    build(browser, site, "fr")
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    browser.evaluate("Engine.state.language = 'ta'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[]"
    browser.evaluate("Engine.state.language = 'fr'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]" and browser.evaluate("Engine.packKey()") == "puducherry:fr"


# ---------------------------------------------------------------------------------------------------------------------
# the server's French pages (migration 0044), for a learner whose profile targets French
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def french(site):
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "french@example.com", "password": PASSWORD, "display_name": "French Learner"})
    body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": "fr", "cefr_level": "A1", "date_of_birth": "1996-01-01"}, token)
    assert body["profile"]["target_language"] == "fr"
    return token


def open_as(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("route,marker", [("#/lessons", "Numbers and Money"), ("#/situations", "Rent a bicycle"), ("#/listening", "Help and Health: which phrase?")])
def test_the_server_pages_show_french_content_and_say_how_it_was_reviewed(site, browser, french, width, route, marker):
    open_as(browser, site, french, route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    assert "French content: AI-assisted editorial review only; not yet checked by a native speaker" in text(browser, "[data-content-review]")
    assert no_sideways_scroll(browser)


def test_french_voice_practice_accepts_a_phrase_typed_without_accents(site, browser, french):
    open_as(browser, site, french, "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    assert "accents are optional" in text(browser, "[data-typed-card]")
    phrase = browser.evaluate("document.querySelector('#voice-root .deva').textContent")
    plain = browser.evaluate(f"{json.dumps(phrase)}.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase()")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(plain)}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)


def test_french_listening_without_a_french_voice_is_a_labelled_transcript(site, browser, french):
    open_as(browser, site, french, "#/listening", 390)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'ta-IN'])")
    assert browser.wait_for("document.querySelectorAll('#listening-root a.card').length > 0", 10)
    browser.evaluate("location.hash = document.querySelector('#listening-root a.card').getAttribute('href')")
    assert browser.wait_for("!!document.querySelector('[data-play]')", 10)
    tap(browser, "[data-play]")
    assert browser.wait_for("!!document.querySelector('[data-transcript]')", 5)
    assert "no French voice" in text(browser, "[data-transcript]") and browser.evaluate("window.__spoken.length") == 0
