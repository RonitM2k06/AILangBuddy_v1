// Adaptive learning (#/ai-insights): today's plan ranked from your own records, suggestions, insights and practice drills. Everything here is derived
// from what you have actually done and stored; the page never shows a number the server did not compute, says "not enough evidence" when there is
// none, and labels generated wording. Nothing on this page awards XP or changes your level.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🧠 Adaptive learning</div><h1>Your next steps</h1>
    <p class="sub">Suggestions and insights come only from your own learning records. Generated wording is labelled.</p></div></div>${inner}`;
  const why = (ev) => (ev && ev.length ? `<div class="muted" style="font-size:12.5px;margin-top:4px"><b>Why:</b> ${ev.map((e) => esc(e.text)).join(" ")}</div>` : "");

  async function mount() {
    const el = document.getElementById("adaptive-root"); if (!el) return;
    const [plan, recs, ins, micro] = await Promise.all([api("GET", "/api/ai/adaptive-plan"), api("GET", "/api/ai/recommendations"), api("GET", "/api/ai/insights"), api("GET", "/api/ai/micro-lessons")]);
    if (!alive(el)) return;
    const first = [plan, recs].find((r) => !r.ok);
    if (first) {
      if (first.status === 401) el.innerHTML = shell(note(`<h2>Sign in to see your next steps</h2><a class="btn btn-primary" href="#/profile">Sign in</a>`));
      else if (first.status === 403) el.innerHTML = shell(note(`<h2>Learner accounts only</h2>`));
      else if (first.status === 409) el.innerHTML = shell(note(`<h2>Set up your profile first</h2><a class="btn btn-primary" href="#/profile">Open profile</a>`));
      else el.innerHTML = shell(note(`<p class="muted">Couldn't load this page. Please try again.</p>`));
      return;
    }
    let state = { plan: plan.data, recs: recs.data, ins: ins.ok ? ins.data : null, micro: micro.ok ? micro.data.micro_lessons : [] }, msg = "", results = {};

    const draw = () => {
      const p = state.plan, r = state.recs, i = state.ins;
      el.innerHTML = shell(`
        <h3>Today's plan, in order <span class="chip">${p.source === "llm" ? "ranked by an AI model" : "ranked by your records"}</span></h3>
        ${p.items.length ? p.items.map((x) => `<div class="card" style="margin-bottom:8px"><b>${x.rank}. ${esc(x.title)}</b> ${x.in_phase6_plan ? `<span class="chip ok">in today's plan${x.status === "done" ? " · done" : ""}</span>` : ""}
          <div>${esc(x.reason)}</div>${x.ai_note ? `<div class="muted" style="font-size:13px">${esc(x.ai_note)}</div>` : ""}</div>`).join("") : `<div class="muted">Not enough evidence yet to rank anything. Keep practising and this will fill in.</div>`}
        <h3 style="margin-top:16px">Suggestions for you</h3><div class="muted" id="ad-msg">${esc(msg)}</div>
        ${r.recommendations.length ? r.recommendations.map((x) => `<div class="card" style="margin-bottom:8px"><div class="row between"><b>${esc(x.title)}</b>
          <span class="chip">${esc(x.kind.replace(/_/g, " "))}</span></div><div>${esc(x.reason)}</div>${why(x.evidence)}
          <div style="margin-top:6px">${x.status === "applied" ? `<span class="chip ok">Taken ✓</span>` : `<button class="btn btn-primary btn-sm" data-apply="${x.id}">Take this suggestion</button>`}</div></div>`).join("")
          : `<div class="muted">${esc(r.message || "Not enough evidence yet.")}</div>`}
        <h3 style="margin-top:16px">What your records show</h3>
        ${i && i.insights.length ? i.insights.map((x) => `<div class="card" style="margin-bottom:8px"><div>${esc(x.text)}</div>${why(x.evidence)}</div>`).join("") : `<div class="muted">${esc(i ? i.message : "Not enough evidence yet to say anything about your progress.")}</div>`}
        <h3 style="margin-top:16px">Practice drills made for you</h3><div class="muted" style="font-size:13px">Extra practice, not part of your lessons. Answering them earns no XP.</div>
        ${state.micro.length ? state.micro.map((m) => drill(m)).join("") : `<div class="muted">No drills right now. They appear when something in your records suggests one.</div>`}`);
    };

    const drill = (m) => {
      const res = results[m.id];
      const answers = m.answer_mode === "text"
        ? `<div class="row" style="margin-top:6px;flex-wrap:nowrap"><input id="ad-text-${m.id}" class="pc-in" style="flex:1" maxlength="500" placeholder="Your answer…" /><button class="btn btn-primary btn-sm" data-text="${m.id}">Check</button></div>`
        : `<div class="row" style="margin-top:6px">${m.options.map((o) => `<button class="btn btn-ghost btn-sm" data-drill="${m.id}" data-choice="${o.choice}">${esc(o.text)}</button>`).join("")}</div>`;
      return `<div class="card" style="margin-bottom:8px"><div class="muted" style="font-size:12px">${esc(m.label)}${m.topic ? " · " + esc(m.topic.name) : ""}</div><b>${esc(m.question)}</b>${answers}
        ${res ? `<div style="margin-top:6px"><span class="chip ${res.correct ? "ok" : "warn"}">${res.correct ? "Correct ✓" : "Not quite"}</span> <span class="muted">Answer: ${esc(res.correct_answer)}</span></div>` : ""}${why(m.evidence)}</div>`;
    };

    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.apply) {
        const r = await api("POST", `/api/ai/recommendations/${encodeURIComponent(d.apply)}/apply`);
        msg = r.ok ? "Noted. Open it from the menu or here: " + r.data.go_to : errText(r);
        const fresh = await api("GET", "/api/ai/recommendations"); if (fresh.ok) state.recs = fresh.data;
      } else if (d.drill) {
        const r = await api("POST", `/api/ai/micro-lessons/${encodeURIComponent(d.drill)}/answer`, { choice: +d.choice });
        if (r.ok) results[d.drill] = r.data; else msg = errText(r);
      } else if (d.text) {
        const text = el.querySelector(`#ad-text-${d.text}`).value.trim();
        if (!text) { msg = "Type your answer first."; draw(); return; }
        const r = await api("POST", `/api/ai/micro-lessons/${encodeURIComponent(d.text)}/answer`, { text });
        if (r.ok) results[d.text] = r.data; else msg = errText(r);
      } else return;
      draw();
    };
    draw();
  }

  window.AdaptiveView = { page() { setTimeout(mount, 0); return `<div id="adaptive-root"><div class="card muted">Loading…</div></div>`; } };
})();
