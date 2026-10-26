"""Jaipur and Lucknow in a real browser (headless Google Chrome, tests/cdp.py) at phone (375, 390) and laptop (1366) widths: the cards and
previews, Hindi and English offered, each city's Hindi pack, roleplays, the Hindi voice used only if the device has one, fair prices, and
switching city. Voices are a controlled list (tests/test_marathi_flows_browser.py VOICES)."""
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


def build(b, site, city, name, width=1366):
    visit(b, site, "adult", "#/new", width)
    tap(b, f"[onclick=\"A.pickCity('{city}')\"]")
    assert b.wait_for("document.querySelectorAll('.lang').length === (" + ('3' if city == 'delhi' else '2') + ")")
    b.evaluate("A.pickLang('hi')")
    time.sleep(0.3)
    b.evaluate("A.build()")
    assert b.wait_for(f"location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in {name}'", 10)


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("city,name,alt", [("jaipur", "Jaipur", "The Pink City"), ("lucknow", "Lucknow", "The City of Nawabs"), ("bhopal", "Bhopal", "The City of Lakes")])
def test_the_city_offers_hindi_and_english_with_a_preview(site, browser, width, city, name, alt):
    visit(browser, site, "adult", "#/new", width)
    card = text(browser, f"[onclick=\"A.pickCity('{city}')\"]")
    assert name in card and f"Also called {alt}" in card and "Available" in card and "Native-speaker review pending" in card
    tap(browser, f"[onclick=\"A.pickCity('{city}')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    langs = browser.evaluate(LANGS)
    assert [l.split(" · ")[0].split(" ")[-1] for l in langs][-1] == "English" and len(langs) == 2 and "Hindi" in langs[0]
    preview = browser.evaluate("document.querySelector('[data-city-preview]').textContent")
    assert f"About {name} ({alt})" in preview and browser.evaluate("document.querySelectorAll('[data-city-preview] li').length") == 7
    assert no_sideways_scroll(browser)


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("city,name,review,phrase,roman,price", [
    ("jaipur", "Jaipur", "Jaipur Hindi", "हवा महल चलोगे?", "Hawa Mahal chaloge?", "Jaipur · approx."),
    ("lucknow", "Lucknow", "Lucknow Hindi", "हज़रतगंज चलेंगे?", "Hazratganj chalenge?", "Lucknow · approx."),
    ("bhopal", "Bhopal", "Bhopal Hindi", "न्यू मार्केट चलोगे?", "New Market chaloge?", "Bhopal · approx."),
])
def test_the_hindi_pack(site, browser, width, city, name, review, phrase, roman, price):
    build(browser, site, city, name, width)
    assert f"{name} Hindi" in review and "not yet checked by a native speaker from " + name in text(browser) and browser.evaluate("Engine.speechLang()") == "hi-IN"
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(roman)})", 10)
    page = text(browser)
    assert phrase in page and price in page and no_sideways_scroll(browser)


@pytest.mark.parametrize("width", (375, 1366))
@pytest.mark.parametrize("city,name,scene,partner,said,answer", [
    ("jaipur", "Jaipur", "jpr_auto", "Ramesh", "Sau rupaye mein chalo.", "Theek hai, sau mein chalo"),
    ("lucknow", "Lucknow", "lko_food", "Haji sahab", "Do plate galouti kebab dijiye.", "Bahut khoob!"),
    ("bhopal", "Bhopal", "bpl_food", "Mishra ji", "Pohe mein sev zyaada daalna.", "Sev bhi, nimbu bhi!"),
])
def test_a_roleplay_runs(site, browser, width, city, name, scene, partner, said, answer):
    build(browser, site, city, name, width)
    browser.evaluate(f"location.hash = '#/roleplay/{scene}'")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(partner)})")
    browser.evaluate(f"A.rpSend({json.dumps(said)})")
    assert browser.wait_for(f"document.querySelector('#app').innerText.includes({json.dumps(answer)})", 8)
    assert no_sideways_scroll(browser)


def spoken_with(b, site, city, name, voices):
    build(b, site, city, name)
    b.evaluate("location.hash = '#/lesson/3'")
    assert b.wait_for("!!document.querySelector('.phrase button')", 10)
    b.evaluate(VOICES + f"({json.dumps(voices)})")
    b.evaluate("document.querySelector('.phrase button').click()")
    time.sleep(0.4)
    return [s["voice"] for s in b.evaluate("window.__spoken")]


@pytest.mark.parametrize("city,name", [("jaipur", "Jaipur"), ("lucknow", "Lucknow")])
def test_the_voice_is_chosen_exactly_as_for_delhi(site, browser, city, name):
    """Hindi is not a language of its own script-and-voice pair like Kannada or Tamil: a Hindi city picks its voice as Delhi always has."""
    assert spoken_with(browser, site, city, name, ["en-US", "hi-IN"])[:1] == ["hi-IN"]
    for voices in (["en-US", "en-IN"], ["en-US", "en-IN", "ta-IN"]):
        assert spoken_with(browser, site, city, name, voices) == spoken_with(browser, site, "delhi", "Delhi", voices), voices


@pytest.mark.parametrize("city,name,item,quote,phrase", [
    ("jaipur", "Jaipur", "mojdi", "2000", "बहुत महँगा है, भैया।"),
    ("lucknow", "Lucknow", "chikan", "3000", "ये ज़्यादा है।"),
    ("lucknow", "Lucknow", "metro", "40", "✅ That's the normal fare."),
    ("bhopal", "Bhopal", "batua", "1500", "ये तो बहुत महँगा है।"),
])
def test_fair_price_advice(site, browser, city, name, item, quote, phrase):
    build(browser, site, city, name)
    browser.evaluate("location.hash = '#/lesson/2'")
    assert browser.wait_for("!!document.querySelector('#pc-item')")
    browser.evaluate(f"document.querySelector('#pc-item').value = '{item}'; document.querySelector('#pc-quote').value = '{quote}'; A.priceCheck()")
    assert browser.wait_for(f"document.querySelector('#pc-out').innerText.includes({json.dumps(phrase)})")


def test_switching_between_the_cities_keeps_each_ones_pack(site, browser):
    build(browser, site, "jaipur", "Jaipur")
    browser.evaluate("A.completeDay(1)")
    time.sleep(0.9)
    assert browser.evaluate("Engine.packKey()") == "jaipur" and browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]"
    browser.evaluate("Engine.state.city = 'lucknow'")
    assert browser.evaluate("Engine.packKey()") == "lucknow" and browser.evaluate("JSON.stringify(Engine.daysDone())") == "[]"
    browser.evaluate("Engine.state.city = 'jaipur'")
    assert browser.evaluate("JSON.stringify(Engine.daysDone())") == "[1]"
