"""Chennai in Tamil, in a real browser (headless Google Chrome, tests/cdp.py), at phone (375, 390) and laptop (1366) widths: the
destination card and its preview, Tamil and English offered (no Hindi), the Tamil pack and its lessons with the review note, fair-price advice in Tamil, a roleplay answered in Tamil, the Tamil voice used only if the device has one, practice that
never invents a score, and a language the new city does not offer dropped on the way. The browser's voices are replaced by a controlled list
(tests/test_marathi_flows_browser.py VOICES), so "no Tamil voice" and "a Tamil voice" are both tested; nothing is really played."""
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


def build_tamil(b, site, width=1366, lang="ta"):
    visit(b, site, "adult", "#/new", width)
    tap(b, "[onclick=\"A.pickCity('chennai')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === 2")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Chennai'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_chennai_is_offered_in_tamil_and_english_with_a_preview(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, "[onclick=\"A.pickCity('chennai')\"]")
    assert "Chennai" in card and "Also called Madras" in card and "Available" in card and "Native-speaker review pending" in card and "In Development" not in card
    tap(browser, "[onclick=\"A.pickCity('chennai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Tamil", "English"]
    assert "தமிழ் Tamil · The city's own language" in langs[0] and browser.evaluate("document.querySelectorAll('.lang')[0].querySelector('.native.deva') !== null")
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")     # (innerText is upper-cased by the eyebrow style)
    assert "About Chennai (Madras)" in preview and "Your first week" in preview and "Breakfast at a tiffin centre" in preview
    assert browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")                                              # Mumbai has no preview card and is unchanged
    time.sleep(0.3)
    assert [l.split(" · ")[0].split(" ")[-1] for l in browser.evaluate(LANGS)] == ["Hindi", "Marathi", "English"]
    assert not browser.evaluate("!!document.querySelector('[data-city-preview]')")


def test_tamil_text_uses_a_tamil_font(site, browser):
    build_tamil(browser, site)
    family = browser.evaluate("getComputedStyle(document.querySelector('.loop-item .deva') || document.querySelector('.deva')).fontFamily")
    assert "Noto Sans Tamil" in family and "Noto Sans Devanagari" in family


@pytest.mark.parametrize("width", WIDTHS)
def test_the_tamil_pack_and_lessons(site, browser, width):
    build_tamil(browser, site, width)
    page = text(browser)
    assert "Early version" in page and "not yet checked by a native Tamil speaker" in page
    assert browser.evaluate("Engine.state.language") == "ta" and browser.evaluate("Engine.speechLang()") == "ta-IN"
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('வணக்கம், எப்படி இருக்கீங்க?')", 10)
    page = text(browser)
    assert "Vanakkam, eppadi irukeenga?" in page and "வணக்கம், எப்படி இருக்கீங்க?" in page and "WOMEN SAY" not in page.upper()   # nothing gendered to show
    assert not any("ऀ" <= ch <= "ॿ" for ch in page.replace("कृपया पढ़िए", ""))
    assert no_sideways_scroll(browser)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('மீட்டர் போடுங்க.')", 10)
    assert "Chennai Metro" in text(browser) and "Chennai · approx." in text(browser) and no_sideways_scroll(browser)


def test_the_english_view_shows_the_tamil_pack_english_first(site, browser):
    build_tamil(browser, site, lang="en")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Please use the meter.')", 10)
    assert "மீட்டர் போடுங்க." in text(browser) and browser.evaluate("Engine.speechLang()") == "ta-IN"


@pytest.mark.parametrize("item,quote,phrase", [("kurta", "2000", "Romba adhigam. 500 rupaaikku tharuveengalaa?"), ("auto", "300", "Romba adhigam. 120 rupaaikku"),
                                               ("metro", "40", "Airportukku oru ticket kudunga."), ("coffee", "20", "Sari, edukkaren.")])
def test_fair_price_advice_is_in_tamil(site, browser, item, quote, phrase):
    build_tamil(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({phrase!r})")
    out = text(browser, "#pc-out")
    assert "भैया" not in out and "दादा" not in out


@pytest.mark.parametrize("width", (375, 1366))
def test_a_tamil_roleplay_answers_in_tamil(site, browser, width):
    build_tamil(browser, site, width)
    browser.evaluate("location.hash = '#/roleplay/chn_auto'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Murugan')")
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith("Type in Tamil (or English)")
    browser.evaluate("A.rpSend('Meter podunga.')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Meter podren, aanaa meter-ku mela fifty rupees kudunga.')", 8)
    browser.evaluate("A.rpSend('Venaam, meter mattum.')")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Sari sari, meter mattum. Ukkaarunga!')", 8)
    assert no_sideways_scroll(browser)


def test_without_a_tamil_voice_nothing_is_played_and_with_one_tamil_is(site, browser):
    build_tamil(browser, site)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN', 'kn-IN'])")              # Hindi, Kannada, Indian-English voices: none may read Tamil
    browser.evaluate("document.querySelector('.phrase button').click()")
    assert browser.wait_for("document.querySelector('#toast').textContent.includes('no Tamil voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'ta-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "ta-IN" and any("\u0B80" <= ch <= "\u0BFF" for ch in spoken[0]["text"])


def test_practice_never_invents_a_tamil_score(site, browser):
    build_tamil(browser, site)
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    box = text(browser, "[data-no-score]")
    assert "nothing was assessed" in box and "%" not in box
    assert not browser.evaluate("!!document.querySelector('.phrase .feedback .score')")
    browser.evaluate("location.hash = '#/roleplay/chn_food'")                         # the roleplay's feedback card is honest too
    assert browser.wait_for("!!document.querySelector('#rp-input')")
    browser.evaluate("A.rpSend('Rendu idli kudunga.')")
    assert browser.wait_for("document.querySelectorAll('.msg.me').length === 1", 5)
    browser.evaluate("A.rpFeedback()")
    assert browser.wait_for("!!document.querySelector('#rp-fb [data-no-score]')", 5)
    assert "%" not in text(browser, "#rp-fb")


def test_switching_from_mumbai_marathi_to_chennai_drops_marathi(site, browser):
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length === 3")
    browser.evaluate("A.pickLang('mr')")
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('chennai')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 0
    browser.evaluate("A.build()")
    time.sleep(0.6)
    assert browser.evaluate("location.hash") == "#/new"
    assert browser.evaluate("document.querySelector('#toast').textContent") == "👆 Pick a language first: Tamil or English."
    browser.evaluate("A.pickLang('en')")                                              # a language both offer is kept on the way back
    time.sleep(0.3)
    tap(browser, "[onclick=\"A.pickCity('mumbai')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelectorAll('.lang.selected').length") == 1


@pytest.mark.parametrize("lang", ["hi", "kn", "hinglish"])
def test_a_saved_language_chennai_does_not_offer_falls_back_to_tamil_and_is_repaired(site, browser, lang):
    visit(browser, site, "adult", "#/", 1366)
    browser.evaluate(f"Engine.state.city = 'chennai'; Engine.state.language = '{lang}'")
    assert browser.evaluate("Engine.language()") == "ta" and browser.evaluate("Engine.speechLang()") == "ta-IN"
    browser.evaluate("Engine.save()")
    assert browser.evaluate("Engine.state.language") == "ta"
    time.sleep(1.2)
    state = browser.evaluate("fetch('/api/auth/me').then(r => r.json()).then(j => fetch('/api/state/' + j.user.handle)).then(r => r.json()).then(j => JSON.stringify([j.state.city, j.state.language]))")
    assert json.loads(state) == ["chennai", "ta"]


def test_each_city_keeps_its_own_first_week_progress(site, browser):
    build_tamil(browser, site)
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    days = json.loads(browser.evaluate("JSON.stringify([Engine.daysDone(), Engine.state.packDays.chennai, Engine.packKey()])"))
    assert days == [[1], [1], "chennai"]
    xp = browser.evaluate("Engine.state.xp")
    browser.evaluate("A.completeDay(1)")                                              # completing it again: no second day award (+50 XP)
    time.sleep(0.9)
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]" and browser.evaluate("Engine.state.xp") - xp < 50
    browser.evaluate("Engine.state.city = 'mumbai'; Engine.state.language = 'mr'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[]"              # Mumbai's Marathi pack is not touched


def test_the_home_page_is_chennais(site, browser):
    build_tamil(browser, site, 390)
    browser.evaluate("location.hash = '#/'")
    assert browser.wait_for("document.querySelector('#app').textContent.includes('Right now in Chennai')", 10)
    assert browser.evaluate("!!document.querySelector('.now-card a[href^=\"#/roleplay/chn_\"]')")
    assert no_sideways_scroll(browser)


# ---------------------------------------------------------------------------------------------------------------------
# the server's Tamil pages (migrations 0040, 0041), for a learner whose profile targets Tamil
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def tamil(site):
    from .test_mobile_layout import PASSWORD, http
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "tamil@example.com", "password": PASSWORD, "display_name": "Tamil Learner"})
    body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": "ta", "cefr_level": "A1", "date_of_birth": "1996-01-01"}, token)
    assert body["profile"]["target_language"] == "ta"
    return token


def open_as(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("route,marker", [("#/lessons", "Numbers and Money"), ("#/situations", "Auto to T. Nagar"), ("#/listening", "Help and Health: which phrase?")])
def test_the_server_pages_show_tamil_content_and_say_how_it_was_reviewed(site, browser, tamil, width, route, marker):
    open_as(browser, site, tamil, route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    note = text(browser, "[data-content-review]")
    assert "Tamil content: AI-assisted editorial review only; not yet checked by a native speaker" in note
    assert no_sideways_scroll(browser)


def test_tamil_listening_without_a_tamil_voice_is_a_labelled_transcript(site, browser, tamil):
    open_as(browser, site, tamil, "#/listening", 390)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'kn-IN'])")                  # Hindi and Kannada voices must not read Tamil
    assert browser.wait_for("document.querySelectorAll('#listening-root a.card').length > 0", 10)
    browser.evaluate("location.hash = document.querySelector('#listening-root a.card').getAttribute('href')")
    assert browser.wait_for("!!document.querySelector('[data-play]')", 10)
    tap(browser, "[data-play]")
    assert browser.wait_for("!!document.querySelector('[data-transcript]')", 5)
    t = text(browser, "[data-transcript]")
    assert "no Tamil voice" in t and any("\u0B80" <= ch <= "\u0BFF" for ch in t)
    assert browser.evaluate("window.__spoken.length") == 0 and no_sideways_scroll(browser)


def test_tamil_voice_practice_is_a_typed_check_in_tamil_script(site, browser, tamil):
    open_as(browser, site, tamil, "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    card = text(browser, "[data-typed-card]")
    assert "Roman letters or Tamil script" in card and "does not hear you or score pronunciation" in card
    roman = browser.evaluate("document.querySelector('#voice-root .deva').nextElementSibling.textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(roman.lower().rstrip('?.!'))}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)


def test_a_server_roleplay_runs_in_tamil(site, browser, tamil):
    open_as(browser, site, tamil, "#/ai-roleplay")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Auto to T. Nagar')", 10)
    browser.evaluate("[...document.querySelectorAll('[data-start]')].find(b => b.closest('.card').innerText.includes('Auto to T. Nagar')).click()")
    assert browser.wait_for("location.hash.startsWith('#/ai-roleplay/') && !!document.querySelector('#rp-input')", 10)
    scene = text(browser)
    assert "Murugan: Vanakkam!" in scene and "Say this in Tamil" in scene and "Namaste" not in scene
