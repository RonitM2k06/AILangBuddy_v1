// Kids adventure for child learners (#/kids, #/kids/:level). Short levels, big buttons, hearts for lives. Lives, levels and
// answers all live on the server; this page only shows them. Levels, questions and choices are positions (1, 2, 3), never ids.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const root = () => document.getElementById("kids-root");
  const note = (html) => `<div class="card kid-card">${html}</div>`;

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to play</h2><a class="btn btn-primary kid-btn" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>This game is for younger learners</h2><p class="muted">Your account has other lessons to try.</p><a class="btn btn-primary" href="#/">Go home</a>`);
    if (res.status === 409 && res.data && /profile/i.test(String(res.data.detail))) return note(`<h2>Let's set up first!</h2><a class="btn btn-primary kid-btn" href="#/profile">Open my profile</a>`);
    return null;
  }
  const hearts = (l) => `<div class="hearts" aria-label="${l.current} of ${l.max} lives">${"❤️".repeat(l.current)}${"🖤".repeat(l.max - l.current)}</div>`;
  const mins = (s) => (s >= 60 ? Math.ceil(s / 60) + " min" : s + " sec");

  async function mountMap() {
    const el = root(); if (!el) return;
    const res = await api("GET", "/api/kids/adventure");
    if (!alive(el)) return;
    const b = blocked(res);
    if (b) { el.innerHTML = b; return; }
    if (!res.ok) { el.innerHTML = note(`<p>Oops! Try again.</p>`); return; }
    const { lives, levels } = res.data;
    const tiles = levels.map((l) => {
      const inner = `<div class="kid-ic">${l.status === "locked" ? "🔒" : esc(l.icon)}</div><div class="kid-t">Level ${l.number}</div><div>${esc(l.title)}</div>
        <div class="kid-s">${l.status === "completed" ? "⭐ Done!" : l.status === "locked" ? "Locked" : l.done + " / " + l.total}</div>`;
      return l.status === "locked" ? `<div class="kid-tile locked" aria-disabled="true">${inner}</div>` : `<a class="kid-tile ${l.status}" href="#/kids/${l.number}">${inner}</a>`;
    }).join("");
    el.innerHTML = `<div class="kid-head"><h1>My Adventure</h1>${hearts(lives)}</div>
      ${lives.current === 0 ? `<div class="card kid-card">😴 No hearts left. A heart comes back in ${mins(lives.next_life_in_seconds)}.</div>` : ""}
      <div class="kid-grid">${tiles}</div>`;
  }

  async function mountLevel(n) {
    const el = root(); if (!el) return;
    const res = await api("GET", `/api/kids/levels/${encodeURIComponent(n)}`);
    if (!alive(el)) return;
    const b = blocked(res);
    if (b) { el.innerHTML = b; return; }
    if (res.status === 404) { el.innerHTML = note(`<h2>Level not found</h2><a class="btn btn-primary kid-btn" href="#/kids">Back</a>`); return; }
    if (res.status === 409) { el.innerHTML = note(`<h2>🔒 Finish the last level first!</h2><a class="btn btn-primary kid-btn" href="#/kids">Back</a>`); return; }
    if (!res.ok) { el.innerHTML = note(`<p>Oops! Try again.</p>`); return; }
    const level = res.data.level, qs = res.data.questions;
    let lives = res.data.lives, qi = Math.max(0, qs.findIndex((q) => !q.done)), result = null, msg = "", timer = null, audioEl = null, over = null, finished = false;
    const stop = () => { if (timer) { window.clearInterval(timer); timer = null; } };

    const play = (slow) => {
      const src = qs[qi].audio; msg = "";
      if (!src) msg = "No sound for this one.";
      else if (src.kind === "url") { try { if (audioEl) audioEl.pause(); audioEl = new Audio(src.url); audioEl.playbackRate = slow ? 0.75 : 1; const p = audioEl.play(); if (p && p.catch) p.catch(() => { msg = "Couldn't play the sound."; draw(); }); } catch (e) { msg = "Couldn't play the sound."; } }
      else if (window.Engine && window.Engine.canSpeak && window.Engine.hasVoice && !window.Engine.hasVoice(src.locale)) msg = `No voice for this language on this device. Read it instead: ${src.speak_text}${src.speak_fallback_text ? " (" + src.speak_fallback_text + ")" : ""}`;
      else if (window.Engine && window.Engine.canSpeak) window.Engine.speak({ hi: src.speak_text, roman: src.speak_fallback_text }, { slow, locale: src.locale, onerror: () => { msg = "Couldn't play the sound here."; draw(); } });
      else msg = "No sound on this device.";
      draw();
    };

    const startCountdown = (seconds) => {
      stop(); over = { left: seconds };
      timer = window.setInterval(() => { over.left -= 1; if (over.left <= 0) { stop(); over.left = 0; } draw(); }, 1000);
    };

    const draw = () => {
      if (finished) {
        el.innerHTML = `<div class="kid-head"><h1>🎉 Level ${level.number} done!</h1>${hearts(lives)}</div>${note(`<div class="kid-ic">⭐⭐⭐</div>
          <a class="btn btn-primary kid-btn" href="#/kids">${result && result.next_level_unlocked ? "Next level ➜" : "Back to my adventure"}</a>`)}`;
        return;
      }
      if (over) {
        el.innerHTML = `<div class="kid-head"><h1>${esc(level.title)}</h1>${hearts(lives)}</div>${note(`<div class="kid-ic">😴</div><h2>No hearts left</h2>
          <p>${over.left > 0 ? "A heart comes back in " + mins(over.left) + "." : "A heart is back! Tap to play."}</p>
          ${over.left > 0 ? "" : `<button class="btn btn-primary kid-btn" data-retry>▶ Play</button>`}<a class="btn btn-ghost kid-btn" href="#/kids">Back</a>`)}`;
        return;
      }
      const q = qs[qi];
      const choices = q.choices.map((c) => {
        const right = result && c.choice === result.correct_choice;
        return `<button class="btn kid-choice ${right ? "right" : "btn-ghost"}" data-choice="${c.choice}" ${result ? "disabled" : ""}>${esc(c.text)}${c.pronunciation ? `<small>${esc(c.pronunciation)}</small>` : ""}${right ? " ✓" : ""}</button>`;
      }).join("");
      const fb = result ? `<div class="card kid-card ${result.correct ? "kid-ok" : "kid-no"}"><h2>${result.correct ? "🎉 Great job!" : "😮 Oops! Try the next one."}</h2>
        ${result.heard ? `<div class="deva">${esc(result.heard.text)}</div><div class="muted">${esc(result.heard.meaning || "")}</div>` : ""}
        <button class="btn btn-primary kid-btn" data-next>Next ➜</button></div>` : "";
      el.innerHTML = `<div class="kid-head"><a class="back" href="#/kids">⬅</a><h1>${esc(level.title)}</h1>${hearts(lives)}</div>
        <div class="kid-progress">Question ${qi + 1} of ${qs.length}</div>
        <div class="card kid-card"><p class="kid-q">${esc(q.instruction)}</p><button class="btn btn-primary kid-btn" data-play>🔊 Listen</button><button class="btn btn-ghost" data-slow>🐢</button>
          ${msg ? `<div class="muted">${esc(msg)}</div>` : ""}</div><div class="kid-choices">${choices}</div>${fb}`;
    };

    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.play !== undefined) play(false);
      else if (d.slow !== undefined) play(true);
      else if (d.retry !== undefined) { stop(); over = null; mountLevel(n); }
      else if (d.next !== undefined) {
        if (result.level_completed && qs.every((x, i) => x.done || i === qi)) { finished = true; draw(); return; }
        const nxt = qs.findIndex((x, i) => !x.done && i !== qi); result = null;
        if (nxt === -1) { finished = true; } else qi = nxt;
        draw();
      } else if (d.choice) {
        if (result) return;
        const r = await api("POST", `/api/kids/levels/${encodeURIComponent(n)}/answers`, { question: qs[qi].number, choice: +d.choice });
        if (r.status === 409 && r.data && r.data.detail && r.data.detail.next_life_in_seconds !== undefined) {
          lives = { ...lives, current: 0 }; startCountdown(r.data.detail.next_life_in_seconds); draw(); return;
        }
        if (!r.ok) { msg = errText(r); draw(); return; }
        result = r.data; lives = r.data.lives;
        if (r.data.correct) qs[qi].done = true;
        if (r.data.game_over) { startCountdown(r.data.lives.next_life_in_seconds || 0); result = null; }
        draw();
      }
    };
    draw();
  }

  window.KidsView = {
    page(arg) { setTimeout(() => (arg ? mountLevel(arg) : mountMap()), 0); return `<div id="kids-root" class="kids"><div class="card kid-card">Loading…</div></div>`; },
  };
})();
