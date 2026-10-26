"""Phase 15A: the responsive, mobile-first layout and the sign-in gate, checked in a REAL browser (headless Google Chrome via tests/cdp.py) against a live test
server on a temp database. These measure what a phone actually renders: element boxes, overflow, focus, hit-testing of taps. They emulate
phone, tablet and desktop viewports and touch input; they are not a physical device, Safari or a screen reader (see ARCHITECTURE.md
section 28 for what remains unverified).

The browser can reach nothing but 127.0.0.1 (cdp.py), the server has no model provider (blank keys, a dead proxy) and its database is a
temp file. Without Google Chrome the module is skipped as a whole."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from backend.auth import service
from backend.db import connect
from backend.manage import create_admin
from backend.repositories import users as users_repo

from .cdp import Browser, chrome_path
from .conftest import PASSWORD, SHARED_ADDRESS_LIMITS

pytestmark = pytest.mark.skipif(chrome_path() is None, reason="Google Chrome is not installed: the real-browser layout checks need it")

ROOT = Path(__file__).resolve().parent.parent
REAL_DB = (ROOT / "buddy.db").resolve()
PHONES, TABLET, DESKTOPS = (320, 375, 414), 768, (1024, 1280)
ROUTES = {
    "anonymous": ["#/", "#/plan", "#/admin"],                                 # a visitor who is not signed in: the sign-in screen, whatever the route
    "adult": ["#/", "#/new", "#/pack", "#/tutor", "#/learn", "#/confidence", "#/progress", "#/lesson/1", "#/roleplay/auto", "#/lessons", "#/situations", "#/listening", "#/voice", "#/plan", "#/ai-insights", "#/ai-tutor", "#/ai-roleplay", "#/rewards",
              "#/friends", "#/profile", "#/speaking"],
    "child": ["#/kids", "#/listening", "#/profile"],
    "parent": ["#/parent", "#/profile"],
    "admin": ["#/admin", "#/admin/curriculum", "#/admin/analytics", "#/admin/learners", "#/admin/audit", "#/admin/security", "#/admin/health"],
}


# =====================================================================================================================
# the live test server and the browser
# =====================================================================================================================
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(base, method, path, body=None, token=None):
    headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}
    if token:
        headers["Cookie"] = f"llb_session={token}"
    req = urllib.request.Request(base + path, data=json.dumps(body or {}).encode() if method != "GET" else None, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        cookie = r.headers.get("set-cookie") or ""
        return json.loads(r.read() or b"null"), (cookie.split("llb_session=")[1].split(";")[0] if "llb_session=" in cookie else token)


def learner(base, email, dob, name="Learner"):
    _, token = http(base, "POST", "/api/auth/register", {"email": email, "password": PASSWORD, "display_name": name})
    http(base, "PUT", "/api/profile", {"native_language": "en", "target_language": "hi", "cefr_level": "A1", "date_of_birth": dob}, token)
    return token


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    work = tmp_path_factory.mktemp("mobilesrv")
    db_path = (work / "test.db").resolve()
    assert db_path != REAL_DB and ROOT not in db_path.parents
    env = {**os.environ, **SHARED_ADDRESS_LIMITS, "DB_PATH": str(db_path), "RECORDINGS_DIR": str(work / "recordings"), "STT_PROVIDER": "mock"}
    env.pop("PRONUNCIATION_PROVIDER", None)
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(base + "/api/health", timeout=1)
                break
            except OSError:
                time.sleep(0.15)
        else:
            raise RuntimeError("test server did not start")
        tokens = {"anonymous": None, "adult": learner(base, "adult@example.com", "1995-05-20", "Adult Learner"),
                  "child": learner(base, "kid@example.com", "2018-05-20", "Kid")}
        teen = learner(base, "teen@example.com", "2011-05-20", "Teen")
        code, _ = http(base, "POST", "/api/profile/parent-link-code", {}, teen)
        _, tokens["parent"] = http(base, "POST", "/api/auth/register", {"email": "parent@example.com", "password": PASSWORD, "display_name": "Parent", "role": "parent"})
        http(base, "POST", "/api/parent/children", {"code": code["code"]}, tokens["parent"])
        create_admin(db_path, "admin@example.com", PASSWORD, "Admin")
        with connect(db_path) as conn:                                 # an admin session that has passed a second factor (the console needs it)
            uid = conn.execute("SELECT id FROM users WHERE email = 'admin@example.com'").fetchone()[0]
            tokens["admin"], _ = service._start_session(conn, uid, service.utcnow(), mfa_level=1, auth_method="password+totp")
        yield {"base": base, "db": db_path, "tokens": tokens}
    finally:
        proc.terminate()
        proc.wait(10)


@pytest.fixture(scope="module")
def browser():
    b = Browser()
    b.call("Network.enable")
    yield b
    b.close()


def visit(b, site, who, route, width, height=None, settle=0.9):
    """A fresh page load as `who` (no state carried over from another account), then the route."""
    b.goto("about:blank", settle=0.05)
    b.clear_cookies()
    if site["tokens"][who]:
        b.set_cookie(site["base"], "llb_session", site["tokens"][who])
    b.viewport(width, height or (800 if width < 700 else 900), mobile=width < 1000)
    b.goto(f"{site['base']}/{route}", settle=settle)
    settled = ("!document.body.classList.contains('gated') && document.querySelectorAll('#nav a').length > 0" if site["tokens"].get(who)
               else "!!document.querySelector('#gate-root #pf-login')")
    assert b.wait_for(settled), f"the app did not settle for {who} at {route}"   # who is looking is known (two round trips for a parent)
    time.sleep(0.2)


OVERFLOW = r"""(() => {
  const W = document.documentElement.clientWidth, out = [];
  const exempt = (el) => { for (let p = el; p && p !== document.body; p = p.parentElement) { const cs = getComputedStyle(p);
      if (p !== el && /(auto|scroll|hidden|clip)/.test(cs.overflowX)) return true;                     // inside a scroll box or a deliberate clip
      if (cs.position === 'fixed' && (cs.opacity === '0' || cs.pointerEvents === 'none')) return true;  // a closed panel
      if (p.matches && p.matches('.aurora, .aurora *, .loop-track, .spark-canvas, .confetti, .dots')) return true; }                 // decoration
    return false; };
  for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && (r.right > W + 1 || r.left < -1) && !exempt(el)) out.push(el.tagName + '.' + el.className + ' ' + Math.round(r.left) + '..' + Math.round(r.right)); }
  return {W, scroll: document.documentElement.scrollWidth, out: out.slice(0, 5)};
})()"""


def box(b, selector):
    return b.evaluate(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return null; const r = e.getBoundingClientRect();"
                      f" const cs = getComputedStyle(e); return {{x: r.left, y: r.top, w: r.width, h: r.height, display: cs.display, visible: cs.visibility !== 'hidden' && cs.display !== 'none' && r.width > 0}}; }})()")


def tap_at(b, x, y):
    b.call("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
    b.call("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
    time.sleep(0.4)


def tap(b, selector):
    """A real touch on the element's centre: whatever is on top there receives it (so an element covered by another one is not 'tapped')."""
    b.evaluate(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); if (e && !e.closest('#bottom-nav, #more-sheet')) e.scrollIntoView({{block: 'center'}}); }})()")
    time.sleep(0.2)
    r = box(b, selector)
    assert r and r["visible"], f"{selector} is not visible"
    tap_at(b, r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)


def type_into(b, selector, text):
    b.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
    b.call("Input.insertText", text=text)


def key(b, name, code, shift=False):
    mods = 8 if shift else 0
    params = {"key": name, "code": code, "windowsVirtualKeyCode": {"Tab": 9, "Escape": 27}[name], "modifiers": mods}
    b.call("Input.dispatchKeyEvent", type="keyDown", **params)
    b.call("Input.dispatchKeyEvent", type="keyUp", **params)
    time.sleep(0.15)


# =====================================================================================================================
# layout: nothing spills off the screen
# =====================================================================================================================
@pytest.mark.parametrize("who", sorted(ROUTES))
def test_no_page_spills_sideways_at_any_width(site, browser, who):
    problems = []
    for width in (*PHONES, TABLET, *DESKTOPS):
        for route in ROUTES[who]:
            visit(browser, site, who, route, width, settle=0.7)
            r = browser.evaluate(OVERFLOW)
            if r["out"] or r["scroll"] > r["W"]:
                problems.append((width, route, r))
    assert problems == []


def test_the_desktop_layout_is_unchanged(site, browser):
    for width in DESKTOPS:
        visit(browser, site, "adult", "#/", width)
        side, bottom = box(browser, ".sidebar"), box(browser, "#bottom-nav")
        assert side["visible"] and round(side["w"]) == 248 and not bottom["visible"]
        assert not box(browser, "#more-sheet")["visible"] and browser.evaluate("document.querySelectorAll('#nav a').length") >= 19


# =====================================================================================================================
# navigation on a phone: every page is reachable, nothing is off-screen
# =====================================================================================================================
NAV_STATE = r"""(() => {
  const side = [...document.querySelectorAll('#nav a')].map(a => a.getAttribute('href'));
  const bottom = [...document.querySelectorAll('#bottom-nav a')].map(a => a.getAttribute('href'));
  const more = [...document.querySelectorAll('#more-sheet .more-links a')].map(a => a.getAttribute('href'));
  const W = document.documentElement.clientWidth;
  const slots = [...document.querySelectorAll('#bottom-nav a, #bottom-nav button')].map(e => e.getBoundingClientRect());
  return {side, bottom, more, hasMore: !!document.querySelector('#bottom-nav .bn-more'),
          inside: slots.every(r => r.left >= 0 && r.right <= W + 0.5), minW: Math.min(...slots.map(r => r.width)), minH: Math.min(...slots.map(r => r.height)),
          sidebar: getComputedStyle(document.querySelector('.sidebar')).display};
})()"""


@pytest.mark.parametrize("who,home", [("adult", "#/"), ("child", "#/kids"), ("parent", "#/parent"), ("admin", "#/admin")])
@pytest.mark.parametrize("width", PHONES)
def test_every_page_of_the_navigation_is_reachable_on_a_phone(site, browser, who, home, width):
    visit(browser, site, who, home, width)
    s = browser.evaluate(NAV_STATE)
    assert s["sidebar"] == "none" and s["side"], s
    assert set(s["bottom"]) | set(s["more"]) == set(s["side"]) and not set(s["bottom"]) & set(s["more"])   # the same pages, each once
    assert s["inside"] and s["minW"] >= 44 and s["minH"] >= 44, s
    assert s["hasMore"] == bool(s["more"])


def test_each_mode_keeps_its_own_navigation_on_a_phone(site, browser):
    """Responsive layout must not widen what a mode may see: the phone bar and menu hold exactly the sidebar's list."""
    visit(browser, site, "child", "#/kids", 375)
    child = browser.evaluate(NAV_STATE)
    assert child["bottom"] == ["#/kids", "#/listening", "#/profile"] and not child["hasMore"]
    visit(browser, site, "parent", "#/parent", 375)
    parent = browser.evaluate(NAV_STATE)
    assert parent["bottom"][0] == "#/parent" and "#/profile" in parent["bottom"]
    assert not {"#/rewards", "#/friends", "#/ai-tutor", "#/ai-roleplay", "#/ai-insights"} & set(parent["bottom"] + parent["more"])
    visit(browser, site, "admin", "#/admin", 375)
    admin = browser.evaluate(NAV_STATE)
    assert all(h.startswith("#/admin") for h in admin["bottom"] + admin["more"]) and "#/admin/health" in admin["more"]
    visit(browser, site, "adult", "#/", 375)
    adult = browser.evaluate(NAV_STATE)
    assert not [h for h in adult["bottom"] + adult["more"] if h.startswith("#/admin") or h == "#/parent"]


def test_the_more_menu_works_by_touch_and_keyboard(site, browser):
    visit(browser, site, "adult", "#/", 375)
    assert not box(browser, "#more-sheet")["visible"]
    tap(browser, "#bottom-nav .bn-more")
    assert box(browser, "#more-sheet")["visible"]
    assert browser.evaluate("document.querySelector('.bn-more').getAttribute('aria-expanded')") == "true"
    assert browser.evaluate("document.activeElement.matches('#more-sheet .more-links a')")                 # focus moved into the menu
    links = browser.evaluate("document.querySelectorAll('#more-sheet .more-panel a, #more-sheet .more-panel button').length")
    for _ in range(links):                                                                                  # Tab cycles inside the dialog
        key(browser, "Tab", "Tab")
        assert browser.evaluate("!!document.activeElement.closest('#more-sheet')")
    key(browser, "Escape", "Escape")
    assert not box(browser, "#more-sheet")["visible"]
    assert browser.evaluate("document.activeElement.classList.contains('bn-more')")                         # focus back to More
    assert browser.evaluate("document.querySelector('.bn-more').getAttribute('aria-expanded')") == "false"
    tap(browser, "#bottom-nav .bn-more")
    tap(browser, '#more-sheet a[href="#/profile"]')                                                        # choosing a page closes the menu
    assert browser.evaluate("location.hash") == "#/profile" and not box(browser, "#more-sheet")["visible"]
    assert browser.evaluate("document.querySelector('#bottom-nav .bn-more').classList.contains('active')")   # the bar shows where you are
    tap(browser, "#bottom-nav .bn-more")
    tap_at(browser, 187, 20)                                                                               # tapping the backdrop above the panel closes it
    assert not box(browser, "#more-sheet")["visible"]


def test_the_current_page_is_announced(site, browser):
    visit(browser, site, "adult", "#/learn", 375)
    assert browser.evaluate("[...document.querySelectorAll('[aria-current=\"page\"]')].map(a => a.getAttribute('href'))") == ["#/learn", "#/learn"]
    assert browser.evaluate("[...document.querySelectorAll('nav .ic')].every(i => i.getAttribute('aria-hidden') === 'true')")
    assert browser.evaluate("document.querySelector('#bottom-nav').getAttribute('aria-label')") == "Main"


# =====================================================================================================================
# touch, keyboard focus and the phone's own keyboard
# =====================================================================================================================
TARGETS = r"""(() => {
  const hidden = (el) => { for (let p = el; p; p = p.parentElement) { const cs = getComputedStyle(p);
      if (cs.opacity === '0' || cs.pointerEvents === 'none' || cs.visibility === 'hidden' || cs.display === 'none') return true; } return false; };
  const small = [];
  for (const el of document.querySelectorAll('button, .btn, select, input:not([type=checkbox]):not([type=radio]), textarea, #bottom-nav a, .back')) {
    if (hidden(el) || el.closest('.msg .tools')) continue;                         // per-message tools are deliberately compact (36px)
    const r = el.getBoundingClientRect();
    if (r.width && r.height < 43.5) small.push(el.tagName + ' ' + (el.textContent || el.placeholder || '').trim().slice(0, 20) + ' ' + Math.round(r.height));
  }
  return small;
})()"""


@pytest.mark.parametrize("who,route", [("anonymous", "#/"), ("adult", "#/"), ("adult", "#/learn"), ("adult", "#/lesson/1"), ("adult", "#/roleplay/auto"),
                                       ("adult", "#/plan"), ("adult", "#/voice"), ("adult", "#/friends"), ("adult", "#/profile"),
                                       ("parent", "#/parent"), ("admin", "#/admin/audit"), ("admin", "#/admin/security")])
def test_controls_are_big_enough_to_tap(site, browser, who, route):
    visit(browser, site, who, route, 375)
    assert browser.evaluate(TARGETS) == []


@pytest.mark.parametrize("who,route", [("anonymous", "#/"), ("adult", "#/tutor"), ("adult", "#/roleplay/auto"), ("parent", "#/parent"), ("admin", "#/admin/audit"), ("adult", "#/friends")])
def test_fields_are_16px_so_phones_do_not_zoom_when_typing(site, browser, who, route):
    visit(browser, site, who, route, 375)
    sizes = browser.evaluate("[...document.querySelectorAll('input:not([type=checkbox]):not([type=radio]):not([type=range]), select, textarea')]"
                             ".filter(e => e.getBoundingClientRect().width).map(e => parseFloat(getComputedStyle(e).fontSize))")
    assert sizes and min(sizes) >= 16


def test_desktop_fields_keep_their_compact_size(site, browser):
    visit(browser, site, "anonymous", "#/", 1280)
    assert browser.evaluate("parseFloat(getComputedStyle(document.querySelector('#pf-email')).fontSize)") < 16


def test_keyboard_focus_is_always_visible(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    seen = []
    for _ in range(12):
        key(browser, "Tab", "Tab")
        seen.append(browser.evaluate("(() => { const e = document.activeElement; if (!e || e === document.body) return null; const cs = getComputedStyle(e);"
                                     " return {tag: e.tagName, w: parseFloat(cs.outlineWidth), style: cs.outlineStyle}; })()"))
    focused = [s for s in seen if s]
    assert len(focused) >= 8 and all(s["w"] >= 2 and s["style"] != "none" for s in focused), focused
    assert {"INPUT", "BUTTON", "A"} <= {s["tag"] for s in focused}


def test_auth_and_answer_fields_are_labelled_and_hint_the_right_keyboard(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    assert browser.evaluate("['#pf-email', '#pf-pass', '#pf-name', '#pf-role-learner', '#pf-role-parent'].every(s => { const e = document.querySelector(s);"
                            " return e.labels.length > 0 && e.labels[0].textContent.trim().length > 0; })")             # real <label>s
    assert browser.evaluate("document.querySelector('#pf-email').type") == "email"
    visit(browser, site, "adult", "#/tutor", 375)
    assert browser.evaluate("(() => { const i = document.querySelector('#t-input'); return [i.getAttribute('aria-label'), i.getAttribute('enterkeyhint')]; })()") == ["Ask your tutor", "send"]


@pytest.mark.parametrize("route", ["#/tutor", "#/roleplay/auto"])
@pytest.mark.parametrize("width", PHONES)
def test_the_help_button_never_covers_the_send_button(site, browser, route, width):
    visit(browser, site, "adult", route, width)
    send, sos = box(browser, ".composer .send"), box(browser, ".sos-fab")
    assert send["visible"] and sos["visible"]
    apart = send["x"] + send["w"] <= sos["x"] or sos["x"] + sos["w"] <= send["x"] or send["y"] + send["h"] <= sos["y"] or sos["y"] + sos["h"] <= send["y"]
    assert apart, (send, sos)
    assert browser.evaluate("(() => { const s = document.querySelector('.composer .send').getBoundingClientRect(); const e = document.elementFromPoint(s.left + s.width / 2, "
                            "Math.min(s.top + s.height / 2, innerHeight - 1)); return !e || e.closest('.composer') !== null || e.closest('#bottom-nav') !== null; })()")


def test_the_chat_shrinks_to_a_short_visible_screen(site, browser):
    """A short visible screen (a small phone, or one with its keyboard open) gets a chat that is 360px at most, not the old fixed 520px minimum,
    so the reply field is not pushed off the screen. (Emulation changes the whole viewport; that dvh tracks the keyboard on a real phone,
    where vh does not, is not something it can show.)"""
    visit(browser, site, "adult", "#/tutor", 375, height=800)
    tall = box(browser, ".chat")["h"]
    browser.viewport(375, 500)
    time.sleep(0.3)
    short = box(browser, ".chat")["h"]
    assert short < tall and short == 360


def test_there_is_no_on_screen_keyboard_to_get_in_the_way(site, browser):
    """The repository has no on-screen (virtual) keyboard; Phase 15A adds none. The phone's own keyboard is used, nothing is drawn over it."""
    for route in ("#/tutor", "#/learn", "#/lesson/1", "#/roleplay/auto"):
        visit(browser, site, "adult", route, 375)
        assert browser.evaluate("document.querySelectorAll('[class*=keyboard], [id*=keyboard], [class*=osk], [data-keyboard]').length") == 0


# =====================================================================================================================
# the sign-in gate: signed-in accounts only; the 🆘 help and the emergency number for everyone
# =====================================================================================================================
GATE = r"""(() => ({ gated: document.body.classList.contains('gated'), login: !!document.querySelector('#gate-root #pf-login'),
  register: !!document.querySelector('#gate-root #pf-register'), hero: !!document.querySelector('.hero'),
  chrome: ['.sidebar', '#bottom-nav', '#more-sheet'].some(s => { const e = document.querySelector(s); return e && getComputedStyle(e).display !== 'none'; }) }))()"""


@pytest.mark.parametrize("width", (375, 1366))
def test_signed_out_visitors_only_get_the_sign_in_screen(site, browser, width):
    for route in ("#/", "#/plan", "#/lessons", "#/tutor", "#/kids", "#/parent", "#/admin", "#/admin/security", "#/profile"):
        visit(browser, site, "anonymous", route, width)
        assert browser.evaluate(GATE) == {"gated": True, "login": True, "register": True, "hero": False, "chrome": False}, route


@pytest.mark.parametrize("width", (375, 1366))
def test_help_and_the_emergency_number_work_without_an_account(site, browser, width):
    visit(browser, site, "anonymous", "#/", width)
    assert browser.evaluate("[...document.querySelectorAll('a[href=\"tel:112\"]')].length") >= 2          # on the sign-in screen and in the 🆘 panel
    tap(browser, ".sos-fab")
    assert browser.evaluate("document.querySelector('#sos-panel').classList.contains('open')")
    assert browser.evaluate("document.querySelectorAll('#sos-panel .sos-row').length") == 5
    tap(browser, "#sos-panel .btn-ghost")                                                                   # ✕
    tap(browser, ".gate-help .btn-ghost")                                                                   # the screen's own "Emergency phrases"
    assert browser.evaluate("document.querySelector('#sos-panel').classList.contains('open')")


def account_for(site, email, name, role="learner"):
    http(site["base"], "POST", "/api/auth/register", {"email": email, "password": PASSWORD, "display_name": name, "role": role})


@pytest.mark.parametrize("width", (375, 1366))
def test_signing_in_opens_the_app(site, browser, width):
    email = f"signin{width}@example.com"
    account_for(site, email, f"Signed In {width}")
    visit(browser, site, "anonymous", "#/", width)
    type_into(browser, "#pf-email", email)
    type_into(browser, "#pf-pass", PASSWORD)
    tap(browser, "#pf-login")
    assert browser.wait_for("!document.body.classList.contains('gated') && !!document.querySelector('.hero')"), browser.evaluate("document.body.innerText.slice(0, 300)")
    chip = "#account-top .account-chip" if width < 861 else "#account .account-chip"
    assert browser.wait_for(f"(document.querySelector({json.dumps(chip + ' .lb')}) || {{}}).textContent === 'Signed In {width}'")
    assert browser.evaluate("document.cookie") == ""                                                       # the session cookie stays HttpOnly
    assert browser.evaluate(OVERFLOW)["out"] == []
    assert browser.evaluate("document.querySelector('#gate-root')") is None                              # the sign-in screen is gone


def test_a_wrong_password_stays_on_the_sign_in_screen(site, browser):
    account_for(site, "wrongpw@example.com", "Wrong Pw")
    visit(browser, site, "anonymous", "#/plan", 375)
    type_into(browser, "#pf-email", "wrongpw@example.com")
    type_into(browser, "#pf-pass", "not the password")
    tap(browser, "#pf-login")
    assert browser.wait_for("document.querySelector('#pf-msg').textContent.includes('Invalid')")
    assert browser.evaluate(GATE)["gated"] is True


@pytest.mark.parametrize("role,lands", [("learner", "#/"), ("parent", "#/parent")])
def test_creating_an_account_on_the_sign_in_screen_and_signing_out(site, browser, role, lands):
    email = f"new-{role}@example.com"
    visit(browser, site, "anonymous", "#/", 375)
    tap(browser, "#tab-up")
    type_into(browser, "#pf-name", f"New {role.title()}")
    tap(browser, f"label.role-card:has(#pf-role-{role})")
    assert browser.evaluate(f"document.querySelector('#pf-role-{role}').checked")
    type_into(browser, "#pf-email", email)
    type_into(browser, "#pf-pass", PASSWORD)
    tap(browser, "#pf-register")
    assert browser.wait_for("!document.body.classList.contains('gated')")
    assert browser.wait_for(f"[...document.querySelectorAll('#nav a')].some(a => a.getAttribute('href') === '{lands}')")
    with connect(site["db"]) as conn:
        uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
        assert list(users_repo.get_roles(conn, uid)) == [role]
    browser.goto(f"{site['base']}/#/profile", settle=1.2)
    tap(browser, "#pf-logout")
    assert browser.wait_for("document.body.classList.contains('gated') && !!document.querySelector('#gate-root #pf-login')")


def test_the_sign_in_and_create_tabs_work_by_touch_and_keyboard(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    state = "(() => ({mode: document.querySelector('.gate-card').dataset.mode, inSel: document.querySelector('#tab-in').getAttribute('aria-selected'),"\
            " name: !!document.querySelector('#pf-name').offsetParent, heading: document.querySelector('#gate-heading').textContent,"\
            " ac: document.querySelector('#pf-pass').autocomplete}))()"
    assert browser.evaluate(state) == {"mode": "in", "inSel": "true", "name": False, "heading": "Welcome back 👋", "ac": "current-password"}
    tap(browser, "#tab-up")
    assert browser.evaluate(state) == {"mode": "up", "inSel": "false", "name": True, "heading": "Create your account ✨", "ac": "new-password"}
    assert browser.evaluate("document.activeElement.id") == "pf-name"
    browser.evaluate("document.querySelector('#tab-up').focus()")
    browser.call("Input.dispatchKeyEvent", type="keyDown", key="ArrowLeft", code="ArrowLeft", windowsVirtualKeyCode=37)
    browser.call("Input.dispatchKeyEvent", type="keyUp", key="ArrowLeft", code="ArrowLeft", windowsVirtualKeyCode=37)
    time.sleep(0.2)
    assert browser.evaluate(state)["mode"] == "in" and browser.evaluate("document.activeElement.id") == "tab-in"


def test_the_password_can_be_shown_and_hidden(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    type_into(browser, "#pf-pass", "secret-ish")
    look = "(() => { const b = document.querySelector('.pass-toggle'); return [document.querySelector('#pf-pass').type, b.getAttribute('aria-pressed'), b.getAttribute('aria-label')]; })()"
    assert browser.evaluate(look) == ["password", "false", "Show password"]
    tap(browser, ".pass-toggle")
    assert browser.evaluate(look) == ["text", "true", "Hide password"]
    tap(browser, ".pass-toggle")
    assert browser.evaluate(look) == ["password", "false", "Show password"]


def test_an_empty_form_is_explained_without_a_request(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    browser.evaluate("window.__posts = 0; const f = window.fetch; window.fetch = (u, o) => { if (o && o.method === 'POST') window.__posts++; return f(u, o); }")
    tap(browser, "#pf-login")
    assert browser.wait_for("document.querySelector('#pf-msg').textContent === 'Enter your email and password.'")
    assert browser.evaluate("document.querySelector('#pf-msg').classList.contains('bad') && document.querySelector('.gate-card').classList.contains('shake')")
    tap(browser, "#tab-up")
    tap(browser, "#pf-register")
    assert browser.wait_for("document.querySelector('#pf-msg').textContent === 'Enter your name to create an account.'")
    assert browser.evaluate("window.__posts") == 0


@pytest.mark.parametrize("width", PHONES)
def test_the_help_button_never_covers_the_sign_in_form_on_a_phone(site, browser, width):
    """On the phone sign-in screen 🆘 sits in the banner's corner and scrolls with it, so it never covers a field; scrolled past it, the help strip
    right below the form (emergency phrases, 📞 112) is on screen instead. Help is in view at every scroll position."""
    visit(browser, site, "anonymous", "#/", width)
    for y in (0, 150, 300, 450, 600, 10_000):
        browser.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.15)
        r = browser.evaluate("""(() => { const f = document.querySelector('.sos-fab').getBoundingClientRect(), h = document.querySelector('.gate-help').getBoundingClientRect();
            const hit = [...document.querySelectorAll('.gate-card input, .gate-card button')].filter(e => e.offsetParent && e.type !== 'radio')
              .map(e => e.getBoundingClientRect()).filter(c => !(c.right <= f.left || f.right <= c.left || c.bottom <= f.top || f.bottom <= c.top));
            const seen = (b) => b.bottom > 0 && b.top < innerHeight;
            return {overlaps: hit.length, help: seen(f) || seen(h)}; })()""")
        assert r == {"overlaps": 0, "help": True}, (y, r)


def test_motion_stops_for_people_who_ask_for_less(site, browser):
    browser.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
    try:
        visit(browser, site, "anonymous", "#/", 1366)
        assert browser.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") == 0
        assert browser.evaluate("getComputedStyle(document.querySelector('.gate-card')).opacity") == "1"
    finally:
        browser.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    visit(browser, site, "anonymous", "#/", 1366, settle=0.2)
    assert browser.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") > 0       # and it is there otherwise


@pytest.mark.parametrize("role", ["learner", "parent", "admin"])
@pytest.mark.parametrize("width", (375, 1366))
def test_every_account_can_sign_out_from_any_page(site, browser, role, width):
    """A visible Sign out next to the account's name, on phones and desktops, for every kind of account (an admin's console has no profile page,
    so before 15A an admin could not sign out at all). The server ends the session: the old cookie no longer works."""
    email = f"out-{role}-{width}@example.com"
    if role == "admin":
        create_admin(site["db"], email, PASSWORD, "Out Admin")
        with connect(site["db"]) as conn:
            uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
            token, _ = service._start_session(conn, uid, service.utcnow(), mfa_level=1, auth_method="password+totp")
        start = "#/admin/health"
    else:
        _, token = http(site["base"], "POST", "/api/auth/register", {"email": email, "password": PASSWORD, "display_name": f"Out {role}", "role": role})
        start = "#/parent" if role == "parent" else "#/plan"
    site["tokens"]["_out"] = token
    visit(browser, site, "_out", start, width)
    button = ("#account-top" if width < 861 else "#account") + " .account-out"
    r = box(browser, button)
    assert r and r["visible"] and r["y"] >= 0 and r["y"] + r["h"] <= 200 and r["h"] >= 40, r
    assert browser.evaluate(f"document.querySelector({json.dumps(button)}).textContent.trim()") == "Sign out"
    tap(browser, button)
    assert browser.wait_for("document.body.classList.contains('gated') && !!document.querySelector('#gate-root #pf-login')")
    with pytest.raises(urllib.error.HTTPError) as gone:                                                   # the session itself is over
        http(site["base"], "GET", "/api/auth/me", token=token)
    assert gone.value.code == 401


def test_a_new_account_starts_with_its_own_progress_not_the_demo(site, browser):
    account_for(site, "fresh@example.com", "Fresh Face")
    visit(browser, site, "anonymous", "#/", 1366)
    type_into(browser, "#pf-email", "fresh@example.com")
    type_into(browser, "#pf-pass", PASSWORD)
    tap(browser, "#pf-login")
    assert browser.wait_for("!document.body.classList.contains('gated')")
    side = browser.evaluate("document.querySelector('#side-card').innerText")
    assert "0%" in side and "0-day streak" in side and "78%" not in side and "4-day" not in side
    browser.goto(f"{site['base']}/#/tutor", settle=1.0)
    assert browser.wait_for("document.querySelector('#tmsgs') && document.querySelector('#tmsgs').innerText.includes('Namaste Fresh Face')")
    assert "Alex" not in browser.evaluate("document.querySelector('#app').innerText")


# =====================================================================================================================
# laptops and desktops: the sidebar fits, the page is as tall as its content, the content is centred
# =====================================================================================================================
@pytest.mark.parametrize("width,height", [(1024, 768), (1366, 768), (1440, 900), (1920, 1080)])
def test_the_sidebar_scrolls_by_itself_and_never_stretches_the_page(site, browser, width, height):
    for route in ("#/lessons", "#/profile", "#/rewards"):
        visit(browser, site, "adult", route, width, height)
        r = browser.evaluate("""(() => { const sb = document.querySelector('.sidebar'), m = document.querySelector('main');
            const profile = [...document.querySelectorAll('#nav a')].find(a => a.getAttribute('href') === '#/profile');
            sb.scrollTop = sb.scrollHeight; const pr = profile.getBoundingClientRect();
            return {fits: sb.scrollHeight <= sb.clientHeight + 1 || getComputedStyle(sb).overflowY === 'auto', profileVisible: pr.bottom <= innerHeight && pr.top >= 0,
                    doc: document.documentElement.scrollHeight, content: Math.ceil(m.getBoundingClientRect().bottom + scrollY), vh: innerHeight}; })()""")
        assert r["fits"] and r["profileVisible"], (route, r)
        assert r["doc"] <= max(r["vh"], r["content"]) + 1, (route, r)                                     # the page is as tall as its content


@pytest.mark.parametrize("width,who", [(375, "adult"), (1366, "adult"), (375, "parent"), (1366, "parent"), (1366, "admin")])
def test_who_is_signed_in_is_always_in_view(site, browser, width, who):
    visit(browser, site, who, "#/" if who == "adult" else f"#/{who}", width)
    sel = "#account-top .account-chip" if width < 861 else "#account .account-chip"
    r = box(browser, sel)
    assert r and r["visible"] and r["y"] >= 0 and r["y"] + r["h"] <= 200, r
    assert browser.evaluate(f"document.querySelector({json.dumps(sel + ' .lb')}).textContent") in ("Adult Learner", "Parent", "Admin")


@pytest.mark.parametrize("width", (1920, 2560))
def test_content_is_centred_beside_the_sidebar_on_wide_screens(site, browser, width):
    visit(browser, site, "adult", "#/lessons", width, 1200)
    r = browser.evaluate("(() => { const m = document.querySelector('main').getBoundingClientRect(), s = document.querySelector('.sidebar').getBoundingClientRect();"
                         " return {left: m.left - s.right, right: innerWidth - m.right, w: m.width}; })()")
    assert abs(r["left"] - r["right"]) <= 2 and r["left"] > 50, r


# =====================================================================================================================
# voice: the microphone only after a tap
# =====================================================================================================================
def test_the_microphone_is_never_requested_without_a_tap(site, browser):
    script = browser.call("Page.addScriptToEvaluateOnNewDocument", source="""
        window.__mic = 0;
        if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = () => { window.__mic++; return Promise.reject(new DOMException('blocked by the test', 'NotAllowedError')); };""")
    try:
        for route in ("#/voice", "#/speaking", "#/tutor", "#/lesson/1"):
            visit(browser, site, "adult", route, 375)
            assert browser.evaluate("window.__mic") == 0, route
        visit(browser, site, "adult", "#/voice", 375)
        tap(browser, "[data-record]")
        assert browser.wait_for("window.__mic === 1")                                                      # one explicit tap, one request
        time.sleep(0.5)
        assert browser.evaluate("window.__mic") == 1
    finally:
        browser.call("Page.removeScriptToEvaluateOnNewDocument", identifier=script["identifier"])


# =====================================================================================================================
# viewport
# =====================================================================================================================
def test_the_viewport_covers_the_notch(site, browser):
    visit(browser, site, "anonymous", "#/", 375)
    assert "viewport-fit=cover" in browser.evaluate("document.querySelector('meta[name=viewport]').content")
