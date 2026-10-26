"""Jammu & Kashmir in a real browser (headless Google Chrome, tests/cdp.py) at phone (375, 390) and laptop (1366) widths: the In Development card
and preview, Kashmiri, Dogri, Urdu and English offered, the three packs (Kashmiri and Urdu right to left), no Kashmiri or Dogri voice so nothing
is read aloud, roleplays, fair prices, each pack keeping its own progress, and the server's Kashmiri and Dogri pages. Voices are a controlled
list (tests/test_marathi_flows_browser.py VOICES)."""
import json
import time

import pytest

from .cdp import chrome_path
from .test_marathi_flows_browser import VOICES
from .test_mobile_layout import PASSWORD, browser, http, site, tap, visit  # noqa: F401  (browser, site: fixtures)

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")

LANGS = "[...document.querySelectorAll('.lang')].map(c => c.innerText.replace(/\\s+/g, ' ').trim())"
WIDTHS = (375, 390, 1366)
CARD = "[onclick=\"A.pickCity('srinagar-jammu')\"]"
ENDS = """(el => { const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); const n = w.nextNode(); const r = document.createRange();
  r.setStart(n, 0); r.setEnd(n, 1); const first = r.getBoundingClientRect().left; const s = n.textContent.trimEnd();
  r.setStart(n, s.length - 2); r.setEnd(n, s.length - 1); return [first, r.getBoundingClientRect().left]; })"""


def text(b, sel="#app"):
    return b.evaluate(f"(document.querySelector({json.dumps(sel)}) || {{}}).innerText || ''")


def no_sideways_scroll(b):
    return b.evaluate("document.documentElement.scrollWidth <= innerWidth")


def build(b, site, lang, width=1366):
    visit(b, site, "adult", "#/new", width)
    tap(b, CARD)
    assert b.wait_for("document.querySelectorAll('.lang').length === 4")
    b.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for("location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in Jammu & Kashmir'", 10)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_card_says_in_development_and_offers_four_languages(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, CARD)
    assert "Jammu & Kashmir" in card and "In Development" in card and "Available" not in card and "Early version" in card
    tap(browser, CARD)
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs] == ["Kashmiri", "Dogri", "Urdu", "English"]
    assert "(draft)" in langs[0] and "(draft)" in langs[1] and "(draft)" not in langs[2]
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")
    assert "About Srinagar & Jammu" in preview and "draft" in preview and browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_kashmiri_pack_reads_right_to_left_and_says_it_is_a_draft(site, browser, width):
    build(browser, site, "ks", width)
    page = text(browser)
    assert "AI-assisted first draft" in page and browser.evaluate("Engine.speechLang()") == "ks-IN"
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Myon naav chhu Alex.')", 10)
    assert "Bu chhes yeti nev." in text(browser) and no_sideways_scroll(browser)
    el = "[...document.querySelectorAll('.phrase .deva')].find(e => /[\\u0600-\\u06FF]/.test(e.textContent))"
    first, last = browser.evaluate(f"{ENDS}({el})")
    assert first > last, (first, last)


@pytest.mark.parametrize("width", (375, 1366))
def test_the_dogri_pack(site, browser, width):
    build(browser, site, "doi", width)
    assert "AI-assisted first draft" in text(browser) and browser.evaluate("Engine.speechLang()") == "doi-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('मटाडोर कुत्थें थम्मदी ऐ?')", 10)
    page = text(browser)
    assert "Matador kutthen thammdi ai?" in page and "Jammu & Kashmir · approx." in page and no_sideways_scroll(browser)


def test_the_urdu_pack_is_jks_not_hyderabads(site, browser):
    build(browser, site, "ur")
    browser.evaluate("location.hash = '#/lesson/1'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('السلام علیکم! مزاج کیسے ہیں؟')", 10)
    assert browser.evaluate("Engine.packKey()") == "jk:ur" and "Pathargatti" not in text(browser)


@pytest.mark.parametrize("lang,name", [("ks", "Kashmiri"), ("doi", "Dogri")])
def test_no_voice_reads_kashmiri_or_dogri(site, browser, lang, name):
    """Browsers have no Kashmiri or Dogri voice; an Urdu or Hindi voice must not read them in their place."""
    build(browser, site, lang)
    browser.evaluate("location.hash = '#/lesson/3'")
    assert browser.wait_for("!!document.querySelector('.phrase button')", 10)
    browser.evaluate(VOICES + "(['en-US', 'en-IN', 'hi-IN', 'ur-PK'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    assert browser.wait_for(f"document.querySelector('#toast').textContent.includes('no {name} voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0


@pytest.mark.parametrize("lang,scene,partner,said,answer", [
    ("ks", "jk_food", "Rafiq", "Noon chai chha?", "Aa, garam noon chai!"),
    ("doi", "jk_doi_auto", "Kuldeep", "Matador kutthen thammdi ai?", "Matador baahar stand thammdi ai"),
    ("ur", "jk_ur_auto", "Farooq", "Shikaara kahan milega?", "Shikaara Dal Gate ke ghaat par milega."),
])
def test_a_roleplay_runs(site, browser, lang, scene, partner, said, answer):
    build(browser, site, lang, 390)
    browser.evaluate(f"location.hash = '#/roleplay/{scene}'")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(partner)})")
    browser.evaluate(f"A.rpSend({json.dumps(said)})")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(answer)})", 8)
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("lang,item,quote,phrase", [("ks", "shikara", "2000", "official rate is about ₹770"), ("doi", "kalari", "60", "ठीक ऐ, देओ।"),
                                                    ("ur", "pashmina", "20000", "بہت مہنگا ہے۔")])
def test_fair_price_advice(site, browser, lang, item, quote, phrase):
    build(browser, site, lang)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({json.dumps(phrase)})")


def test_each_language_keeps_its_own_first_week_progress(site, browser):
    build(browser, site, "doi")
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    for lang, done in (("ks", "[]"), ("ur", "[]"), ("doi", "[1]")):
        browser.evaluate(f"Engine.state.language = '{lang}'")
        assert browser.evaluate("JSON.stringify(Engine.daysDone())") == done, lang
    assert browser.evaluate("Engine.packKey()") == "jk:doi"


# ---------------------------------------------------------------------------------------------------------------------
# the server's Kashmiri and Dogri pages (migrations 0055, 0056)
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def learners(site):
    out = {}
    for code in ("ks", "doi"):
        _, token = http(site["base"], "POST", "/api/auth/register", {"email": f"{code}-learner@example.com", "password": PASSWORD, "display_name": "J&K Learner"})
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
@pytest.mark.parametrize("code,name,route,marker", [("ks", "Kashmiri", "#/lessons", "Numbers and Money"), ("ks", "Kashmiri", "#/situations", "Welcome to the houseboat"),
                                                    ("doi", "Dogri", "#/lessons", "Numbers and Money"), ("doi", "Dogri", "#/situations", "Kalari kulcha at a dhaba")])
def test_the_server_pages_show_the_content_and_say_it_is_a_draft(site, browser, learners, width, code, name, route, marker):
    open_as(browser, site, learners[code], route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    banner = text(browser, "[data-content-review]")
    assert f"{name} content: AI-assisted editorial review only; not yet checked by a native speaker" in banner and "A DRAFT" in banner
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("code,script", [("ks", "Kashmiri script"), ("doi", "Devanagari")])
def test_voice_practice_accepts_the_phrase_in_its_own_script(site, browser, learners, code, script):
    open_as(browser, site, learners[code], "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    assert script in text(browser, "[data-typed-card]")
    phrase = browser.evaluate("document.querySelector('#voice-root .deva').textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(phrase)}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)
