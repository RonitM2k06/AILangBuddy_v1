// Personalisation for signed-in learners (#/plan): today's plan, the recommended next activity, areas to improve
// and confidence. Additive: the prototype's own Confidence page (#/confidence) is untouched.
(function () {
  const { api, errText, esc } = window.LBApi;
  const $ = (sel, el = document) => el.querySelector(sel);
  const alive = (root) => document.body.contains(root);

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🎯 My Plan</div><h1>Your personal plan</h1>
    <p class="sub">Built from what you've actually practised and how confident you feel.</p></div></div>${inner}`;
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to see your plan</h2><p class="muted">Your plan is built from your own progress.</p><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">Plans are for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><p class="muted">Choose the language you want to learn and your level.</p><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }
  const link = (t) => (t.type === "lesson" ? `#/lessons/${t.id}` : t.type === "situation" ? `#/situations/${t.id}` : null);
  const pct = (v) => (v === null || v === undefined ? "–" : Math.round(v * 100) + "%");
  const sevChip = (s) => `<span class="chip ${s === "high" ? "heart" : s === "medium" ? "warn" : ""}">${esc(s)}</span>`;

  const slider = (attr, value) => `<div class="row" style="flex-wrap:nowrap;gap:8px"><input type="range" min="0" max="100" step="5" value="${value}" ${attr} style="flex:1;min-width:110px" />
    <output style="width:36px;text-align:right">${value}</output></div>`;

  function taskHTML(t) {
    const done = t.status === "done", skipped = t.status === "skipped";
    const go = link(t.target);
    const body = t.target.type === "topic"
      ? `<div class="muted" style="font-size:13px;margin-top:6px">How confident do you feel about ${esc(t.target.title)}?</div>
         <div class="row" style="margin-top:6px">${slider(`data-task-conf="${t.id}"`, 50)}<button class="btn btn-primary btn-sm" data-task-save="${t.id}:${esc(t.target.slug)}">Save</button></div>`
      : "";
    return `<div class="card" style="margin-top:10px;${done || skipped ? "opacity:.65" : ""}">
      <div class="row between"><b>${done ? "✅" : skipped ? "⏭️" : "⬜"} ${t.priority}. ${esc(t.target.title)}</b>
        <span class="chip">${esc(t.task_type.replace("_", " "))}</span></div>
      <div class="muted" style="font-size:13.5px">${esc(t.why)}</div>${t.status === "pending" ? body : ""}
      <div class="row" style="margin-top:8px">${go && t.status === "pending" ? `<a class="btn btn-primary btn-sm" href="${go}">Start →</a>` : ""}
        ${t.status === "pending" ? `<button class="btn btn-ghost btn-sm" data-status="${t.id}:done">Mark done</button><button class="btn btn-ghost btn-sm" data-status="${t.id}:skipped">Skip</button>`
          : `<button class="btn btn-ghost btn-sm" data-status="${t.id}:pending">Undo</button>`}</div></div>`;
  }

  function draw(root, d) {
    const { plan, recs, weak, conf } = d;
    const next = recs.next_activity;
    const nextHTML = next
      ? `<div class="card"><div class="eyebrow" style="margin-bottom:6px">Recommended next</div><h3 style="margin:0 0 4px">${esc(next.target.title)}</h3>
           <p class="muted" style="margin:0 0 10px">${esc(next.reason)}</p>
           <div class="row">${link(next.target) ? `<a class="btn btn-primary" href="${link(next.target)}">Go →</a>` : ""}
           <span class="chip brand" title="${esc(recs.difficulty.reason)}">Suggested exercise level: ${esc(recs.difficulty.label)}</span></div></div>`
      : `<div class="card muted">Nothing to recommend yet for your language and level.</div>`;
    const weakHTML = weak.length
      ? weak.map((w) => `<div class="row between" style="padding:10px 0;border-top:1px solid var(--line)"><div><b>${esc(w.topic ? w.topic.icon + " " + w.topic.name : "“" + (w.item.pronunciation || w.item.text) + "”")}</b>
          <div class="muted" style="font-size:13.5px">${esc(w.explanation)}</div></div>${sevChip(w.severity)}</div>`).join("")
      : `<p class="muted" style="margin:0">Nothing flagged. Areas to improve show up here once you've practised enough for a pattern to be clear.</p>`;
    const confHTML = conf.topics.map((t) => {
      const c = t.confidence, p = t.performance, slug = esc(t.topic.slug);
      return `<div style="padding:10px 0;border-top:1px solid var(--line)"><div class="row between"><b>${esc(t.topic.icon)} ${esc(t.topic.name)}</b>
        <span class="muted" style="font-size:13px">Confidence ${c ? c.score + "%" : "not rated"} · Recent accuracy ${p ? pct(p.accuracy) + " (" + p.correct + "/" + p.attempts + ")" : "–"}</span></div>
        <div class="row" style="margin-top:6px">${slider(`data-conf="${slug}"`, c ? c.score : 50)}<button class="btn btn-ghost btn-sm" data-save="${slug}">Save</button></div></div>`;
    }).join("");
    root.innerHTML = shell(`
      <div class="grid g2" style="align-items:start">
        <div><h2 style="margin-top:0">Today</h2>${plan.tasks.length ? `<div class="muted">${plan.done} of ${plan.total} done</div>${plan.tasks.map(taskHTML).join("")}`
            : `<div class="card muted">No tasks yet for your language and level.</div>`}</div>
        <div>${nextHTML}<div class="card" style="margin-top:12px"><h3 style="margin-top:0">Areas to improve</h3>${weakHTML}</div></div>
      </div>
      <div class="card" style="margin-top:14px"><div class="row between"><h3 style="margin:0">Confidence</h3>
        <span class="muted">${conf.overall === null ? "Rate a topic to see your overall confidence" : "Overall " + conf.overall + "%"}</span></div>
        <p class="muted" style="font-size:13px;margin:4px 0 0">How sure you feel. It is yours to set, and is shown next to (never mixed with) your recent accuracy.</p>${confHTML}</div>`);
  }

  async function load(root) {
    let plan = await api("GET", "/api/daily-plan");
    if (!alive(root)) return;
    const b = blocked(plan);
    if (b) { root.innerHTML = shell(b); return; }
    if (plan.ok && !plan.data.plan.generated) plan = await api("POST", "/api/daily-plan/generate");
    const [recs, weak, conf] = await Promise.all([api("GET", "/api/recommendations"), api("GET", "/api/weaknesses"), api("GET", "/api/confidence")]);
    if (!alive(root)) return;
    if (![plan, recs, weak, conf].every((r) => r.ok)) { root.innerHTML = shell(note(`<p class="muted">Couldn't load your plan. Please try again.</p>`)); return; }
    draw(root, { plan: plan.data.plan, recs: recs.data, weak: weak.data.weaknesses, conf: conf.data });
  }

  async function mount() {
    const root = document.getElementById("plan-root"); if (!root) return;
    await load(root);
    root.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.status) { const [id, status] = d.status.split(":"); await api("POST", `/api/daily-plan/tasks/${id}/status`, { status }); }
      else if (d.save) { const v = +$(`[data-conf="${d.save}"]`, root).value; await api("POST", "/api/confidence", { topic: d.save, score: v }); }
      else if (d.taskSave) { const [id, slug] = d.taskSave.split(":"); const v = +$(`[data-task-conf="${id}"]`, root).value; await api("POST", "/api/confidence", { topic: slug, score: v }); }
      else return;
      await load(root);
    };
    root.oninput = (ev) => { const out = ev.target.nextElementSibling; if (ev.target.type === "range" && out) out.textContent = ev.target.value; };
  }

  window.PlanView = { page() { setTimeout(mount, 0); return `<div id="plan-root"><div class="card muted">Loading…</div></div>`; } };
})();
