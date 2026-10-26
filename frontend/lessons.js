// Database-backed lessons for signed-in learners (#/lessons, #/lessons/:id). Additive: the prototype's
// First Week pack, roleplays and learn tools are untouched and keep working without an account.
(function () {
  const { api, errText, esc } = window.LBApi;
  const $ = (sel, el = document) => el.querySelector(sel);
  const alive = (root) => document.body.contains(root);

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">📘 My Lessons</div><h1>Lessons for your level</h1>
    <p class="sub">Words, grammar and practice for the language and level in your profile.</p></div></div>${inner}`;
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;

  // Why the lessons can't be shown, with the next step (same handling for the list and a single lesson).
  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to see your lessons</h2><p class="muted">Lessons are saved to your account.</p><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">Lessons are for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><p class="muted">Choose the language you want to learn and your level.</p><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }
  const progressChip = (p) => {
    if (p.status === "completed") return `<span class="chip ok">✓ Completed</span>`;
    if (p.status === "in_progress") return `<span class="chip warn">${p.exercises_correct}/${p.exercises_total} done</span>`;
    return `<span class="chip">Not started</span>`;
  };

  // the review note of the learner's language, shown under the page heading once the list is on the page
  async function addReviewBanner(root) {
    const html = await window.LBApi.reviewBanner();
    const head = html && document.body.contains(root) && root.querySelector(".page-head");
    if (head && !root.querySelector("[data-content-review]")) head.insertAdjacentHTML("afterend", html);
  }

  async function mountList() {
    const root = document.getElementById("lessons-root"); if (!root) return;
    const res = await api("GET", "/api/lessons");
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load lessons. Please try again.</p>`)); return; }
    const lessons = res.data.lessons;
    if (!lessons.length) {
      root.innerHTML = shell(note(`<h2>No lessons for this language and level yet</h2><p class="muted">Your First Week pack still works as before.</p><a class="btn btn-primary" href="#/pack">Open First Week</a>`));
      return;
    }
    addReviewBanner(root);
    root.innerHTML = shell(`<div class="grid g2">${lessons.map((l) => `<a class="card hover" href="#/lessons/${l.id}" style="text-decoration:none;color:inherit">
      <div class="row between"><span style="font-size:26px">${esc((l.topics[0] || {}).icon || "📘")}</span><span class="chip brand">${esc(l.cefr_level)}</span></div>
      <h3 style="margin:8px 0 4px">${esc(l.title)}</h3><p class="muted" style="margin:0 0 10px">${esc(l.description)}</p>${progressChip(l.progress)}</a>`).join("")}</div>`);
  }

  const phrase = (v) => `<div style="padding:10px 0;border-top:1px solid var(--line)">
    <div class="deva" style="font-weight:700;font-size:18px">${esc(v.text)}</div>
    ${v.pronunciation ? `<div style="color:var(--brand);font-weight:600;font-size:14px">${esc(v.pronunciation)}</div>` : ""}
    ${v.meaning ? `<div class="muted" style="font-size:14px">${esc(v.meaning)}</div>` : ""}
    ${v.natural ? `<div class="muted" style="font-size:13px">In natural English: “${esc(v.natural)}”</div>` : ""}
    ${(v.examples || []).map((e) => `<div class="muted" style="font-size:13px;margin-top:4px">e.g. ${esc(e.pronunciation || e.text)}${e.meaning ? ` — ${esc(e.meaning)}` : ""}</div>`).join("")}</div>`;

  function exerciseHTML(e, i) {
    const input = e.kind === "multiple_choice"
      ? `<div style="display:grid;gap:8px;margin-top:10px">${e.options.map((o) => `<button class="btn btn-ghost" data-mc="${e.id}:${o.id}">${esc(o.text)}</button>`).join("")}</div>`
      : `<div class="row" style="margin-top:10px"><input class="pc-in" data-text="${e.id}" placeholder="Your answer" aria-label="Your answer" maxlength="500" style="flex:1;min-width:180px" />
         <button class="btn btn-primary btn-sm" data-check="${e.id}">Check</button></div>`;
    return `<div class="card" style="margin-top:12px" data-ex="${e.id}"><b>${i + 1}. ${esc(e.prompt)}</b>${input}<div data-result="${e.id}" style="margin-top:10px"></div></div>`;
  }

  async function mountDetail(id) {
    const root = document.getElementById("lessons-root"); if (!root) return;
    const res = await api("GET", `/api/lessons/${encodeURIComponent(id)}`);
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (res.status === 404) { root.innerHTML = shell(note(`<h2>Lesson not found</h2><a class="btn btn-ghost" href="#/lessons">← My lessons</a>`)); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load this lesson. Please try again.</p>`)); return; }
    const l = res.data.lesson;
    root.innerHTML = `<a class="back" href="#/lessons">← My lessons</a>
      <div class="page-head"><div><div class="eyebrow">${esc((l.topics[0] || {}).icon || "📘")} ${esc(l.cefr_level)}</div><h1>${esc(l.title)}</h1><p class="sub">${esc(l.description)}</p></div>
        <div id="lp-progress">${progressChip(l.progress)}</div></div>
      ${l.situation ? `<div class="card"><b>Situation</b><p style="margin:6px 0 0">${esc(l.situation)}</p></div>` : ""}
      ${l.tip ? `<div class="card" style="margin-top:12px"><b>💡 Tip</b><p style="margin:6px 0 0">${esc(l.tip)}</p></div>` : ""}
      <div class="card" style="margin-top:12px"><h2>Vocabulary</h2>${l.vocabulary.map(phrase).join("")}</div>
      ${l.grammar.map((g) => `<div class="card" style="margin-top:12px"><h2>Grammar: ${esc(g.title)}</h2><p>${esc(g.explanation)}</p>${g.examples.map(phrase).join("")}</div>`).join("")}
      <h2 style="margin-top:22px">Practice</h2>${l.exercises.map(exerciseHTML).join("")}`;

    const submit = async (exerciseId, body) => {
      const out = $(`[data-result="${exerciseId}"]`, root);
      const r = await api("POST", `/api/exercises/${exerciseId}/attempts`, body);
      if (!r.ok) { out.innerHTML = `<span class="muted">${esc(errText(r))}</span>`; return; }
      const d = r.data;
      out.innerHTML = `<div class="feedback"><b>${d.correct ? "✅ Correct!" : "❌ Not quite."}</b>
        ${d.correct ? "" : `<div class="muted" style="margin-top:4px">Answer: ${d.correct_answers.map(esc).join(" / ")}</div>`}
        ${d.explanation ? `<div class="muted" style="margin-top:4px">${esc(d.explanation)}</div>` : ""}</div>`;
      $("#lp-progress", root).innerHTML = progressChip(d.lesson_progress);
    };
    root.onclick = (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      if (t.dataset.mc) { const [ex, ans] = t.dataset.mc.split(":"); submit(ex, { answer_id: +ans }); }
      else if (t.dataset.check) { const v = $(`[data-text="${t.dataset.check}"]`, root).value; submit(t.dataset.check, { text: v }); }
    };
    root.onkeydown = (ev) => {
      if (ev.key === "Enter" && ev.target.dataset && ev.target.dataset.text) submit(ev.target.dataset.text, { text: ev.target.value });
    };
  }

  window.LessonsView = {
    page(arg) { setTimeout(() => (arg ? mountDetail(arg) : mountList()), 0); return `<div id="lessons-root"><div class="card muted">Loading…</div></div>`; },
  };
})();
