"""Hyderabad in a real browser (headless Google Chrome, tests/cdp.py) at phone (375, 390) and laptop (1366) widths: the card and preview, Telugu,
Urdu and English offered, the Telugu pack, the Urdu pack written right to left with its feminine form, each language's own voice or nothing,
practice that never invents a score, roleplays, fair prices, each pack keeping its own progress, and the server's Telugu and Urdu pages. Voices
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
# Where the first and the last letter of an element's text are drawn: right to left means the first letter is to the right of the last.
ENDS = """(el => { const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const n = w.nextNode(); const r = document.createRange(); r.setStart(n, 0); r.setEnd(n, 1); const first = r.getBoundingClientRect().left;
  const s = n.textContent.trimEnd(); r.setStart(n, s.length - 2); r.setEnd(n, s.length - 1); return [first, r.getBoundingClientRect().left]; })"""


def text(b, sel="#app"):
    return b.evaluate(f"(document.querySelector({json.dumps(sel)}) || {{}}).innerText || ''")


def no_sideways_scroll(b):
    return b.evaluate("document.documentElement.scrollWidth <= innerWidth")


def build(b, site, lang, width=1366):
    visit(b, site, "adult", "#/new", width)
    tap(b, "[onclick=\"A.pickCity('hyderabad')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === 3")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Hyderabad'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_hyderabad_offers_telugu_urdu_and_english_with_a_preview(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, "[onclick=\"A.pickCity('hyderabad')\"]")
    assert "Hyderabad" in card and "Also called The City of Pearls" in card and "Available" in card and "Native-speaker review pending" in card
    tap(browser, "[onclick=\"A.pickCity('hyderabad')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Telugu", "Urdu", "English"]
    assert "తెలుగు" in langs[0] and "اردو" in langs[1]
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")
    assert "About Hyderabad (The City of Pearls)" in preview and browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_telugu_pack(site, browser, width):
    build(browser, site, "te", width)
    assert "not yet checked by a native Telugu speaker" in text(browser) and browser.evaluate("Engine.speechLang()") == "te-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('మీటర్ వేయండి.')", 10)
    page = text(browser)
    assert "Meter veyandi." in page and "Hyderabad · approx." in page and "Hyderabad Metro" in page and no_sideways_scroll(browser)
    assert "Noto Sans Telugu" in browser.evaluate("getComputedStyle(document.querySelector('.phrase .deva')).fontFamily")


@pytest.mark.parametrize("width", WIDTHS)
def test_the_urdu_pack_reads_right_to_left_with_its_feminine_form(site, browser, width):
    build(browser, site, "ur", width)
    assert "not yet checked by a native Urdu speaker" in text(browser) and browser.evaluate("Engine.speechLang()") == "ur-IN"
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('السلام علیکم! آپ کیسے ہیں؟')", 10)
    page = text(browser)
    assert "Assalaam alaikum! Aap kaise hain?" in page and "WOMEN SAY" in page.upper() and "Main yahan nayi hoon." in page and no_sideways_scroll(browser)
    el = "[...document.querySelectorAll('.phrase .deva')].find(e => /[\\u0600-\\u06FF]/.test(e.textContent))"
    assert browser.evaluate(f"getComputedStyle({el}).unicodeBidi") == "plaintext"
    first, last = browser.evaluate(f"{ENDS}({el})")
    assert first > last, (first, last)                                                    # drawn right to left
    roman = "[...document.querySelectorAll('.phrase')].map(p => p.innerText).find(t => t.includes('Assalaam alaikum'))"
    assert browser.evaluate(roman)                                                        # the romanised line is still there, left to right


@pytest.mark.parametrize("lang,voices,phrase", [("te", ["en-US", "te-IN"], "ఒక ప్లేట్ బిర్యానీ ఇవ్వండి."), ("ur", ["en-US", "ur-PK"], "ایک پلیٹ بریانی دینا۔")])
def test_each_language_is_read_only_by_its_own_voice(site, browser, lang, voices, phrase):
    build(browser, site, lang)
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN'])")                       # a Hindi voice must never read Urdu or Telugu
    browser.evaluate("document.querySelector('.phrase button').click()")
    name = {"te": "Telugu", "ur": "Urdu"}[lang]
    assert browser.wait_for(f"document.querySelector('#toast').textContent.includes('no {name} voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate(VOICES + f"({json.dumps(voices)})")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == voices[1] and spoken[0]["text"] == phrase


def test_practice_never_invents_a_score(site, browser):
    build(browser, site, "ur")
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    assert "nothing was assessed" in text(browser, "[data-no-score]") and "%" not in text(browser, "[data-no-score]")


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("lang,scene,partner,said,answer", [
    ("te", "hyd_auto", "Srinu", "Entha sepu padutundi?", "Traffic unte iravai nimishaalu."),
    ("ur", "hyd_ur_auto", "Salim bhai", "Metro station kidhar hai?", "Metro chahiye toh Nampally station saamne hai."),
])
def test_a_roleplay_runs(site, browser, width, lang, scene, partner, said, answer):
    build(browser, site, lang, width)
    browser.evaluate(f"location.hash = '#/roleplay/{scene}'")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(partner)})")
    name = {"te": "Telugu", "ur": "Urdu"}[lang]
    assert browser.evaluate("document.querySelector('#rp-input').placeholder").startswith(f"Type in {name} (or English)")
    browser.evaluate(f"A.rpSend({json.dumps(said)})")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(answer)})", 8)
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("lang,item,quote,phrase", [("te", "pearls", "6000", "చాలా ఎక్కువ."), ("ur", "chai", "20", "ٹھیک ہے، دے دیجیے۔"), ("te", "metro", "90", "Metro fares are fixed")])
def test_fair_price_advice_is_in_the_learners_language(site, browser, lang, item, quote, phrase):
    build(browser, site, lang)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({json.dumps(phrase)})")


def test_each_language_keeps_its_own_first_week_progress(site, browser):
    build(browser, site, "ur")
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    browser.evaluate("Engine.state.language = 'te'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[]"
    browser.evaluate("Engine.state.language = 'ur'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]" and browser.evaluate("Engine.packKey()") == "hyderabad:ur"


# ---------------------------------------------------------------------------------------------------------------------
# the server's Telugu and Urdu pages (migrations 0051, 0052)
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def learners(site):
    out = {}
    for code in ("te", "ur"):
        _, token = http(site["base"], "POST", "/api/auth/register", {"email": f"{code}-learner@example.com", "password": PASSWORD, "display_name": "Hyderabad Learner"})
        body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": code, "cefr_level": "A1", "date_of_birth": "1996-01-01"}, token)
        assert body["profile"]["target_language"] == code
        out[code] = token
    return out


def open_as(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("code,name,route,marker", [
    ("te", "Telugu", "#/lessons", "Numbers and Money"), ("te", "Telugu", "#/situations", "Auto to Banjara Hills"),
    ("ur", "Urdu", "#/lessons", "Numbers and Money"), ("ur", "Urdu", "#/situations", "Pearls in Pathargatti"), ("ur", "Urdu", "#/listening", "Help and Health: which phrase?"),
])
def test_the_server_pages_show_the_content_and_say_how_it_was_reviewed(site, browser, learners, width, code, name, route, marker):
    open_as(browser, site, learners[code], route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    assert f"{name} content: AI-assisted editorial review only; not yet checked by a native speaker" in text(browser, "[data-content-review]")
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("code,script", [("te", "Telugu script"), ("ur", "Urdu script")])
def test_voice_practice_accepts_the_phrase_in_its_own_script(site, browser, learners, code, script):
    open_as(browser, site, learners[code], "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    assert script in text(browser, "[data-typed-card]")
    phrase = browser.evaluate("document.querySelector('#voice-root .deva').textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(phrase)}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)
