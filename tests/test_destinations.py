"""'I'm New Here' destinations: every Indian state capital and union territory is shown, Delhi and Mumbai are available (Mumbai's card says its
native-speaker review is pending), every
other destination is "Coming Soon" and cannot be picked. The destinations are display data (frontend/content.js DESTINATIONS); the learning
packs stay in CITIES, which is unchanged and kept in step with the database. Content is read by running content.js itself; the screen is
checked in a real browser (headless Google Chrome, tests/cdp.py)."""
import json
import subprocess
import time
from pathlib import Path

import pytest

from .cdp import chrome_path
from .test_mobile_layout import box, browser, site, tap, visit  # noqa: F401  (browser, site: fixtures)

ROOT = Path(__file__).resolve().parent.parent

STATE_CAPITALS = {
    "Andhra Pradesh": "Amaravati", "Arunachal Pradesh": "Itanagar", "Assam": "Dispur", "Bihar": "Patna", "Chhattisgarh": "Raipur", "Goa": "Panaji",
    "Gujarat": "Gandhinagar", "Haryana": "Chandigarh", "Himachal Pradesh": "Shimla", "Jharkhand": "Ranchi", "Karnataka": "Bengaluru",
    "Kerala": "Thiruvananthapuram", "Madhya Pradesh": "Bhopal", "Maharashtra": "Mumbai", "Manipur": "Imphal", "Meghalaya": "Shillong",
    "Mizoram": "Aizawl", "Nagaland": "Kohima", "Odisha": "Bhubaneswar", "Punjab": "Chandigarh", "Rajasthan": "Jaipur", "Sikkim": "Gangtok",
    "Tamil Nadu": "Chennai", "Telangana": "Hyderabad", "Tripura": "Agartala", "Uttar Pradesh": "Lucknow", "Uttarakhand": "Dehradun", "West Bengal": "Kolkata",
}
UNION_TERRITORIES = {
    "Andaman and Nicobar Islands": "Sri Vijaya Puram", "Chandigarh": "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu": "Daman",
    "Delhi": "New Delhi", "Jammu and Kashmir": "Srinagar & Jammu", "Ladakh": "Leh", "Lakshadweep": "Kavaratti", "Puducherry": "Puducherry",
}


def _content():
    expr = ("var G = this; G.window = G; eval($.NSString.stringWithContentsOfFileEncodingError('" + str(ROOT / "frontend" / "content.js") + "', 4, null).js);"
            " JSON.stringify({cities: CITIES, destinations: typeof DESTINATIONS === 'undefined' ? null : DESTINATIONS})")
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", expr], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


C = _content()
D = C["destinations"] or []
CITY = {c["id"]: c for c in C["cities"]}


def selectable(d):
    """The same rule the screen uses: never more than the learning packs allow."""
    return d["status"] != "coming_soon" and d.get("city") in CITY and CITY[d["city"]]["ready"]


# =====================================================================================================================
# the data
# =====================================================================================================================
def test_every_state_capital_and_union_territory_is_listed_once():
    served = [(s["name"], s["type"], d["name"]) for d in D for s in d["serves"]]
    states = {n: cap for n, t, cap in served if t == "state"}
    uts = {n: cap for n, t, cap in served if t == "ut"}
    assert len([1 for _, t, _ in served if t == "state"]) == 28 and states == STATE_CAPITALS
    assert len([1 for _, t, _ in served if t == "ut"]) == 8 and uts == UNION_TERRITORIES


def test_destinations_are_unique_and_well_formed():
    assert len({d["id"] for d in D}) == len(D) == 34                      # Chandigarh serves Punjab, Haryana and its own territory: one card
    assert len({d["name"] for d in D}) == len(D)
    for d in D:
        assert d["emoji"] and d["serves"] and d["status"] in ("available", "in_development", "coming_soon")
        assert d.get("city") is None or d["city"] in CITY


def test_only_the_cities_with_packs_can_be_picked():
    status = {d["id"]: d["status"] for d in D}
    assert status["delhi"] == "available" and status["mumbai"] == "available"            # Mumbai: available since 2026-10-18 (docs/CONTENT_REVIEW.md)
    assert status["bengaluru"] == status["chennai"] == status["puducherry"] == "available"     # available since 2026-10-18 (docs/CONTENT_REVIEW.md)
    assert status["srinagar-jammu"] == "in_development"                                         # a lower-confidence draft (docs/CONTENT_REVIEW.md)
    assert status["kolkata"] == status["hyderabad"] == status["bhopal"] == "available" and status["shimla"] == "in_development"                             # available since 2026-10-19 (docs/CONTENT_REVIEW.md)
    assert status["jaipur"] == status["lucknow"] == "available"                                # available since 2026-10-19 (docs/CONTENT_REVIEW.md)
    assert {i for i, s in status.items() if s != "coming_soon"} == {"delhi", "mumbai", "bengaluru", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "hyderabad", "bhopal", "srinagar-jammu", "shimla"}
    assert {d["id"] for d in D if selectable(d)} == {"delhi", "mumbai", "bengaluru", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "hyderabad", "bhopal", "srinagar-jammu", "shimla"}


def test_no_unavailable_city_is_enabled():
    """Every city in the learning list is ready (Hyderabad since 2026-10-19); a coming-soon destination never links to a ready city."""
    assert [c["id"] for c in C["cities"]] == ["delhi", "mumbai", "bengaluru", "hyderabad", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "bhopal", "jk", "shimla"]
    assert {c["id"] for c in C["cities"] if c["ready"]} == {"delhi", "mumbai", "bengaluru", "hyderabad", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "bhopal", "jk", "shimla"}
    for d in D:
        if d["status"] == "coming_soon" and d.get("city"):
            assert CITY[d["city"]]["ready"] is False, d["id"]


# =====================================================================================================================
# the screen, in a real browser
# =====================================================================================================================
SCREEN = r"""(() => {
  const cards = [...document.querySelectorAll('#app .city')];
  const info = (c) => ({ text: c.innerText.replace(/\s+/g, ' ').trim(), disabled: c.getAttribute('aria-disabled') === 'true', soon: c.classList.contains('dest-soon') });
  return { cards: cards.map(info), banner: (document.querySelector('.dest-banner') || {}).innerText || '',
           groups: [...document.querySelectorAll('.dest-group h3')].map(h => h.innerText.replace(/\s+/g, ' ').trim()), step2: !!document.querySelector('.lang') };
})()"""

pytestmark_browser = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed")


@pytestmark_browser
@pytest.mark.parametrize("width", (375, 1366))
def test_the_screen_shows_the_available_cities_and_the_rest_coming_soon(site, browser, width):
    visit(browser, site, "adult", "#/new", width)
    s = browser.evaluate(SCREEN)
    open_cards = [c for c in s["cards"] if not c["soon"]]
    soon_cards = [c for c in s["cards"] if c["soon"]]
    assert len(open_cards) == 12 and "Delhi" in open_cards[0]["text"] and "Available" in open_cards[0]["text"]
    card = {c["text"].split("Also called")[0].split()[-1]: c["text"] for c in open_cards}             # by city name: the cards follow DESTINATIONS order
    blr = card["Bengaluru"]
    assert "Bengaluru" in blr and "Also called Bangalore" in blr and "Available" in blr and "In Development" not in blr
    assert "Native-speaker review pending" in blr                                          # available is not "reviewed"
    chn = card["Chennai"]
    assert "Chennai" in chn and "Also called Madras" in chn and "Available" in chn and "Native-speaker review pending" in chn
    pdy = card["Puducherry"]
    for city, alt in (("Jaipur", "The Pink City"), ("Lucknow", "The City of Nawabs")):
        assert f"Also called {alt}" in card[city] and "Available" in card[city] and "Native-speaker review pending" in card[city]
    assert "Puducherry" in pdy and "Also called Pondicherry" in pdy and "Available" in pdy and "Native-speaker review pending" in pdy
    assert "Mumbai" in open_cards[1]["text"] and "Available" in open_cards[1]["text"] and "In Development" not in open_cards[1]["text"]
    assert "Native-speaker review pending" in open_cards[1]["text"]                       # an honest card: available is not "reviewed"
    assert "review pending" not in open_cards[0]["text"] and "Early version" not in open_cards[0]["text"]   # Delhi's card is unchanged
    assert len(soon_cards) == 22 and all(c["disabled"] and "Coming Soon" in c["text"] for c in soon_cards)
    assert not any(c["disabled"] for c in open_cards)
    assert "Coming soon to every state capital and union territory" in s["banner"] and "22 more destinations" in s["banner"]
    assert s["groups"] == ["State capitals · 18", "Union territories · 4"]
    texts = " ".join(c["text"] for c in soon_cards)
    assert "Bengaluru" not in texts and "Chennai" not in texts and "Jaipur" not in texts and "Lucknow" not in texts and "Kolkata" not in texts and "Hyderabad" not in texts and "Bhopal" not in texts
    for name in ("Patna", "Shillong", "Leh", "Kavaratti", "Sri Vijaya Puram", "Punjab · Haryana · Chandigarh"):
        assert name in texts, name
    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytestmark_browser
@pytest.mark.parametrize("dest", ["patna", "shillong", "kavaratti", "chandigarh"])
def test_a_coming_soon_destination_cannot_be_picked(site, browser, dest):
    visit(browser, site, "adult", "#/new", 1366)
    browser.evaluate(f"document.querySelector(\"[onclick=\\\"A.pickCity('{dest}')\\\"]\").scrollIntoView({{block: 'center'}})")
    tap(browser, f"[onclick=\"A.pickCity('{dest}')\"]")
    time.sleep(0.3)
    assert browser.evaluate("document.querySelector('#toast').textContent").startswith("🚧 ")
    assert "coming soon" in browser.evaluate("document.querySelector('#toast').textContent")
    assert browser.evaluate(SCREEN)["step2"] is False                                                # no language step: nothing was picked
    assert browser.evaluate("A.destinations.selectable(" + json.dumps(dest) + ")") is False


@pytestmark_browser
@pytest.mark.parametrize("dest,city,langs,lang", [("delhi", "Delhi", 3, "hi"), ("mumbai", "Mumbai", 3, "hi"),   # Mumbai: Hindi, Marathi, English
                                                   ("bengaluru", "Bengaluru", 2, "kn"), ("chennai", "Chennai", 2, "ta"),       # Kannada or Tamil, English
                                                   ("puducherry", "Puducherry", 3, "fr"),                                    # Tamil, French, English
                                                   ("jaipur", "Jaipur", 2, "hi"), ("lucknow", "Lucknow", 2, "hi"),
                                                   ("kolkata", "Kolkata", 2, "bn"), ("hyderabad", "Hyderabad", 3, "ur"), ("bhopal", "Bhopal", 2, "hi"), ("shimla", "Shimla", 2, "hi"), ("srinagar-jammu", "Jammu & Kashmir", 4, "ks")])          # Hindi, English
def test_every_available_city_builds_its_pack(site, browser, dest, city, langs, lang):
    visit(browser, site, "adult", "#/new", 1366)
    tap(browser, f"[onclick=\"A.pickCity('{dest}')\"]")
    assert browser.wait_for("document.querySelectorAll('.lang').length > 0")
    assert browser.evaluate("document.querySelectorAll('.lang').length") == langs
    assert browser.evaluate(f"document.querySelector(\"[onclick=\\\"A.pickCity('{dest}')\\\"]\").getAttribute('aria-pressed')") == "true"
    browser.evaluate(f"A.pickLang('{lang}')")
    time.sleep(0.3)
    browser.evaluate("A.build()")
    assert browser.wait_for(f"location.hash === '#/pack' && document.querySelector('#app h1').textContent === 'Your First Week in {city}'", 10)
