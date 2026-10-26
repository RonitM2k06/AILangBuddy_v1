// Listening activities for signed-in learners (#/listening, #/listening/:id). The audio comes from a stored file when the
// server has one, otherwise from the browser's speech synthesis (the prototype's Engine.speak). The spoken text is never
// shown, only played. Additive: the prototype's own Learn > Listening quiz is untouched.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🎧 Listening</div><h1>Listen and choose</h1>
    <p class="sub">Play the audio, then pick what you heard. Replay as often as you like.</p></div></div>${inner}`;
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to practise listening</h2><p class="muted">Your progress is saved to your account.</p><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">Listening practice is for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><p class="muted">Choose the language you want to learn and your level.</p><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }
  const dots = (n) => "●".repeat(n) + "○".repeat(3 - n);
  const chip = (p) => (p.status === "completed" ? `<span class="chip ok">✓ Got it</span>` : p.status === "attempted" ? `<span class="chip warn">Keep trying</span>` : `<span class="chip">New</span>`);
  const modeLabel = (m) => (m === "choose_meaning" ? "Meaning" : "Phrase");

  // the review note of the learner's language, shown under the page heading once the list is on the page
  async function addReviewBanner(root) {
    const html = await window.LBApi.reviewBanner();
    const head = html && document.body.contains(root) && root.querySelector(".page-head");
    if (head && !root.querySelector("[data-content-review]")) head.insertAdjacentHTML("afterend", html);
  }

  async function mountList() {
    const root = document.getElementById("listening-root"); if (!root) return;
    const [res, prog] = await Promise.all([api("GET", "/api/listening"), api("GET", "/api/listening/progress")]);
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load listening activities. Please try again.</p>`)); return; }
    const list = res.data.activities;
    if (!list.length) {
      root.innerHTML = shell(note(`<h2>No listening activities for this language and level yet</h2><p class="muted">The rest of LingoBuddy works as before.</p><a class="btn btn-primary" href="#/pack">Open First Week</a>`));
      return;
    }
    const p = prog.ok ? prog.data.progress : null;
    const summary = p ? `<div class="card" style="margin-bottom:14px"><b>${p.activities_completed} of ${p.activities_total} completed</b>
        <span class="muted"> · ${p.attempts} answers${p.accuracy === null ? "" : " · " + Math.round(p.accuracy * 100) + "% correct"}</span></div>` : "";
    addReviewBanner(root);
    root.innerHTML = shell(`${summary}<div class="grid g2">${list.map((a) => `<a class="card hover" href="#/listening/${a.id}" style="text-decoration:none;color:inherit">
      <div class="row between"><span style="font-size:26px">${esc(a.topic.icon)}</span><span class="chip brand">${modeLabel(a.mode)}</span></div>
      <h3 style="margin:8px 0 4px">${esc(a.title)}</h3><p class="muted" style="margin:0 0 10px">${esc(a.prompt)}</p>
      <div class="row between"><span class="muted" style="font-size:13px" title="Difficulty">${dots(a.difficulty)}</span>${chip(a.progress)}</div></a>`).join("")}</div>`);
  }

  async function mountDetail(id) {
    const root = document.getElementById("listening-root"); if (!root) return;
    const [res, all] = await Promise.all([api("GET", `/api/listening/${encodeURIComponent(id)}`), api("GET", "/api/listening")]);
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (res.status === 404) { root.innerHTML = shell(note(`<h2>Activity not found</h2><a class="btn btn-ghost" href="#/listening">← Listening</a>`)); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load this activity. Please try again.</p>`)); return; }
    const a = res.data.activity;
    const order = all.ok ? all.data.activities.map((x) => x.id) : [];
    const nextId = order[order.indexOf(a.id) + 1];
    let plays = 0, firstPlayAt = null, result = null, msg = "", audioEl = null, transcript = false;

    const play = (slow) => {
      plays += 1; if (firstPlayAt === null) firstPlayAt = Date.now();
      msg = "";
      const src = a.audio;
      if (!src) msg = "No audio is available for this activity.";
      else if (src.kind === "url") {
        try { if (audioEl) audioEl.pause(); audioEl = new Audio(src.url); audioEl.playbackRate = slow ? 0.75 : 1; const p = audioEl.play(); if (p && p.catch) p.catch(() => { msg = "Couldn't play the audio file."; draw(); }); }
        catch (e) { msg = "Couldn't play the audio file."; }
      } else if (window.Engine && window.Engine.canSpeak && window.Engine.hasVoice && !window.Engine.hasVoice(src.locale)) {
        transcript = true;                                         // no voice for this language: the words, clearly as text
      } else if (window.Engine && window.Engine.canSpeak) {
        window.Engine.speak({ hi: src.speak_text, roman: src.speak_fallback_text }, { slow, locale: src.locale, onerror: () => { msg = "Couldn't play audio here."; draw(); } });
      } else msg = "Audio playback isn't available in this browser.";
      draw();
    };

    const draw = () => {
      const p = result ? result.progress : a.progress;
      const opts = a.options.map((o) => {
        const isRight = result && o.id === result.correct_option_id;
        const cls = result ? (isRight ? "btn-primary" : "btn-ghost") : "btn-ghost";
        return `<button class="btn ${cls}" data-option="${o.id}" ${result ? "disabled" : ""}>${esc(o.text)}${o.pronunciation ? ` <span class="muted">· ${esc(o.pronunciation)}</span>` : ""}${isRight ? " ✓" : ""}</button>`;
      }).join("");
      const feedback = result ? `<div class="feedback" style="margin-top:12px"><b>${result.correct ? "✅ Correct!" : "❌ Not quite."}</b>
        <div style="margin-top:6px"><span class="deva" style="font-weight:700">${esc(result.heard.text)}</span><div style="color:var(--brand);font-weight:600">${esc(result.heard.pronunciation || "")}</div>
        <div class="muted">${esc(result.heard.meaning || "")}</div></div>
        <div class="row" style="margin-top:10px"><button class="btn btn-ghost btn-sm" data-again>↺ Try again</button>
          ${nextId ? `<a class="btn btn-primary btn-sm" href="#/listening/${nextId}">Next →</a>` : `<a class="btn btn-primary btn-sm" href="#/listening">Back to listening</a>`}</div></div>` : "";
      root.innerHTML = `<a class="back" href="#/listening">← Listening</a>
        <div class="page-head"><div><div class="eyebrow">${esc(a.topic.icon)} ${esc(a.topic.name)} · ${modeLabel(a.mode)}</div><h1>${esc(a.title)}</h1><p class="sub">${esc(a.prompt)}</p></div><div>${chip(p)}</div></div>
        <div class="card" style="text-align:center;padding:26px"><div class="row" style="justify-content:center">
          <button class="btn btn-primary btn-lg" data-play>${plays ? "🔁 Replay" : "▶ Play"}</button><button class="btn btn-ghost" data-slow>🐢 Slow</button></div>
          <div class="muted" style="margin-top:8px;font-size:13px">${plays ? "Played " + plays + (plays === 1 ? " time" : " times") : "Press play to listen"}</div>
          ${msg ? `<div class="muted" style="margin-top:6px">${esc(msg)}</div>` : ""}</div>
        ${transcript && a.audio ? window.LBApi.transcriptHTML(a.audio.speak_text, a.audio.speak_fallback_text, a.audio.locale) : ""}
        <div style="display:grid;gap:8px;margin-top:14px">${opts}</div>${feedback}`;
    };

    root.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.play !== undefined) play(false);
      else if (d.slow !== undefined) play(true);
      else if (d.again !== undefined) { result = null; plays = 0; firstPlayAt = null; msg = ""; transcript = false; draw(); }
      else if (d.option) {
        if (result) return;
        const body = { option_id: +d.option, plays: Math.min(plays, 99) };
        if (firstPlayAt !== null) body.response_ms = Math.min(Date.now() - firstPlayAt, 3600000);
        const r = await api("POST", `/api/listening/${a.id}/attempts`, body);
        if (!r.ok) { msg = errText(r); draw(); return; }
        result = r.data; draw();
      }
    };
    draw();
  }

  window.ListeningView = {
    page(arg) { setTimeout(() => (arg ? mountDetail(arg) : mountList()), 0); return `<div id="listening-root"><div class="card muted">Loading…</div></div>`; },
  };
})();
