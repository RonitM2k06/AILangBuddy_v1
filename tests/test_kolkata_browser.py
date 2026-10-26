"""Kolkata in a real browser (headless Google Chrome, tests/cdp.py) at phone (375, 390) and laptop (1366) widths: the card and preview,
Bengali and English offered, the Bengali pack in Bengali script, the Bengali voice used only if the device has one, practice that never
invents a score, roleplays, fair prices, the English view, and the server's Bengali pages for a learner whose profile targets Bengali. Voices
are a controlled list (tests/test_marathi_flows_browser.py VOICES)."""
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


def build(b, site, lang="bn", width=1366):
    visit(b, site, "adult", "#/new", width)
    tap(b, "[onclick=\"A.pickCity('kolkata')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === 2")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Kolkata'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_kolkata_offers_bengali_and_english_with_a_preview(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, "[onclick=\"A.pickCity('kolkata')\"]")
    assert "Kolkata" in card and "Also called Calcutta" in card and "Available" in card and "Native-speaker review pending" in card
    tap(browser, "[onclick=\"A.pickCity('kolkata')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert len(langs) == 2 and "বাংলা" in langs[0] and "Bengali" in langs[0] and "English" in langs[1]
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")
    assert "About Kolkata (Calcutta)" in preview and browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_bengali_pack(site, browser, width):
    build(browser, site, "bn", width)
    assert "not yet checked by a native Bengali speaker" in text(browser) and browser.evaluate("Engine.speechLang()") == "bn-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('মিটারে যাবেন তো?')", 10)
    page = text(browser)
    assert "Meter-e jaben to?" in page and "Kolkata · approx." in page and "Yellow taxi" in page and no_sideways_scroll(browser)


def test_the_english_view_teaches_the_same_bengali(site, browser):
    build(browser, site, "en")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('You\\'ll go by the meter, won\\'t you?')", 10)
    assert "মিটারে যাবেন তো?" in text(browser) and browser.evaluate("Engine.packLanguage()") == "bn"


def test_without_a_bengali_voice_nothing_is_played_and_with_one_bengali_is(site, browser):
    build(browser, site)
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN'])")                       # Hindi and Indian-English voices: neither may read Bengali
    browser.evaluate("document.querySelector('.phrase button').click()")
    assert browser.wait_for("document.querySelector('#toast').textContent.includes('no Bengali voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate(VOICES + "(['en-US', 'bn-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "bn-IN" and spoken[0]["text"] == "একটা এগ রোল দিন।"


def test_bengali_practice_never_invents_a_score(site, browser):
    build(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    assert "nothing was assessed" in text(browser, "[data-no-score]") and "%" not in text(browser, "[data-no-score]")


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("scene,partner,said,answer", [
    ("kol_taxi", "Bapi da", "Meter-e jaben to?", "Meter-e jabo, kintu kuri taka beshi lagbe"),
    ("kol_food", "Shibu da", "Ekta egg roll din.", "Garam garam egg roll!"),
])
def test_a_bengali_roleplay_runs(site, browser, width, scene, partner, said, answer):
    build(browser, site, "bn", width)
    browser.evaluate(f"location.hash = '#/roleplay/{scene}'")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(partner)})")
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith("Type in Bengali (or English)")
    browser.evaluate(f"A.rpSend({json.dumps(said)})")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(answer)})", 8)
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("item,quote,phrase", [("saree", "3000", "খুব বেশি দাম।"), ("cha", "15", "ঠিক আছে, দিন।"), ("metro", "40", "Metro fares are fixed")])
def test_fair_price_advice_is_in_bengali(site, browser, item, quote, phrase):
    build(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({json.dumps(phrase)})")


# ---------------------------------------------------------------------------------------------------------------------
# the server's Bengali pages (migration 0048), for a learner whose profile targets Bengali
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def bengali(site):
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "bengali@example.com", "password": PASSWORD, "display_name": "Bengali Learner"})
    body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": "bn", "cefr_level": "A1", "date_of_birth": "1996-01-01"}, token)
    assert body["profile"]["target_language"] == "bn"
    return token


def open_as(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("route,marker", [("#/lessons", "Numbers and Money"), ("#/situations", "Yellow taxi to Park Street"), ("#/listening", "Help and Health: which phrase?")])
def test_the_server_pages_show_bengali_content_and_say_how_it_was_reviewed(site, browser, bengali, width, route, marker):
    open_as(browser, site, bengali, route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    assert "Bengali content: AI-assisted editorial review only; not yet checked by a native speaker" in text(browser, "[data-content-review]")
    assert no_sideways_scroll(browser)


def test_bengali_voice_practice_accepts_bengali_script_or_roman_letters(site, browser, bengali):
    open_as(browser, site, bengali, "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    assert "Bengali script" in text(browser, "[data-typed-card]")
    phrase = browser.evaluate("document.querySelector('#voice-root .deva').textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(phrase)}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)
