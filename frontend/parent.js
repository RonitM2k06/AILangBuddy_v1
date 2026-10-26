// Parent portal (#/parent, #/parent/:id). A parent links a child with the one-time code the child makes, then sees that child's
// progress, activity, confidence, areas to improve and the parental controls. Everything is read from the server, which only ever
// answers for children linked to this parent; the page keeps nothing. Children are named by the parent's own link id.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const root = () => document.getElementById("parent-root");
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;
  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">👪 My Children</div><h1>Family</h1><p class="sub">See how your child is learning and choose what they can use.</p></div></div>${inner}`;
  const pct = (a, b) => (b ? Math.round((100 * a) / b) + "%" : "–");

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in as a parent</h2><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Parent accounts only</h2><p class="muted">Create a parent account to follow a child's learning.</p>`);
    return null;
  }

  async function mountList() {
    const el = root(); if (!el) return;
    const res = await api("GET", "/api/parent/children");
    if (!alive(el)) return;
    const b = blocked(res);
    if (b) { el.innerHTML = shell(b); return; }
    if (!res.ok) { el.innerHTML = shell(note(`<p class="muted">Couldn't load your children. Please try again.</p>`)); return; }
    const kids = res.data.children;
    const cards = kids.map((c) => `<a class="card hover" href="#/parent/${c.id}" style="text-decoration:none;color:inherit;display:block">
      <b>${esc(c.display_name)}</b><div class="muted" style="margin-top:4px">${c.has_profile ? `${esc(c.age_group.label)} · ${esc(c.target_language)} · ${esc(c.cefr_level)}` : "Has not set up a profile yet"}</div></a>`).join("");
    el.innerHTML = shell(`<div class="grid g2">${cards || note(`<p class="muted">No children linked yet.</p>`)}</div>
      <div class="card" style="max-width:560px;margin-top:14px"><b>Add a child</b>
        <p class="muted" style="margin:6px 0 10px">Ask your child to open their Profile, press “Make a code”, and type the code here.</p>
        <div class="row"><input id="pa-code" class="pc-in" placeholder="Code" maxlength="40" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-label="Your child's link code" /><button class="btn btn-primary" id="pa-add">Add</button></div>
        <div class="muted" id="pa-msg" style="margin-top:8px"></div></div>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || t.id !== "pa-add") return;
      const code = el.querySelector("#pa-code").value.trim();
      const msg = el.querySelector("#pa-msg");
      if (!code) { msg.textContent = "Type the code your child made."; return; }
      const r = await api("POST", "/api/parent/children", { code });
      if (r.ok) mountList(); else msg.textContent = errText(r);
    };
  }

  const list = (rows, empty) => (rows.length ? rows.join("") : `<div class="muted">${empty}</div>`);

  async function mountChild(id) {
    const el = root(); if (!el) return;
    const base = `/api/parent/children/${encodeURIComponent(id)}`;
    const [ov, wk, cf, ac] = await Promise.all([api("GET", base + "/overview"), api("GET", base + "/weaknesses"), api("GET", base + "/confidence"), api("GET", base + "/activity")]);
    if (!alive(el)) return;
    const b = blocked(ov);
    if (b) { el.innerHTML = shell(b); return; }
    if (ov.status === 404) { el.innerHTML = shell(note(`<h2>Child not found</h2><a class="btn btn-ghost" href="#/parent">← My children</a>`)); return; }
    if (!ov.ok) { el.innerHTML = shell(note(`<p class="muted">Couldn't load this child. Please try again.</p>`)); return; }
    const o = ov.data, c = o.child;
    let controls = o.controls;

    const stat = (label, value) => `<div class="card" style="text-align:center"><div class="muted" style="font-size:13px">${label}</div><div style="font-size:26px;font-weight:800">${value}</div></div>`;
    const lis = o.listening;
    const weaknesses = wk.ok && wk.data.weaknesses ? wk.data.weaknesses : [];
    const hist = cf.ok && cf.data.history ? cf.data.history : [];
    const topics = cf.ok && cf.data.overview ? cf.data.overview.topics.filter((t) => t.confidence) : [];
    const recent = ac.ok && ac.data.recent ? ac.data.recent : [];
    const plan = o.daily_plan;

    const draw = () => {
      const voice = controls.voice_unavailable_reason === "age_group"
        ? `<p class="muted">Voice practice is off for children under 10. This can't be turned on.</p>`
        : `<label class="row" style="gap:10px"><input type="checkbox" id="pa-voice" ${controls.voice_disabled ? "checked" : ""} /> <span>Turn off voice practice (speaking and recording) for ${esc(c.display_name)}</span></label>
           ${controls.voice_available_to_child ? "" : `<div class="muted" style="margin-top:6px">Voice practice is currently off for this child.</div>`}`;
      el.innerHTML = shell(`<a class="back" href="#/parent">← My children</a>
        <h2 style="margin:10px 0 2px">${esc(c.display_name)}</h2>
        <div class="muted" style="margin-bottom:12px">${c.has_profile ? `${esc(c.age_group.label)} · learning ${esc(c.target_language)} · level ${esc(c.cefr_level)}` : "Has not set up a profile yet"}</div>
        <div class="grid g3" style="margin-bottom:14px">
          ${stat("Lessons completed", `${o.lessons.completed} / ${o.lessons.started} started`)}
          ${stat("Listening answers", lis ? lis.attempts + (lis.accuracy === null ? "" : " · " + Math.round(lis.accuracy * 100) + "% right") : "–")}
          ${stat("Confidence", o.confidence_overall === null ? "–" : o.confidence_overall + "%")}
          ${stat("Today's plan", plan && plan.generated ? `${plan.done} / ${plan.total} done` : "–")}
          ${stat("Speaking sessions", o.speaking ? o.speaking.completed + " completed" : "–")}
          ${stat("Areas to improve", o.weaknesses_count === null ? "–" : o.weaknesses_count)}</div>
        <div class="grid g2">
          <div class="card"><b>Areas to improve</b>${list(weaknesses.map((w) => `<div style="margin-top:8px">${w.topic ? esc(w.topic.icon) + " " : "🔤 "}<span class="chip ${w.severity === "high" ? "heart" : "warn"}">${esc(w.severity)}</span> ${esc(w.summary)}</div>`), "Nothing needs extra practice right now.")}</div>
          <div class="card"><b>Confidence</b>${list(topics.map((t) => `<div style="margin-top:8px">${esc(t.topic.icon)} ${esc(t.topic.name)}: <b>${t.confidence.score}%</b></div>`), "No confidence ratings yet.")}
            ${hist.length ? `<div class="muted" style="margin-top:8px;font-size:13px">Recent ratings: ${hist.slice(0, 8).map((h) => h.score + "%").join(" ← ")}</div>` : ""}</div>
          <div class="card"><b>Recent activity</b>${list(recent.slice(0, 10).map((r) => `<div style="margin-top:6px" class="muted">${r.correct ? "✅" : "❌"} ${esc(r.source)} · ${esc(r.at)}</div>`), "No activity yet.")}</div>
          <div class="card"><b>Pronunciation & speaking</b>${o.pronunciation && o.pronunciation.pronunciation.length
            ? o.pronunciation.pronunciation.map((p) => `<div style="margin-top:6px">${esc(p.label)}: <b>${p.average_score}</b> / 100 <span class="muted">(${p.assessments} ${p.assessments === 1 ? "check" : "checks"}${p.is_measurement ? "" : ", test score"})</span></div>`).join("")
            : `<div class="muted" style="margin-top:6px">No pronunciation checks yet.</div>`}</div></div>
        <div class="card" style="margin-top:14px"><b>Controls</b><div style="margin-top:8px">${voice}</div><div class="muted" id="pa-ctl-msg" style="margin-top:8px"></div></div>
        <div style="margin-top:14px"><button class="btn btn-ghost btn-sm" id="pa-unlink">Stop following ${esc(c.display_name)}</button></div>`);
    };

    el.onchange = async (ev) => {
      if (!ev.target || ev.target.id !== "pa-voice") return;
      const r = await api("PUT", base + "/controls", { voice_disabled: !!ev.target.checked });
      if (r.ok) { controls = r.data.controls; draw(); el.querySelector("#pa-ctl-msg").textContent = "Saved ✓"; }
      else { draw(); el.querySelector("#pa-ctl-msg").textContent = errText(r); }
    };
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || t.id !== "pa-unlink") return;
      if (!window.confirm || window.confirm(`Stop following ${c.display_name}? You can link again with a new code.`)) {
        const r = await api("DELETE", base);
        if (r.ok) window.location.hash = "#/parent"; else el.querySelector("#pa-ctl-msg").textContent = errText(r);
      }
    };
    draw();
  }

  window.ParentView = { page(arg) { setTimeout(() => (arg ? mountChild(arg) : mountList()), 0); return `<div id="parent-root"><div class="card muted">Loading…</div></div>`; } };
})();
