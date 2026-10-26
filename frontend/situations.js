// Database-backed situational learning for signed-in learners (#/situations, #/situations/:id).
// Additive: "I'm New Here", the First Week pack and the roleplays are untouched and work without an account.
(function () {
  const { api, errText, esc } = window.LBApi;
  const $ = (sel, el = document) => el.querySelector(sel);
  const alive = (root) => document.body.contains(root);

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🧭 Situations</div><h1>Learn by situation</h1>
    <p class="sub">Real moments, step by step: learn the phrases, then use them.</p></div></div>${inner}`;
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to start a situation</h2><p class="muted">Your progress is saved to your account.</p><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">Situations are for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><p class="muted">Choose the language you want to learn and your level.</p><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }
  const dots = (n) => "●".repeat(n) + "○".repeat(5 - n);
  const chip = (p) => {
    if (p.status === "completed") return `<span class="chip ok">✓ Completed</span>`;
    if (p.status === "in_progress") return `<span class="chip warn">Step ${p.current_step_order} of ${p.steps_total}</span>`;
    return `<span class="chip">Not started</span>`;
  };

  // the review note of the learner's language, shown under the page heading once the list is on the page
  async function addReviewBanner(root) {
    const html = await window.LBApi.reviewBanner();
    const head = html && document.body.contains(root) && root.querySelector(".page-head");
    if (head && !root.querySelector("[data-content-review]")) head.insertAdjacentHTML("afterend", html);
  }

  async function mountList() {
    const root = document.getElementById("situations-root"); if (!root) return;
    const res = await api("GET", "/api/situations");
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load situations. Please try again.</p>`)); return; }
    const list = res.data.situations;
    if (!list.length) {
      root.innerHTML = shell(note(`<h2>No situations for this language and level yet</h2><p class="muted">Your First Week pack still works as before.</p><a class="btn btn-primary" href="#/pack">Open First Week</a>`));
      return;
    }
    addReviewBanner(root);
    root.innerHTML = shell(`<div class="grid g2">${list.map((s) => `<a class="card hover" href="#/situations/${s.id}" style="text-decoration:none;color:inherit">
      <div class="row between"><span style="font-size:26px">${esc(s.topic.icon)}</span><span class="chip brand">${esc(s.cefr_level)}</span></div>
      <h3 style="margin:8px 0 4px">${esc(s.title)}</h3><p class="muted" style="margin:0 0 10px">${esc(s.description)}</p>
      <div class="row between"><span class="muted" style="font-size:13px" title="Difficulty">${dots(s.difficulty)}</span>${chip(s.progress)}</div></a>`).join("")}</div>`);
  }

  const phrase = (v) => `<div class="deva" style="font-weight:700;font-size:22px">${esc(v.text)}</div>
    ${v.pronunciation ? `<div style="color:var(--brand);font-weight:600">${esc(v.pronunciation)}</div>` : ""}
    ${v.meaning ? `<div class="muted">${esc(v.meaning)}</div>` : ""}${v.natural ? `<div class="muted" style="font-size:13px">In natural English: “${esc(v.natural)}”</div>` : ""}`;
  const bubble = (step, partner) => `<div class="card" style="background:var(--surface-2)">
    <div class="muted" style="font-size:13px">${esc(partner || "They say")}</div>
    <div style="font-size:19px;font-weight:700;margin-top:2px">${esc(step.prompt)}</div>
    ${step.prompt_meaning ? `<div class="muted">${esc(step.prompt_meaning)}</div>` : ""}</div>`;
  const inputRow = (label) => `<div class="row" style="margin-top:12px"><input class="pc-in" data-input placeholder="Your answer" aria-label="Your answer" maxlength="500" style="flex:1;min-width:180px" />
    <button class="btn btn-primary btn-sm" data-send>${label}</button></div>`;

  function stepHTML(step, s) {
    const who = s.partner_name ? `${s.partner_name} (${s.partner_role})` : null;
    if (step.kind === "learn_phrase")
      return `<div class="card"><div class="eyebrow" style="margin-bottom:8px">New phrase</div>${phrase(step.item)}<button class="btn btn-primary" style="margin-top:14px" data-learn>Got it →</button></div>`;
    if (step.kind === "choose_response")
      return `${bubble(step, who)}<h3 style="margin:14px 0 8px">What do you say?</h3><div style="display:grid;gap:8px">${step.options.map((o) => `<button class="btn btn-ghost" data-option="${o.id}">${esc(o.text)}</button>`).join("")}</div>`;
    if (step.kind === "conversation")
      return `${bubble(step, who)}<h3 style="margin:14px 0 8px">Your reply</h3>
        <div class="row">${step.suggestions.map((t) => `<button class="chip brand" style="cursor:pointer;border:0" data-suggest="${esc(t)}">${esc(t)}</button>`).join("")}</div>${inputRow("Send")}`;
    return `<div class="card"><b>${esc(step.prompt)}</b>${inputRow("Check")}</div>`;  // translate, fill_blank
  }

  async function mountDetail(id) {
    const root = document.getElementById("situations-root"); if (!root) return;
    const res = await api("GET", `/api/situations/${encodeURIComponent(id)}`);
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (res.status === 404) { root.innerHTML = shell(note(`<h2>Situation not found</h2><a class="btn btn-ghost" href="#/situations">← Situations</a>`)); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load this situation. Please try again.</p>`)); return; }
    const s = res.data.situation;
    let feedback = null;   // result of the last response, shown until the learner continues

    const draw = () => {
      const p = s.progress, done = p.status === "completed";
      const cur = s.steps.find((x) => x.id === p.current_step_id);
      const pct = Math.round((p.steps_completed / p.steps_total) * 100);
      const meta = [s.partner_name && `with ${s.partner_name} (${s.partner_role})`, s.setting].filter(Boolean).join(" · ");
      root.innerHTML = `<a class="back" href="#/situations">← Situations</a>
        <div class="page-head"><div><div class="eyebrow">${esc(s.topic.icon)} ${esc(s.topic.name)} · ${esc(s.cefr_level)}</div><h1>${esc(s.title)}</h1>
          <p class="sub">${esc(s.description)}</p></div><div>${chip(p)}</div></div>
        ${s.goal || meta ? `<div class="card"><b>🎯 Goal:</b> ${esc(s.goal || "")}${meta ? `<div class="muted" style="margin-top:4px">${esc(meta)}</div>` : ""}</div>` : ""}
        <div style="margin:14px 0 6px" class="muted">${p.steps_completed} of ${p.steps_total} steps done</div>
        <div style="height:8px;border-radius:99px;background:var(--line);overflow:hidden"><div style="height:100%;width:${pct}%;background:var(--brand)"></div></div>
        <div style="margin-top:16px">${feedback ? feedbackHTML(feedback, done) : done ? completeHTML() : cur ? stepHTML(cur, s) : ""}</div>`;
    };
    const feedbackHTML = (f, done) => `<div class="feedback"><b>${f.correct ? "✅ Nice!" : "❌ Not quite."}</b>
      ${!f.correct && f.correct_answers.length ? `<div class="muted" style="margin-top:4px">Try: ${f.correct_answers.map(esc).join(" · ")}</div>` : ""}
      ${f.explanation ? `<div class="muted" style="margin-top:4px">${esc(f.explanation)}</div>` : ""}
      <button class="btn ${f.correct ? "btn-primary" : "btn-ghost"}" style="margin-top:10px" data-continue>${f.correct ? (done ? "Finish" : "Continue →") : "Try again"}</button></div>`;
    const completeHTML = () => `<div class="card" style="text-align:center;padding:30px"><div style="font-size:44px">🎉</div><h2>Situation complete!</h2>
      <p class="muted">You finished “${esc(s.title)}”.</p><a class="btn btn-primary" href="#/situations">More situations</a></div>`;

    const submit = async (body) => {
      const cur = s.steps.find((x) => x.id === s.progress.current_step_id);
      const r = await api("POST", `/api/situations/${s.id}/steps/${cur.id}/responses`, body);
      if (!r.ok) { feedback = { correct: false, correct_answers: [], explanation: errText(r) }; draw(); return; }
      const { progress, ...result } = r.data;
      s.progress = { ...s.progress, ...progress };
      feedback = cur.kind === "learn_phrase" && result.correct ? null : result;  // acknowledging a phrase just moves on
      draw();
    };
    root.onclick = (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      if (t.dataset.continue !== undefined) { feedback = null; draw(); }
      else if (t.dataset.learn !== undefined) submit({});
      else if (t.dataset.option) submit({ answer_id: +t.dataset.option });
      else if (t.dataset.suggest) submit({ text: t.dataset.suggest });
      else if (t.dataset.send !== undefined) submit({ text: $("[data-input]", root).value });
    };
    root.onkeydown = (ev) => { if (ev.key === "Enter" && ev.target.dataset && ev.target.dataset.input !== undefined) submit({ text: ev.target.value }); };
    draw();
  }

  window.SituationsView = {
    page(arg) { setTimeout(() => (arg ? mountDetail(arg) : mountList()), 0); return `<div id="situations-root"><div class="card muted">Loading…</div></div>`; },
  };
})();
