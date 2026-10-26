"""Bengaluru in Kannada, in a real browser (headless Google Chrome, tests/cdp.py), at phone (375, 390) and laptop (1366) widths: the
destination card and its preview, Kannada and English offered (no Hindi), the Kannada pack and its lessons with the review note and the
feminine form, fair-price advice in Kannada, a roleplay answered in Kannada, the Kannada voice used only if the device has one, practice that
never invents a score, and a language the new city does not offer dropped on the way. The browser's voices are replaced by a controlled list
(tests/test_marathi_flows_browser.py VOICES), so "no Kannada voice" and "a Kannada voice" are both tested; nothing is really played."""
import json
import time

import pytest

from .cdp import chrome_path
from .test_marathi_flows_browser import VOICES
from .test_mobile_layout import browser, site, tap, visit  # noqa: F401  (browser, site: fixtures)

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")

LANGS = "[...document.querySelectorAll('.lang')].map(c => c.innerText.replace(/\\s+/g, ' ').trim())"
WIDTHS = (375, 390, 1366)


def text(b, sel="#app"):
    return b.evaluate(f"(document.querySelector({json.dumps(sel)}) || {{}}).innerText || ''")


def no_sideways_scroll(b):
    return b.evaluate("document.documentElement.scrollWidth <= innerWidth")


def build_kannada(b, site, width=1366, lang="kn"):
    visit(b, site, "adult", "#/new", width)
    tap(b, "[onclick=\"A.pickCity('bengaluru')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === 2")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Bengaluru'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_bengaluru_is_offered_in_kannada_and_english_with_a_preview(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, "[onclick=\"A.pickCity('bengaluru')\"]")
    assert "Bengaluru" in card and "Also called Bangalore" in card and "Available" in card and "Native-speaker review pending" in card and "In Development" not in card
    tap(browser, "[onclick=\"A.pickCity('bengaluru')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Kannada", "English"]
    assert "ಕನ್ನಡ Kannada · The city's own language" in langs[0] and browser.evaluate("document.querySelectorAll('.lang')[0].querySelector('.native.deva') !== null")
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")     # (innerText is upper-cased by the eyebrow style)
    assert "About Bengaluru (Bangalore)" in preview and "Your first week" in preview and "Breakfast at a darshini" in preview
    assert browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")                                              # Mumbai has no preview card and is unchanged
    time.sleep(0.3)
    assert [l.split(" · ")[0].split(" ")[-1] for l in browser.evaluate(LANGS)] == ["Hindi", "Marathi", "English"]
    assert not browser.evaluate("!!document.querySelector('[data-city-preview]')")


def test_kannada_text_uses_a_kannada_font(site, browser):
    build_kannada(browser, site)
    family = browser.evaluate("getComputedStyle(document.querySelector('.loop-item .deva') || document.querySelector('.deva')).fontFamily")
    assert "Noto Sans Kannada" in family and "Noto Sans Devanagari" in family


@pytest.mark.parametrize("width", WIDTHS)
def test_the_kannada_pack_and_lessons(site, browser, width):
    build_kannada(browser, site, width)
    page = text(browser)
    assert "Early version" in page and "not yet checked by a native Kannada speaker" in page
    assert browser.evaluate("Engine.state.language") == "kn" and browser.evaluate("Engine.speechLang()") == "kn-IN"
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?')", 10)
    page = text(browser)
    assert "Namaskara, hegiddira?" in page and "WOMEN SAY" in page.upper() and "Naanu illi hosabalu." in page and "ನಾನು ಇಲ್ಲಿ ಹೊಸಬಳು." in page
    assert not any("ऀ" <= ch <= "ॿ" for ch in page.replace("कृपया पढ़िए", ""))
    assert no_sideways_scroll(browser)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('ಮೀಟರ್ ಹಾಕಿ.')", 10)
    assert "Namma Metro" in text(browser) and "Bengaluru · approx." in text(browser) and no_sideways_scroll(browser)


def test_the_english_view_shows_the_kannada_pack_english_first(site, browser):
    build_kannada(browser, site, lang="en")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Please use the meter.')", 10)
    assert "ಮೀಟರ್ ಹಾಕಿ." in text(browser) and browser.evaluate("Engine.speechLang()") == "kn-IN"


@pytest.mark.parametrize("item,quote,phrase", [("kurta", "2000", "Tumba jaasti aaytu. "), ("auto", "300", "Meter haaki."),
                                               ("metro", "40", "Majesticge ondu token kodi."), ("coffee", "20", "Sari, aaytu.")])
def test_fair_price_advice_is_in_kannada(site, browser, item, quote, phrase):
    build_kannada(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({phrase!r})")
    out = text(browser, "#pc-out")
    assert "भैया" not in out and "दादा" not in out


@pytest.mark.parametrize("width", (375, 1366))
def test_a_kannada_roleplay_answers_in_kannada(site, browser, width):
    build_kannada(browser, site, width)
    browser.evaluate("location.hash = '#/roleplay/blr_auto'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Manju')")
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith("Type in Kannada (or English)")
    browser.evaluate("A.rpSend('Meter haaki.')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Meter haaktini, aadre twenty rupees mele kodi.')", 8)
    browser.evaluate("A.rpSend('Beda, meter maatra.')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Sari sari, meter maatra. Kootkolli!')", 8)
    assert no_sideways_scroll(browser)


def test_without_a_kannada_voice_nothing_is_played_and_with_one_kannada_is(site, browser):
    build_kannada(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN'])")                        # Hindi and Indian-English voices: neither may read Kannada
    browser.evaluate("document.querySelector('.phrase button').click()")
    assert browser.wait_for("document.querySelector('#toast').textContent.includes('no Kannada voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'kn-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "kn-IN" and any("ಀ" <= ch <= "೿" for ch in spoken[0]["text"])


def test_practice_never_invents_a_kannada_score(site, browser):
    build_kannada(browser, site)
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    box = text(browser, "[data-no-score]")
    assert "nothing was assessed" in box and "%" not in box
    assert not browser.evaluate("!!document.querySelector('.phrase .feedback .score')")
    browser.evaluate("location.hash = '#/roleplay/blr_food'")                         # the roleplay's feedback card is honest too
    assert browser.wait_for("!!document.querySelector('#rp-input')")
    browser.evaluate("A.rpSend('Ondu masale dose kodi.')")
    assert browser.wait_for("document.querySelectorAll('.msg.me').length === 1", 5)
    browser.evaluate("A.rpFeedback()")
    assert browser.wait_for("!!document.querySelector('#rp-fb [data-no-score]')", 5)
    assert "%" not in text(browser, "#rp-fb")


def test_switching_from_mumbai_marathi_to_bengaluru_drops_marathi(site, browser):
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    browser.evaluate("A.pickLang('mr')")
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('bengaluru')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 0
    browser.evaluate("A.build()")
    time.sleep(0.6)
    assert browser.evaluate("location.hash") == "#/new"
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Kannada or English."
    browser.evaluate("A.pickLang('en')")                                              # a language both offer is kept on the way back
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 1


@pytest.mark.parametrize("lang", ["hi", "mr", "hinglish"])
def test_a_saved_language_bengaluru_does_not_offer_falls_back_to_kannada_and_is_repaired(site, browser, lang):
    visit(browser, site, "adult", "#/", 1366)
    browser.evaluate(f"Engine.state.city = 'bengaluru'; Engine.state.language = '{lang}'")
    assert browser.evaluate("Engine.language()") == "kn" and browser.evaluate("Engine.speechLang()") == "kn-IN"
    browser.evaluate("Engine.save()")
    assert browser.evaluate("Engine.state.language") == "kn"
    time.sleep(1.2)
    state = browser.evaluate("fetch('/api/auth/me').then(r => r.json()).then(j => fetch('/api/state/' + j.user.handle)).then(r => r.json()).then(j => JSON.stringify([j.state.city, j.state.language]))")
    assert json.loads(state) == ["bengaluru", "kn"]


def test_each_city_keeps_its_own_first_week_progress(site, browser):
    build_kannada(browser, site)
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    days = json.loads(browser.evaluate("JSON.stringify([Engine.daysDone(), Engine.state.packDays.bengaluru, Engine.packKey()])"))
    assert days == [[1], [1], "bengaluru"]
    xp = browser.evaluate("Engine.state.xp")
    browser.evaluate("A.completeDay(1)")                                              # completing it again: no second day award (+50 XP)
    time.sleep(0.9)
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]" and browser.evaluate("Engine.state.xp") - xp < 50
    browser.evaluate("Engine.state.city = 'mumbai'; Engine.state.language = 'mr'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[]"              # Mumbai's Marathi pack is not touched


def test_the_home_page_is_bengalurus(site, browser):
    build_kannada(browser, site, 390)
    browser.evaluate("location.hash = '#/'")
    assert browser.wait_for("document.querySelector('#app').textContent.includes('Right now in Bengaluru')", 10)
    assert browser.evaluate("!!document.querySelector('.now-card a[href^=\"#/roleplay/blr_\"]')")
    assert no_sideways_scroll(browser)


# ---------------------------------------------------------------------------------------------------------------------
# the server's Kannada pages (migration 0037), for a learner whose profile targets Kannada
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def kannada(site):
    from .test_mobile_layout import PASSWORD, http
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "kannada@example.com", "password": PASSWORD, "display_name": "Kannada Learner"})
    body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": "kn", "cefr_level": "A1", "date_of_birth": "1996-01-01"}, token)
    assert body["profile"]["target_language"] == "kn"
    return token


def open_as(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("route,marker", [("#/lessons", "Numbers and Money"), ("#/situations", "Auto to Indiranagar"), ("#/listening", "Help and Health: which phrase?")])
def test_the_server_pages_show_kannada_content_and_say_how_it_was_reviewed(site, browser, kannada, width, route, marker):
    open_as(browser, site, kannada, route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    note = text(browser, "[data-content-review]")
    assert "Kannada content: AI-assisted editorial review only; not yet checked by a native speaker" in note
    assert no_sideways_scroll(browser)


def test_kannada_listening_without_a_kannada_voice_is_a_labelled_transcript(site, browser, kannada):
    open_as(browser, site, kannada, "#/listening", 390)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'mr-IN'])")                  # Hindi and Marathi voices must not read Kannada
    assert browser.wait_for("document.querySelectorAll('#listening-root a.card').length > 0", 10)
    browser.evaluate("location.hash = document.querySelector('#listening-root a.card').getAttribute('href')")
    assert browser.wait_for("!!document.querySelector('[data-play]')", 10)
    tap(browser, "[data-play]")
    assert browser.wait_for("!!document.querySelector('[data-transcript]')", 5)
    t = text(browser, "[data-transcript]")
    assert "no Kannada voice" in t and any("ಀ" <= ch <= "೿" for ch in t)
    assert browser.evaluate("window.__spoken.length") == 0 and no_sideways_scroll(browser)


def test_kannada_voice_practice_is_a_typed_check_in_kannada_script(site, browser, kannada):
    open_as(browser, site, kannada, "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    card = text(browser, "[data-typed-card]")
    assert "Roman letters or Kannada script" in card and "does not hear you or score pronunciation" in card
    roman = browser.evaluate("document.querySelector('#voice-root .deva').nextElementSibling.textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(roman.lower().rstrip('?.!'))}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)


def test_a_server_roleplay_runs_in_kannada(site, browser, kannada):
    open_as(browser, site, kannada, "#/ai-roleplay")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Auto to Indiranagar')", 10)
    browser.evaluate("[...document.querySelectorAll('[data-start]')].find(b => b.closest('.card').innerText.includes('Auto to Indiranagar')).click()")
    assert browser.wait_for("location.hash.startsWith('#/ai-roleplay/') && !!document.querySelector('#rp-input')", 10)
    scene = text(browser)
    assert "Manju: Namaskara!" in scene and "Say this in Kannada" in scene and "Namaste" not in scene
