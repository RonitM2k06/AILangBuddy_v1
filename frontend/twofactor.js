// Two-factor authentication (Phase 14D): the sign-in code step, and the setup / recovery-code / turn-off card used by the profile page
// and by the admin console's mandatory enrollment. The server decides everything; this only presents it. Nothing here is stored in the
// browser: the setup key and recovery codes live in the page only while they are shown, and are never logged.
(function () {
  const { api, errText, esc } = window.LBApi;
  const msgOf = (res, fallback) => (res && res.data && typeof res.data.detail === "string" ? res.data.detail : fallback || errText(res));
  const box = (inner, state) => `<div class="card tf-card" data-state="${state}" style="max-width:560px;margin-top:14px"><b>🔐 Two-factor authentication</b>${inner}</div>`;
  const value = (el, sel) => { const f = el.querySelector(sel); return f ? String(f.value || "").trim() : ""; };

  // The QR code arrives as a matrix of "0"/"1" rows. Only digits and numbers go into the SVG, so nothing in it can be markup.
  function qrSvg(qr) {
    if (!qr || !Number.isInteger(qr.size) || !Array.isArray(qr.modules) || qr.modules.length !== qr.size
      || !qr.modules.every((r) => typeof r === "string" && r.length === qr.size && /^[01]+$/.test(r))) return "";
    const quiet = 4, n = qr.size + 2 * quiet;
    let d = "";
    qr.modules.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (row[x] === "1") d += `M${x + quiet} ${y + quiet}h1v1h-1z`; });
    return `<svg class="tf-qr" viewBox="0 0 ${n} ${n}" width="200" height="200" role="img" aria-label="QR code for your authenticator app" shape-rendering="crispEdges"><rect width="${n}" height="${n}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
  }
  const groups = (key) => key.replace(/(.{4})/g, "$1 ").trim();
  const codesList = (codes) => `<div class="tf-codes" data-state="codes" style="margin-top:12px"><b>Your recovery codes</b>
    <p class="muted">Each one works once, if you lose your authenticator. Save them somewhere safe now: they are not shown again after you leave this page.</p>
    <ol class="tf-code-list">${codes.map((c) => `<li><code>${esc(c)}</code></li>`).join("")}</ol>
    <button class="btn btn-primary" data-act="saved">I have saved them</button></div>`;

  // ---------- the card ----------
  async function mount(el, opts = {}) {
    if (!el) return;
    let shownCodes = null;
    const res = await api("GET", "/api/auth/2fa");
    if (!res.ok) { el.innerHTML = ""; return; }
    const s = res.data;
    const msg = (text) => { const m = el.querySelector("#tf-msg"); if (m) m.textContent = text; };

    function drawOff() {
      el.innerHTML = box(s.available
        ? `<p class="muted">${s.required ? "Administrators must use it. " : ""}Protect your account with a code from an authenticator app as well as your password.</p>
           <input id="tf-password" class="pc-in" type="password" autocomplete="current-password" placeholder="Your password" />
           <div class="row" style="margin-top:10px"><button class="btn btn-primary" data-act="setup">Set up two-factor authentication</button></div>
           <div class="muted" id="tf-msg" style="margin-top:8px"></div>`
        : `<p class="muted">Two-factor authentication is not available on this server yet.</p>`, "off");
    }
    function drawSetup(setup) {
      el.innerHTML = box(`<p class="muted">1. Scan this code with an authenticator app, or type the key by hand.</p>
        <div class="tf-qr-wrap">${qrSvg(setup.qr) || `<p class="muted">The picture could not be drawn: type the key below instead.</p>`}</div>
        <p style="margin:8px 0 2px">Setup key:</p><code id="tf-key" class="tf-key">${esc(groups(setup.secret))}</code>
        <div class="row" style="margin-top:6px"><button class="btn btn-ghost btn-sm" data-act="copy">Copy key</button></div>
        <p class="muted" style="margin-top:10px">2. Type the 6-digit code the app shows. This setup expires in ${Math.round(setup.expires_in_seconds / 60)} minutes.</p>
        <input id="tf-code" class="pc-in" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="123456" />
        <div class="row" style="margin-top:10px"><button class="btn btn-primary" data-act="confirm">Turn on</button><button class="btn btn-ghost" data-act="cancel">Cancel</button></div>
        <div class="muted" id="tf-msg" style="margin-top:8px"></div>`, "setup");
      el._key = setup.secret;                               // only for the Copy button; gone when the card is redrawn
    }
    function drawOn() {
      el.innerHTML = box(`<p><span class="chip ok">On</span> ${s.recovery_codes_remaining} recovery code${s.recovery_codes_remaining === 1 ? "" : "s"} left.</p>
        ${opts.adminGate && !s.session_mfa ? `<p class="muted">This session was started without your code. Sign out and sign in again with your code to use the admin console.</p>` : ""}
        ${shownCodes ? codesList(shownCodes) : ""}
        <details style="margin-top:10px"><summary>New recovery codes</summary>
          <p class="muted">Your old codes stop working.</p>
          <input id="tf-regen-password" class="pc-in" type="password" autocomplete="current-password" placeholder="Your password" />
          <input id="tf-regen-code" class="pc-in" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="Code from your app" style="margin-top:6px" />
          <div class="row" style="margin-top:8px"><button class="btn btn-ghost" data-act="regenerate">Make new codes</button></div></details>
        ${s.required ? `<p class="muted" style="margin-top:10px">Administrators cannot turn two-factor authentication off.</p>`
          : `<details style="margin-top:10px"><summary>Turn off</summary>
          <input id="tf-off-password" class="pc-in" type="password" autocomplete="current-password" placeholder="Your password" />
          <input id="tf-off-code" class="pc-in" autocomplete="one-time-code" maxlength="19" placeholder="Code from your app, or a recovery code" style="margin-top:6px" />
          <div class="row" style="margin-top:8px"><button class="btn btn-ghost" data-act="disable">Turn off two-factor authentication</button></div></details>`}
        <div class="muted" id="tf-msg" style="margin-top:8px"></div>`, "on");
    }
    const redraw = () => (s.enabled ? drawOn() : drawOff());

    el.onclick = async (ev) => {
      const t = ev.target && ev.target.closest && ev.target.closest("[data-act]");
      if (!t) return;
      const act = t.dataset.act;
      if (act === "setup") {
        msg("Starting…");
        const r = await api("POST", "/api/auth/2fa/setup", { password: value(el, "#tf-password") });
        if (!r.ok) return msg(r.status === 403 ? "That password is not correct." : msgOf(r));
        drawSetup(r.data);
      } else if (act === "copy") {
        try { await window.navigator.clipboard.writeText(el._key); msg("Copied."); } catch (e) { msg("Select the key and copy it."); }
      } else if (act === "cancel") {
        el._key = null; drawOff();
      } else if (act === "confirm") {
        const r = await api("POST", "/api/auth/2fa/confirm", { code: value(el, "#tf-code") });
        if (!r.ok) return msg(r.status === 403 ? "That code is not correct. Check the time on your phone and try again." : msgOf(r));
        el._key = null; s.enabled = true; s.session_mfa = true; s.recovery_codes_remaining = r.data.recovery_codes.length; shownCodes = r.data.recovery_codes;
        drawOn();
      } else if (act === "saved") {
        shownCodes = null; drawOn();
        if (opts.onEnabled) opts.onEnabled();
      } else if (act === "regenerate") {
        const r = await api("POST", "/api/auth/2fa/recovery-codes", { password: value(el, "#tf-regen-password"), code: value(el, "#tf-regen-code") });
        if (!r.ok) return msg(r.status === 403 ? "The password or the code is not correct." : msgOf(r));
        shownCodes = r.data.recovery_codes; s.recovery_codes_remaining = shownCodes.length; drawOn();
      } else if (act === "disable") {
        const factor = value(el, "#tf-off-code"), body = { password: value(el, "#tf-off-password") };
        if (/^[0-9]{6}$/.test(factor)) body.code = factor; else body.recovery_code = factor;
        const r = await api("POST", "/api/auth/2fa/disable", body);
        if (!r.ok) { const d = msgOf(r, ""); return msg(d === "That is not correct" ? "The password or the code is not correct." : d || errText(r)); }
        s.enabled = false; s.recovery_codes_remaining = 0; drawOff(); msg("Two-factor authentication is off. Your other devices were signed out.");
      }
    };
    redraw();
  }

  // ---------- the second step of signing in ----------
  function challenge(root, onSignedIn, onRestart) {
    let recovery = false;
    const draw = (text) => {
      root.innerHTML = `<div class="card" data-state="mfa-challenge" style="max-width:480px"><h2>Enter your code</h2>
        <p class="muted">${recovery ? "Type one of your recovery codes. Each works once." : "Open your authenticator app and type the 6-digit code for LingoBuddy."}</p>
        ${recovery ? `<input id="tf-recovery" class="pc-in" type="text" autocomplete="off" maxlength="19" placeholder="XXXX-XXXX-XXXX-XXXX" />`
                   : `<input id="tf-login-code" class="pc-in" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="123456" />`}
        <div class="row" style="margin-top:12px"><button class="btn btn-primary" data-act="verify">Verify</button>
          <button class="btn btn-ghost" data-act="toggle">${recovery ? "Use my authenticator app" : "Use a recovery code"}</button>
          <button class="btn btn-ghost" data-act="restart">Start over</button></div>
        <div class="muted" id="tf-msg" style="margin-top:10px">${esc(text || "")}</div></div>`;
    };
    draw();
    root.onclick = async (ev) => {
      const t = ev.target && ev.target.closest && ev.target.closest("[data-act]");
      if (!t) return;
      if (t.dataset.act === "toggle") { recovery = !recovery; return draw(); }
      if (t.dataset.act === "restart") { root.onclick = null; return onRestart(); }
      if (t.dataset.act !== "verify") return;
      const body = recovery ? { recovery_code: value(root, "#tf-recovery") } : { code: value(root, "#tf-login-code") };
      const r = await api("POST", "/api/auth/2fa/verify", body);
      if (r.ok) { root.onclick = null; return onSignedIn(r.data.user); }
      if (r.status === 401 && /expired/.test(msgOf(r, ""))) { root.onclick = null; return onRestart("Your sign-in expired. Please sign in again."); }
      draw(r.status === 429 ? "Too many wrong codes. Wait a few minutes and try again." : (recovery ? "That recovery code did not work." : "That code is not correct."));
    };
  }

  window.TwoFactorView = { mount, challenge, qrSvg };
})();
