"""Mumbai's Marathi flows in a real browser (headless Google Chrome, tests/cdp.py), for a learner whose profile targets Marathi: the review note,
listening with and without a Marathi voice (transcript mode, never a Hindi voice), voice practice's typed check, a server roleplay answered in
Marathi, and the prototype's Marathi practice that never invents a score. The browser's voices are replaced by a controlled list, so "no
Marathi voice" and "a Marathi voice" are both tested deterministically; what would have been spoken is recorded, not played."""
import json
import time

import pytest

from .cdp import chrome_path
from .test_mobile_layout import PASSWORD, browser, http, site, tap  # noqa: F401  (browser, site: fixtures)

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")

VOICES = r"""(langs => {
  window.__spoken = [];
  const voices = langs.map((l) => ({ lang: l, name: "Test " + l, voiceURI: "test-" + l, localService: true, default: false }));
  speechSynthesis.getVoices = () => voices;
  window.SpeechSynthesisUtterance = function (text) { this.text = text; this.lang = ""; this.voice = null; };   // a real utterance refuses a fake voice
  speechSynthesis.speak = (u) => { window.__spoken.push({ text: u.text, lang: u.lang, voice: u.voice && u.voice.lang }); if (u.onend) setTimeout(() => u.onend(), 0); };
  if (speechSynthesis.onvoiceschanged) speechSynthesis.onvoiceschanged();
})"""


@pytest.fixture(scope="module")
def marathi(site):
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "marathi@example.com", "password": PASSWORD, "display_name": "Marathi Learner"})
    body, _ = http(site["base"], "PUT", "/api/profile", {"native_language": "en", "target_language": "mr", "cefr_level": "A2", "date_of_birth": "1996-01-01"}, token)
    assert body["profile"]["target_language"] == "mr"
    return token


def open_page(b, site, token, route, width=1366):
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    b.set_cookie(site["base"], "llb_session", token)
    b.viewport(width, 800 if width < 700 else 900, mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=1.0)
    assert b.wait_for("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0", 10)


def text(b, sel="#app"):
    return b.evaluate(f"(document.querySelector({json.dumps(sel)}) || {{}}).innerText || ''")


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("route,marker", [("#/lessons", "Asking for Favours"), ("#/situations", "Bus to Pune"), ("#/listening", "Time and Days: what does it mean?")])
def test_server_pages_show_marathi_content_and_say_how_it_was_reviewed(site, browser, marathi, width, route, marker):
    open_page(browser, site, marathi, route, width)
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(marker)})", 10)
    assert browser.wait_for("!!document.querySelector('[data-content-review]')", 8)
    note = text(browser, "[data-content-review]")
    assert "Marathi content: AI-assisted editorial review only; not yet checked by a native speaker" in note and "2026-10-18" in note
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")


def _first_listening(browser):
    assert browser.wait_for("document.querySelectorAll('#listening-root a.card').length > 0", 10)
    browser.evaluate("location.hash = document.querySelector('#listening-root a.card').getAttribute('href')")
    assert browser.wait_for("!!document.querySelector('[data-play]')", 10)


@pytest.mark.parametrize("width", (375, 1366))
def test_without_a_marathi_voice_listening_shows_a_labelled_transcript_and_speaks_nothing(site, browser, marathi, width):
    open_page(browser, site, marathi, "#/listening", width)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN'])")                         # a Hindi voice exists: it must NOT be used for Marathi
    _first_listening(browser)
    tap(browser, "[data-play]")
    assert browser.wait_for("!!document.querySelector('[data-transcript]')", 5)
    t = text(browser, "[data-transcript]")
    assert "transcript mode (text, not audio)" in t.lower() and "no Marathi voice" in t
    assert any("ऀ" <= ch <= "ॿ" for ch in t)
    assert browser.evaluate("window.__spoken.length") == 0
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_with_a_marathi_voice_listening_speaks_marathi(site, browser, marathi):
    open_page(browser, site, marathi, "#/listening")
    browser.evaluate(VOICES + "(['en-US', 'hi-IN', 'mr-IN'])")
    _first_listening(browser)
    tap(browser, "[data-play]")
    time.sleep(0.4)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "mr-IN" and any("ऀ" <= ch <= "ॿ" for ch in spoken[0]["text"])
    assert not browser.evaluate("!!document.querySelector('[data-transcript]')")


def test_voice_practice_offers_a_typed_check_that_never_claims_to_hear(site, browser, marathi):
    open_page(browser, site, marathi, "#/voice")
    assert browser.wait_for("!!document.querySelector('[data-typed-card]')", 10)
    card = text(browser, "[data-typed-card]")
    assert "does not hear you or score pronunciation" in card
    roman = browser.evaluate("document.querySelector('#voice-root .deva').nextElementSibling.textContent")
    browser.evaluate(f"document.querySelector('[data-typed]').value = {json.dumps(roman.lower().rstrip('?.!'))}")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-ok]')", 5)
    browser.evaluate("document.querySelector('[data-typed]').value = 'kitna hua'")
    tap(browser, "[data-typed-check]")
    assert browser.wait_for("!!document.querySelector('[data-typed-no]')", 5)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN'])")
    tap(browser, "[data-hear]")
    assert browser.wait_for("document.querySelector('#voice-root').innerText.includes('no Marathi voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0


def test_a_server_roleplay_runs_in_marathi(site, browser, marathi):
    open_page(browser, site, marathi, "#/ai-roleplay")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Kaali-peeli taxi')", 10)
    browser.evaluate("[...document.querySelectorAll('[data-start]')].find(b => b.closest('.card').innerText.includes('Kaali-peeli taxi')).click()")
    assert browser.wait_for("location.hash.startsWith('#/ai-roleplay/') && !!document.querySelector('#rp-input')", 10)
    scene = text(browser)
    assert "Shinde kaka: Namaskar!" in scene and "Say this in Marathi" in scene and "Namaste" not in scene
    browser.evaluate("document.querySelector('#rp-input').value = 'Dada, meterne yenar ka?'; document.querySelector('[data-say]').click()")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('✓ Correct')", 10)
    page = text(browser)
    assert any(p in page for p in ("Chhan!", "Ekdum barobar!", "Shabbas!")) and not any(h in page for h in ("Achha!", "Bilkul theek!", "Shabaash!"))


def test_the_prototype_never_invents_a_marathi_score(site, browser):
    """The First Week pack in Marathi: without a Marathi voice nothing is read by a Hindi voice, and practice without a transcript shows no score."""
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "pack-mr@example.com", "password": PASSWORD, "display_name": "Pack Learner"})
    open_page(browser, site, token, "#/")
    browser.evaluate("Engine.state.city = 'mumbai'; Engine.state.language = 'mr'; Engine.save(); location.hash = '#/lesson/2'")
    assert browser.wait_for("document.querySelector('#app').innerText.includes('मीटरने येणार का?')", 10)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")      # 🔊 Listen on the first phrase
    assert browser.wait_for("document.querySelector('#toast').textContent.includes('no Marathi voice')", 5)
    assert browser.evaluate("window.__spoken.length") == 0
    browser.evaluate("window.webkitSpeechRecognition = undefined; window.SpeechRecognition = undefined")
    browser.evaluate("Engine.canListen = false")
    browser.evaluate("document.querySelector('.phrase .mic-btn').click()")
    assert browser.wait_for("!!document.querySelector('[data-no-score]')", 5)
    box = text(browser, "[data-no-score]")
    assert "nothing was assessed" in box and "%" not in box
    assert not browser.evaluate("!!document.querySelector('.phrase .feedback .score')")                 # no percentage "pronunciation" score anywhere


def test_delhi_hindi_practice_is_unchanged(site, browser):
    _, token = http(site["base"], "POST", "/api/auth/register", {"email": "pack-hi@example.com", "password": PASSWORD, "display_name": "Delhi Learner"})
    open_page(browser, site, token, "#/")
    browser.evaluate("Engine.state.city = 'delhi'; Engine.state.language = 'hi'; Engine.save(); location.hash = '#/lesson/1'")
    assert browser.wait_for("!!document.querySelector('.phrase .mic-btn')", 10)
    browser.evaluate(VOICES + "(['en-US', 'hi-IN'])")
    browser.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.3)
    spoken = browser.evaluate("window.__spoken")
    assert spoken and spoken[0]["voice"] == "hi-IN"                          # Hindi is read by the Hindi voice, as before


@pytest.mark.parametrize("width", (390, 1366))
def test_an_admin_manages_marathi_content_in_the_console(site, browser, width):
    """Filter the curriculum to Marathi A2, open a lesson, validate it, take it off the shelf and put it back."""
    open_page(browser, site, site["tokens"]["admin"], "#/admin/curriculum/lessons?language=mr&cefr=A2", width)
    assert browser.wait_for("document.querySelector('#app').innerText.includes('Asking for Favours')", 10)
    rows = browser.evaluate("document.querySelectorAll('#app tr[data-id]').length")
    assert rows == 10
    browser.evaluate("location.hash = [...document.querySelectorAll('#app tr[data-id] a')].find(a => a.textContent.includes('Travelling Out of Mumbai')).getAttribute('href')")
    assert browser.wait_for("!!document.querySelector('[data-act=\"validate\"]')", 10)
    for act, done in (("validate", "No findings."), ("unpublish", "Unpublished: it is a draft again."), ("publish", "Published ✓")):
        browser.evaluate(f"document.querySelector('[data-act=\"{act}\"]').click()")
        assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(done)})", 10), act
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")
