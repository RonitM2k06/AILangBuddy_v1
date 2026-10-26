// Learner profile page + database-backed language/CEFR catalogue.
// Kept separate from app.js so the prototype's own views are untouched. The profile page and the sign-in screen are the only places that
// talk to the account APIs. Since Phase 15A the app is shown to signed-in accounts only: a visitor gets the sign-in screen (gate) and the
// 🆘 help button, nothing else.
(function () {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (sel, el = document) => el.querySelector(sel);

  // ---------- Catalogue: the database owns it; content.js values remain the offline fallback ----------
  window.CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  fetch("/api/languages").then((r) => r.json()).then((j) => {
    if (j.languages && j.languages.length && window.LANGUAGES) {
      LANGUAGES.splice(0, LANGUAGES.length, ...j.languages.map((l) => ({ code: l.code, name: l.name, native: l.native_name, tts: l.tts_locale })));
    }
  }).catch(() => {});
  fetch("/api/cefr-levels").then((r) => r.json()).then((j) => {
    if (j.levels && j.levels.length) window.CEFR_LEVELS = j.levels.map((l) => l.code);
  }).catch(() => {});

  // ---------- helpers ----------
  // Every write carries the browser-request signal the server requires on all state-changing calls (backend/security/csrf.py):
  // X-Requested-With plus the JSON content type, with or without a body.
  async function api(method, url, body) {
    const opts = { method, headers: {} };
    if (method !== "GET") { opts.headers["Content-Type"] = "application/json"; opts.headers["X-Requested-With"] = "XMLHttpRequest"; }
    if (body) opts.body = JSON.stringify(body);
    let res;
    try { res = await fetch(url, opts); } catch (e) { return { ok: false, status: 0, data: null }; }
    let data = null;
    try { data = await res.json(); } catch (e) {}
    return { ok: res.ok, status: res.status, data };
  }
  function errText(res) {
    if (res.status === 0) return "Can't reach LingoBuddy right now. Check your connection and try again.";   // offline or server down: nothing was saved
    const d = res.data && res.data.detail;
    if (Array.isArray(d)) return d.map((e) => e.msg).join(" · ");
    return typeof d === "string" ? d : "Something went wrong. Please try again.";
  }
  const alive = (root) => document.body.contains(root);
  // The legacy engine keeps one state per identity (engine.js): after signing in or out it must re-check who is signed in.
  // Signing in or out changes the whole app (the sign-in screen, the mode, the navigation): app.js re-reads who is signed in and redraws.
  const reidentify = () => { if (window.A && window.A.identityChanged) return window.A.identityChanged(); if (window.Engine) window.Engine.hydrate(); };

  // ---------- views ----------
  function shell(inner) {
    return `<div class="page-head"><div><div class="eyebrow">⚙️ Profile</div><h1>Your learning profile</h1>
      <p class="sub">Tell us your languages, level and age so lessons can fit you.</p></div></div>${inner}`;
  }

  // ---------- the sign-in screen (Phase 15A) ----------
  // Everyone who is not signed in sees only this (app.js gate()). Left: the brand panel; right: sign in / create an account. The 🆘 help needs
  // no account. Motion comes from styles.css and bits.js and is switched off for prefers-reduced-motion.
  const GATE_PHRASES = [
    { hi: "भैया, कनॉट प्लेस चलोगे?", roman: "Bhaiya, Connaught Place chaloge?", en: "Could you take me to Connaught Place?", tag: "🛺 Transport" },
    { hi: "कम मिर्च, प्लीज़।", roman: "Kam mirch, please.", en: "Less spicy, please.", tag: "🍛 Food" },
    { hi: "मेट्रो स्टेशन कहाँ है?", roman: "Metro station kahan hai?", en: "Where is the metro station?", tag: "📍 Directions" },
  ];
  function gateShell(card) {
    return `<div class="gate2">
      <section class="gate-art">
        <div class="gate-art-inner">
          <div class="gate-brand"><span class="logo" aria-hidden="true">🌍</span><b>LingoBuddy</b></div>
          <h1 class="gate-title">Just moved here?<br>Let's get you talking.</h1>
          <p class="hero-line">Autos, street food, bargaining, metro lines and chai small talk: the stuff you need in your first week.</p>
          <div class="gate-floats" aria-hidden="true">${GATE_PHRASES.map((p, i) => `<div class="float-card gate-float" style="--i:${i}"><small>${esc(p.tag)}</small>
            <div class="deva">${esc(p.hi)}</div><div class="gate-roman">${esc(p.roman)}</div><small>“${esc(p.en)}”</small></div>`).join("")}</div>
          <div class="hero-stats gate-stats"><div><b data-count="7">7</b><span>days to feel at home</span></div><div><b data-count="30">30</b><span>real-life phrases</span></div>
            <div><b data-count="7">7</b><span>AI locals to talk to</span></div></div>
        </div>
      </section>
      <section class="gate-side">${card}
        <div class="gate-help"><div><b>🆘 Need help right now?</b><span>No account needed: play emergency phrases out loud or call for help.</span></div>
          <div class="row"><button type="button" class="btn btn-ghost" onclick="A.sos()">🆘 Emergency phrases</button><a class="btn btn-primary" href="tel:112">📞 Call 112</a></div></div>
      </section>
    </div>`;
  }

  function gateCard(root, notice) {
    root.onclick = null;
    root.innerHTML = gateShell(`<div class="gate-card" data-mode="in">
      <div class="gate-tabs" role="tablist" aria-label="Sign in or create an account">
        <button type="button" role="tab" id="tab-in" data-tab="in" aria-selected="true" aria-controls="gate-form">Sign in</button>
        <button type="button" role="tab" id="tab-up" data-tab="up" aria-selected="false" aria-controls="gate-form" tabindex="-1">Create account</button>
        <span class="gate-tab-ink" aria-hidden="true"></span>
      </div>
      <h2 id="gate-heading">Welcome back 👋</h2>
      <p class="gate-lede" id="gate-lede">Sign in to pick up where you left off.</p>
      <form id="gate-form" class="gate-form" role="tabpanel" aria-labelledby="gate-heading" novalidate>
        <div class="field up-only"><label for="pf-name">Your name</label>
          <input id="pf-name" class="pc-in" type="text" maxlength="60" autocomplete="name" placeholder="e.g. Priya" /></div>
        <div class="field up-only"><span class="field-label" id="role-label">I am…</span>
          <div class="role-pick" role="radiogroup" aria-labelledby="role-label">
            <label class="role-card"><input type="radio" name="pf-role" id="pf-role-learner" value="learner" checked /><span class="role-ic" aria-hidden="true">🎒</span><b>A learner</b><small>Learn the language</small></label>
            <label class="role-card"><input type="radio" name="pf-role" id="pf-role-parent" value="parent" /><span class="role-ic" aria-hidden="true">👪</span><b>A parent</b><small>Follow my child</small></label>
          </div></div>
        <div class="field"><label for="pf-email">Email</label>
          <input id="pf-email" class="pc-in" type="email" autocomplete="email" inputmode="email" placeholder="you@example.com" /></div>
        <div class="field"><label for="pf-pass">Password</label>
          <div class="pass-wrap"><input id="pf-pass" class="pc-in" type="password" autocomplete="current-password" placeholder="Your password" />
            <button type="button" class="pass-toggle" aria-label="Show password" aria-pressed="false">👁</button></div>
          <small class="field-hint up-only">At least 8 characters.</small></div>
        <button class="btn btn-brand btn-lg gate-submit in-only" id="pf-login" type="submit"><span class="lbl">Sign in</span></button>
        <button class="btn btn-brand btn-lg gate-submit up-only" id="pf-register" type="submit"><span class="lbl">Create my account</span></button>
        <div class="gate-msg" id="pf-msg" role="alert">${esc(notice || "")}</div>
      </form>
    </div>`);
    if (window.Bits) window.Bits.enhance(root);
    const card = $(".gate-card", root), form = $("#gate-form", root), msg = $("#pf-msg", root), pass = $("#pf-pass", root);
    const say = (text, bad) => { msg.textContent = text; msg.classList.toggle("bad", !!bad); if (bad) { card.classList.remove("shake"); void card.offsetWidth; card.classList.add("shake"); } };
    const setMode = (m, focus) => {
      card.dataset.mode = m;
      ["in", "up"].forEach((t) => { const b = $(`#tab-${t}`, root); b.setAttribute("aria-selected", String(t === m)); b.tabIndex = t === m ? 0 : -1; });
      $("#gate-heading", root).textContent = m === "in" ? "Welcome back 👋" : "Create your account ✨";
      $("#gate-lede", root).textContent = m === "in" ? "Sign in to pick up where you left off." : "It takes a minute. Your progress will follow you to any device.";
      pass.autocomplete = m === "in" ? "current-password" : "new-password";
      say("");
      if (focus) $(m === "in" ? "#pf-email" : "#pf-name", root).focus();
    };
    $(".gate-tabs", root).addEventListener("click", (e) => { const b = e.target.closest("[data-tab]"); if (b) setMode(b.dataset.tab, true); });
    $(".gate-tabs", root).addEventListener("keydown", (e) => {                 // arrow keys move between the two tabs (WAI-ARIA tabs pattern)
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      const next = card.dataset.mode === "in" ? "up" : "in"; setMode(next, false); $(`#tab-${next}`, root).focus(); e.preventDefault();
    });
    $(".pass-toggle", root).onclick = (e) => {
      const show = pass.type === "password"; pass.type = show ? "text" : "password";
      e.currentTarget.setAttribute("aria-pressed", String(show)); e.currentTarget.setAttribute("aria-label", show ? "Hide password" : "Show password");
      e.currentTarget.textContent = show ? "🙈" : "👁"; pass.focus();
    };
    const busy = (btn, on) => { btn.classList.toggle("is-busy", on); btn.disabled = on; };
    const done = () => { card.classList.add("is-done"); setTimeout(() => { reidentify(); mount(); }, 450); };
    const creds = () => ({ email: $("#pf-email", root).value.trim(), password: pass.value });
    async function signIn() {
      const btn = $("#pf-login", root), c = creds();
      if (!c.email || !c.password) return say("Enter your email and password.", true);
      busy(btn, true); say("Signing in…");
      const res = await api("POST", "/api/auth/login", c);
      busy(btn, false);
      if (res.ok && res.data && res.data.mfa_required && window.TwoFactorView) {      // the password was right; no session until the code
        return window.TwoFactorView.challenge(root, () => { reidentify(); mount(); }, (text) => gateCard(root, text));
      }
      res.ok ? done() : say(errText(res), true);
    }
    async function register() {
      const btn = $("#pf-register", root), name = $("#pf-name", root).value.trim(), c = creds();
      if (!name) return say("Enter your name to create an account.", true);
      if (!c.email || c.password.length < 8) return say("Enter your email and a password of at least 8 characters.", true);
      const role = ($('input[name="pf-role"]:checked', root) || {}).value === "parent" ? "parent" : "learner";   // the server accepts only these two
      busy(btn, true); say("Creating your account…");
      const res = await api("POST", "/api/auth/register", { ...c, display_name: name, role });
      busy(btn, false);
      res.ok ? done() : say(errText(res), true);
    }
    form.onsubmit = (e) => { e.preventDefault(); (card.dataset.mode === "in" ? signIn : register)(); };
  }

  function authCard(root, notice, gate) {
    if (gate) return gateCard(root, notice);
    root.onclick = null;
    const wrap = shell;
    root.innerHTML = wrap(`<div class="card auth-card" style="max-width:480px"><h2>Sign in or create an account</h2>
      <div style="display:grid;gap:10px;margin-top:12px">
        <input id="pf-email" class="pc-in" type="email" placeholder="Email" autocomplete="email" aria-label="Email" />
        <input id="pf-pass" class="pc-in" type="password" placeholder="Password (8+ characters)" autocomplete="current-password" aria-label="Password" />
        <input id="pf-name" class="pc-in" type="text" placeholder="Your name (only for a new account)" maxlength="60" autocomplete="name" aria-label="Your name (only for a new account)" />
        <select id="pf-role" class="pc-in" aria-label="Account type (only for a new account)"><option value="learner">New account: I'm a learner</option><option value="parent">New account: I'm a parent</option></select>
      </div>
      <div class="row" style="margin-top:14px"><button class="btn btn-primary" id="pf-login">Sign in</button>
        <button class="btn btn-ghost" id="pf-register">Create account</button></div>
      <div class="muted" id="pf-msg" style="margin-top:10px;font-size:13.5px">${esc(notice || "")}</div></div>`);
    const msg = $("#pf-msg", root);
    const creds = () => ({ email: $("#pf-email", root).value.trim(), password: $("#pf-pass", root).value });
    $("#pf-login", root).onclick = async () => {
      msg.textContent = "Signing in…";
      const res = await api("POST", "/api/auth/login", creds());
      if (res.ok && res.data && res.data.mfa_required && window.TwoFactorView) {      // the password was right; no session until the code
        return window.TwoFactorView.challenge(root, () => { reidentify(); mount(); }, (text) => authCard(root, text, gate));
      }
      res.ok ? (reidentify(), mount()) : (msg.textContent = errText(res));
    };
    $("#pf-register", root).onclick = async () => {
      const name = $("#pf-name", root).value.trim();
      if (!name) { msg.textContent = "Enter your name to create an account."; return; }
      const role = $("#pf-role", root).value === "parent" ? "parent" : "learner";     // the server only ever accepts these two
      msg.textContent = "Creating account…";
      const res = await api("POST", "/api/auth/register", { ...creds(), display_name: name, role });
      res.ok ? (reidentify(), mount()) : (msg.textContent = errText(res));
    };
  }

  // The age-aware experience follows the account: after signing in or out or saving a profile, re-read the mode and, if it
  // changed, redraw the navigation and page.
  function syncMode() {
    const A = window.AgeMode; if (!A) return;
    const before = A.mode();
    A.refresh().then(() => { if (A.mode() !== before) window.dispatchEvent(new Event("hashchange")); });
  }

  function signOutButton(root) {
    const b = $("#pf-logout", root);
    if (b) b.onclick = async () => { await api("POST", "/api/auth/logout"); reidentify(); mount(); };
  }

  function notLearner(root, user) {
    root.innerHTML = shell(`<div class="card" style="max-width:480px"><h2>Learner profiles only</h2>
      <p class="muted">${esc(user.display_name)} is signed in as ${esc(user.roles.join(", "))}. Profiles are for learner accounts.</p>
      ${user.roles.includes("parent") ? `<a class="btn btn-primary" href="#/parent">Open my children</a> ` : ""}<button class="btn btn-ghost" id="pf-logout">Sign out</button></div>
      <div id="pf-2fa"></div>`);
    signOutButton(root);
    twoFactor(root);
  }

  function twoFactor(root) {
    if (window.TwoFactorView) window.TwoFactorView.mount($("#pf-2fa", root));
  }

  function form(root, user, cat, profile) {
    const opt = (v, label, sel) => `<option value="${esc(v)}" ${sel ? "selected" : ""}>${esc(label)}</option>`;
    const byCode = Object.fromEntries(cat.languages.map((l) => [l.code, l]));
    const levelLabel = Object.fromEntries(cat.levels.map((l) => [l.code, l.label]));
    const targets = cat.combos.map((c) => c.language);
    const nativeSel = profile ? profile.native_language : (byCode.en ? "en" : cat.languages[0].code);
    const targetSel = profile && targets.includes(profile.target_language) ? profile.target_language : targets[0];
    const today = new Date().toISOString().slice(0, 10);
    root.innerHTML = shell(`<div class="card" style="max-width:560px">
      <div class="row between"><b>${esc(user.display_name)}</b><button class="btn btn-ghost btn-sm" id="pf-logout">Sign out</button></div>
      <div style="display:grid;gap:12px;margin-top:14px">
        <label>I speak<br><select id="pf-native" class="pc-in" style="width:100%">${cat.languages.map((l) => opt(l.code, `${l.name} (${l.native_name})`, l.code === nativeSel)).join("")}</select></label>
        <label>I want to learn<br><select id="pf-target" class="pc-in" style="width:100%">${targets.map((c) => opt(c, byCode[c] ? byCode[c].name : c, c === targetSel)).join("")}</select></label>
        <label>My level<br><select id="pf-level" class="pc-in" style="width:100%"></select></label>
        <label>Date of birth<br><input id="pf-dob" class="pc-in" type="date" max="${today}" style="width:100%" value="${esc(profile ? profile.date_of_birth : "")}" /></label>
      </div>
      <div class="row" style="margin-top:16px"><button class="btn btn-primary" id="pf-save">Save profile</button>
        <span id="pf-age">${profile ? ageChip(profile) : ""}</span></div>
      <div class="muted" id="pf-msg" style="margin-top:10px;font-size:13.5px"></div></div>
      <div class="card" style="max-width:560px;margin-top:14px"><b>Share my progress with a parent</b>
        <p class="muted" style="margin:6px 0 10px">Make a one-time code and give it to your parent. They enter it in their own LingoBuddy account. It stops working after 15 minutes or once used.</p>
        <button class="btn btn-ghost" id="pf-parent-code">Make a code</button> <span id="pf-parent-out" style="font-weight:700;letter-spacing:2px"></span></div>
      <div id="pf-2fa"></div>`);
    twoFactor(root);
    $("#pf-parent-code", root).onclick = async () => {
      const out = $("#pf-parent-out", root);
      const r = await api("POST", "/api/profile/parent-link-code");
      out.textContent = r.ok ? r.data.code : errText(r);
    };
    const fillLevels = (keep) => {
      const levels = (cat.combos.find((c) => c.language === $("#pf-target", root).value) || { levels: [] }).levels;
      $("#pf-level", root).innerHTML = levels.map((l) => opt(l, `${l} — ${levelLabel[l] || ""}`, l === keep)).join("");
    };
    fillLevels(profile ? profile.cefr_level : null);
    $("#pf-target", root).onchange = () => fillLevels(null);
    signOutButton(root);
    $("#pf-save", root).onclick = async () => {
      const msg = $("#pf-msg", root);
      const dob = $("#pf-dob", root).value;
      if (!dob) { msg.textContent = "Please enter your date of birth."; return; }
      msg.textContent = "Saving…";
      const res = await api("PUT", "/api/profile", {
        native_language: $("#pf-native", root).value, target_language: $("#pf-target", root).value,
        cefr_level: $("#pf-level", root).value, date_of_birth: dob,
      });
      if (!res.ok) { msg.textContent = errText(res); return; }
      msg.textContent = "Saved ✓";
      syncMode();
      $("#pf-age", root).innerHTML = ageChip(res.data.profile);
    };
  }
  const ageChip = (p) => (p.age_group ? `<span class="chip brand">Age group: ${esc(p.age_group.label)}</span>` : "");

  async function mount() {
    const root = document.getElementById("profile-root");
    if (!root) return;
    root.onclick = null;                                   // a sign-in code step that was showing no longer handles clicks
    const me = await api("GET", "/api/auth/me");
    if (!alive(root)) return;
    syncMode();
    if (!me.ok) return authCard(root);
    const user = me.data.user;
    if (!user.roles.includes("learner")) return notLearner(root, user);
    const [languages, levels, combos, profile] = await Promise.all([
      api("GET", "/api/languages"), api("GET", "/api/cefr-levels"), api("GET", "/api/language-levels"), api("GET", "/api/profile"),
    ]);
    if (!alive(root)) return;
    if (![languages, levels, combos, profile].every((r) => r.ok) || !combos.data.language_levels.length) {
      root.innerHTML = shell(`<div class="card muted">Couldn't load your profile right now. Please try again in a moment.</div>`);
      return;
    }
    form(root, user, { languages: languages.data.languages, levels: levels.data.levels, combos: combos.data.language_levels }, profile.data.profile);
  }

  // A language's name for a learner ("mr" -> "Marathi"): the app's own catalogue name (content.js LANGUAGES: "Bengali", where a browser may
  // say "Bangla"), else the browser's, else the code itself.
  function languageName(code) {
    const own = (window.LANGUAGES || []).find((l) => l.code === code);
    if (own) return own.name;
    try { return new Intl.DisplayNames(["en"], { type: "language" }).of(code) || code; } catch (e) { return code; }
  }
  // How the content of the learner's language has been checked (GET /api/content-review, migration 0034): a plain note on every page that
  // shows that content, unless a native speaker has approved it. Never claims more than the record says. "" when there is nothing to say.
  async function reviewBanner() {
    return "";   // review notices are hidden; GET /api/content-review still reports the status
    const r = await api("GET", "/api/content-review");
    const v = r.ok && r.data && r.data.review;
    if (!v || v.native_review_status === "approved") return "";
    const how = v.editorial_status === "ai_assisted_review" ? "AI-assisted editorial review only" : v.editorial_status === "human_editorial_review" ? "editorial review only" : "not reviewed yet";
    return `<div class="dest-note review-note" role="note" data-content-review>🧪 ${esc(languageName(r.data.language))} content: ${how}; not yet checked by a native speaker`
      + `${v.last_editorial_reviewed_at ? ` (last editorial check ${esc(v.last_editorial_reviewed_at)})` : ""}. ${esc(v.known_limitations || "")}</div>`;
  }
  // Where a phrase can't be heard: the device has no voice for its language. The page then shows the words, said plainly to be text.
  function transcriptHTML(text, roman, locale) {
    return `<div class="card" style="margin-top:12px;border:2px dashed var(--line)" data-transcript role="note"><div class="eyebrow" style="margin:0 0 6px">📝 Transcript mode (text, not audio)</div>
      <div class="muted" style="font-size:13px">This device has no ${esc(languageName(String(locale || "").split(/[-_]/)[0]))} voice, so there is no audio. Read the phrase instead:</div>
      <div class="deva" style="font-weight:700;font-size:22px;margin-top:6px">${esc(text)}</div>${roman ? `<div style="color:var(--brand);font-weight:600">${esc(roman)}</div>` : ""}</div>`;
  }

  window.LBApi = { api, errText, esc, languageName, reviewBanner, transcriptHTML }; // shared with lessons.js and the other pages

  window.ProfileView = {
    // app.js router entry: returns a skeleton synchronously and fills it in once the data arrives.
    page() { setTimeout(mount, 0); return `<div id="profile-root"><div class="card muted">Loading…</div></div>`; },
    gate() {
      setTimeout(() => { const root = document.getElementById("gate-root"); if (root) authCard(root, "", true); }, 0);
      return `<div id="gate-root"><div class="card muted">Loading…</div></div>`;
    },
  };
})();
