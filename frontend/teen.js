// My Path for teen learners (#/path): the learner's lessons, the recommended next step, difficulty and the areas to improve.
// Everything shown comes from the existing curriculum, recommendation, weakness and plan systems (the server composes them);
// nothing is recomputed here.
(function () {
  const { api, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;
  const link = (t) => (t.type === "lesson" ? `#/lessons/${t.id}` : t.type === "situation" ? `#/situations/${t.id}` : "#/plan");
  const status = (p) => (p.status === "completed" ? `<span class="chip ok">Completed</span>` : p.status === "in_progress" ? `<span class="chip warn">In progress</span>` : `<span class="chip">New</span>`);

  async function mount() {
    const el = document.getElementById("path-root"); if (!el) return;
    const res = await api("GET", "/api/teen/home");
    if (!alive(el)) return;
    const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🧭 My Path</div><h1>Your path</h1><p class="sub">Pick up where you left off and work on what needs practice.</p></div></div>${inner}`;
    if (res.status === 401) { el.innerHTML = shell(note(`<h2>Sign in to see your path</h2><a class="btn btn-primary" href="#/profile">Sign in</a>`)); return; }
    if (res.status === 403) { el.innerHTML = shell(note(`<h2>Not available for this account</h2><a class="btn btn-ghost" href="#/">Go home</a>`)); return; }
    if (res.status === 409) { el.innerHTML = shell(note(`<h2>Set up your profile first</h2><a class="btn btn-primary" href="#/profile">Open profile</a>`)); return; }
    if (!res.ok) { el.innerHTML = shell(note(`<p class="muted">Couldn't load your path. Please try again.</p>`)); return; }
    const h = res.data, n = h.next_activity;
    const next = n ? `<a class="card hover" href="${link(n.target)}" style="display:block;text-decoration:none;color:inherit;margin-bottom:14px"><div class="eyebrow">Up next</div>
        <h3 style="margin:4px 0">${esc(n.target.title)}</h3><p class="muted" style="margin:0">${esc(n.reason)}</p></a>` : "";
    const diff = `<span class="chip brand" title="${esc(h.difficulty.reason)}">Difficulty: ${esc(h.difficulty.label)}</span>`;
    const weak = h.weaknesses.length ? `<div class="card" style="margin-bottom:14px"><b>Worth practising</b>${h.weaknesses.map((w) => `<div class="muted" style="margin-top:6px">${esc(w.reason || w.message || w.kind || "")}</div>`).join("")}</div>` : "";
    const plan = h.daily_plan.generated ? `<span class="chip">Today: ${h.daily_plan.done}/${h.daily_plan.total} done</span>` : `<a class="chip" href="#/plan">Make today's plan</a>`;
    el.innerHTML = shell(`<div class="row" style="margin-bottom:12px">${diff}${plan}</div>${next}${weak}
      <div class="grid g2">${h.path.map((l) => `<a class="card hover" href="#/lessons/${l.id}" style="text-decoration:none;color:inherit"><div class="row between"><b>${esc(l.title)}</b><span class="chip brand">${esc(l.cefr_level)}</span></div>
        <p class="muted" style="margin:6px 0 10px">${esc(l.description)}</p>${status(l.progress)}</a>`).join("")}</div>`);
  }
  window.TeenView = { page() { setTimeout(mount, 0); return `<div id="path-root"><div class="card muted">Loading…</div></div>`; } };
})();
