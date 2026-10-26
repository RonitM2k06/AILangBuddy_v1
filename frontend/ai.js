// AI Tutor (#/ai-tutor, #/ai-tutor/:id) and Roleplay practice (#/ai-roleplay, #/ai-roleplay/:id) for signed-in learners. The server decides
// everything that matters: what the tutor may know, whether a roleplay answer is right, what is revealed and when, and the feedback evidence.
// This page only shows it. Stored facts are shown apart from the generated advice, a failed send keeps your text so you can retry (the
// same client id makes a retry safe), and children are offered only the built-in helper questions.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;
  const newId = () => "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

  function blocked(res, what) {
    if (res.status === 401) return note(`<h2>Sign in to use ${what}</h2><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">${what[0].toUpperCase() + what.slice(1)} is for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }

  // ---------- tutor ----------
  const tutorShell = (inner) => `<div class="page-head"><div><div class="eyebrow">🤖 Tutor Chat</div><h1>Your tutor</h1>
    <p class="sub">Ask for hints, get mistakes explained, or practise a phrase. The tutor only knows what is in your own learning records.</p></div></div>${inner}`;

  async function mountTutorList() {
    const el = document.getElementById("aitutor-root"); if (!el) return;
    const res = await api("GET", "/api/tutor/conversations");
    if (!alive(el)) return;
    const b = blocked(res, "the tutor");
    if (b) { el.innerHTML = tutorShell(b); return; }
    if (!res.ok) { el.innerHTML = tutorShell(note(`<p class="muted">Couldn't load your conversations. Please try again.</p>`)); return; }
    const list = res.data.conversations;
    el.innerHTML = tutorShell(`<button class="btn btn-primary" data-new>New conversation</button> <span class="muted" id="at-msg"></span>
      <div style="display:grid;gap:8px;margin-top:14px">${list.map((c) => `<a class="card hover" href="#/ai-tutor/${c.id}" style="text-decoration:none;color:inherit"><b>${esc(c.title)}</b>
        <div class="muted" style="font-size:13px">${c.message_count} messages · ${esc(c.updated_at)}</div></a>`).join("") || `<div class="muted">No conversations yet.</div>`}</div>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || t.dataset.new === undefined) return;
      const r = await api("POST", "/api/tutor/conversations", {});
      if (r.ok) window.location.hash = "#/ai-tutor/" + r.data.conversation.id; else el.querySelector("#at-msg").textContent = errText(r);
    };
  }

  async function mountTutor(id) {
    const el = document.getElementById("aitutor-root"); if (!el) return;
    const base = `/api/tutor/conversations/${encodeURIComponent(id)}`;
    const [conv, msgs] = await Promise.all([api("GET", base), api("GET", base + "/messages?limit=100")]);
    if (!alive(el)) return;
    const b = blocked(conv, "the tutor");
    if (b) { el.innerHTML = tutorShell(b); return; }
    if (conv.status === 404) { el.innerHTML = tutorShell(note(`<h2>Conversation not found</h2><a class="btn btn-ghost" href="#/ai-tutor">← Conversations</a>`)); return; }
    if (!conv.ok || !msgs.ok) { el.innerHTML = tutorShell(note(`<p class="muted">Couldn't load this conversation. Please try again.</p>`)); return; }
    const quick = conv.data.quick_prompts;                     // present only for children: the only way a child can talk to the tutor
    let suggestion = null;
    if (!quick) { const sr = await api("GET", "/api/ai/recommendations"); if (sr.ok && sr.data.recommendations.length) suggestion = sr.data.recommendations[0]; }
    let messages = msgs.data.messages, facts = null, busy = false, error = "", draft = "", pending = null;

    const bubble = (m) => `<div class="card" style="margin:8px 0;${m.role === "learner" ? "margin-left:40px;background:var(--surface-2)" : "margin-right:40px"}">
      <div class="muted" style="font-size:12px">${m.role === "learner" ? "You" : "Tutor" + (m.generated ? " · generated advice" : "")}</div><div style="white-space:pre-wrap">${esc(m.content)}</div></div>`;
    const draw = () => {
      el.innerHTML = tutorShell(`<a class="back" href="#/ai-tutor">← Conversations</a><h3 style="margin:8px 0">${esc(conv.data.conversation.title)}</h3>
        ${suggestion ? `<div class="card" id="at-suggestion" style="font-size:13px"><b>Suggested next step</b> <span class="muted">(generated from your records)</span><div>${esc(suggestion.title)}: ${esc(suggestion.reason)}</div></div>` : ""}
        <div id="at-log">${messages.map(bubble).join("") || `<div class="muted">Say hello to your tutor.</div>`}</div>
        ${facts && facts.length ? `<div class="card" style="font-size:13px"><b>From your records</b> <span class="muted">(stored facts the tutor was given)</span>${facts.map((f) => `<div>• ${esc(f.text)}</div>`).join("")}</div>` : ""}
        ${busy ? `<div class="muted" id="at-busy">Thinking…</div>` : ""}${error ? `<div class="muted" id="at-error" style="color:var(--heart,#c33)">${esc(error)}</div>` : ""}
        ${quick ? `<div class="row" style="margin-top:10px">${quick.map((q) => `<button class="btn btn-primary" data-quick="${esc(q.key)}" ${busy ? "disabled" : ""}>${esc(q.text)}</button>`).join("")}</div>`
                : `<div class="row" style="margin-top:10px;flex-wrap:nowrap"><input id="at-input" class="pc-in" style="flex:1" maxlength="500" enterkeyhint="send" aria-label="Ask your tutor" placeholder="Ask your tutor…" value="${esc(draft)}" ${busy ? "disabled" : ""} />
                   <button class="btn btn-primary" data-send ${busy ? "disabled" : ""}>Send</button></div>`}`);
    };
    const send = async (body) => {
      busy = true; error = ""; draw();
      const r = await api("POST", base + "/messages", body);
      busy = false;
      if (!r.ok) { error = r.status === 502 ? "The tutor couldn't answer just now. Your message is kept; press Send to try again." : errText(r); }
      else { messages = messages.concat([r.data.message, r.data.reply]); facts = r.data.facts; draft = ""; pending = null; }
      draw();
      const log = el.querySelector("#at-log"); if (log && log.scrollIntoView) log.scrollIntoView({ block: "end" });
    };
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || busy) return;
      const d = t.dataset;
      if (d.quick) await send({ quick_prompt: d.quick, client_id: newId() });
      else if (d.send !== undefined) {
        const text = el.querySelector("#at-input").value.trim();
        if (!text && !pending) { error = "Type a message first."; draw(); return; }
        if (!pending || pending.text !== text) pending = { text, id: newId() };      // a retry of the same text reuses its id, so it can never be stored twice
        draft = text;
        await send({ message: text, client_id: pending.id });
      }
    };
    draw();
  }

  // ---------- roleplay ----------
  const rpShell = (inner) => `<div class="page-head"><div><div class="eyebrow">🎭 Roleplay</div><h1>Roleplay practice</h1>
    <p class="sub">Act out a real-life situation. Reply in your own words; hints come if you get stuck.</p></div></div>${inner}`;

  async function mountRoleplayList() {
    const el = document.getElementById("airoleplay-root"); if (!el) return;
    const [sits, sessions] = await Promise.all([api("GET", "/api/situations"), api("GET", "/api/roleplay/sessions")]);
    if (!alive(el)) return;
    const b = blocked(sits, "roleplay");
    if (b) { el.innerHTML = rpShell(b); return; }
    if (!sits.ok) { el.innerHTML = rpShell(note(`<p class="muted">Couldn't load situations. Please try again.</p>`)); return; }
    const recent = sessions.ok ? sessions.data.sessions : [];
    el.innerHTML = rpShell(`<div class="grid g2">${sits.data.situations.map((s) => `<div class="card"><div class="row between"><b>${esc(s.topic.icon)} ${esc(s.title)}</b><span class="chip brand">${esc(s.cefr_level)}</span></div>
        <p class="muted" style="margin:6px 0 10px">${esc(s.goal)}</p><button class="btn btn-primary btn-sm" data-start="${s.id}">Start roleplay</button></div>`).join("")}</div>
      <div class="muted" id="rp-msg" style="margin-top:8px"></div>
      ${recent.length ? `<h3 style="margin-top:14px">Your roleplays</h3>${recent.map((r) => `<a class="card hover" href="#/ai-roleplay/${r.id}" style="display:block;text-decoration:none;color:inherit;margin-bottom:8px">
        <b>${esc(r.title)}</b> <span class="chip ${r.status === "completed" ? "ok" : ""}">${r.status === "completed" ? "Finished" : "In progress"}</span></a>`).join("")}` : ""}`);
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || !t.dataset.start) return;
      const r = await api("POST", "/api/roleplay/sessions", { situation_id: +t.dataset.start });
      if (r.ok) window.location.hash = "#/ai-roleplay/" + r.data.session.id; else el.querySelector("#rp-msg").textContent = errText(r);
    };
  }

  async function mountRoleplay(id) {
    const el = document.getElementById("airoleplay-root"); if (!el) return;
    const base = `/api/roleplay/sessions/${encodeURIComponent(id)}`;
    const res = await api("GET", base);
    if (!alive(el)) return;
    const b = blocked(res, "roleplay");
    if (b) { el.innerHTML = rpShell(b); return; }
    if (res.status === 404) { el.innerHTML = rpShell(note(`<h2>Roleplay not found</h2><a class="btn btn-ghost" href="#/ai-roleplay">← Roleplay</a>`)); return; }
    if (!res.ok) { el.innerHTML = rpShell(note(`<p class="muted">Couldn't load this roleplay. Please try again.</p>`)); return; }
    let s = res.data.session, feedback = null, xp = 0, remediation = [], busy = false, error = "", draft = "", pending = null;
    if (s.status === "completed") { const f = await api("GET", base + "/feedback"); if (f.ok) feedback = f.data.feedback; }

    const turn = (t) => `<div style="margin:8px 0"><div class="card" style="margin-left:40px;background:var(--surface-2)"><span class="muted" style="font-size:12px">You${t.input_mode === "voice" ? " (spoken)" : ""}</span><div>${esc(t.you)}</div></div>
      <div class="card" style="margin-right:40px"><div>${esc(t.character)}</div>${t.verdict === "correct" ? `<span class="chip ok">✓ Correct</span>` : `<span class="chip warn">Not quite</span>`}
        ${t.grading && t.grading.method !== "exact" ? `<div class="muted" style="font-size:13px;margin-top:4px" data-grading>${t.grading.semantic_match ? "Understood: your wording means the same. " : ""}${esc(t.grading.explanation)}${t.grading.missing_objective ? " (" + esc(t.grading.missing_objective) + ")" : ""}${t.grading.grammar_feedback ? " " + esc(t.grading.grammar_feedback) : ""}</div>` : ""}
        ${t.model_answer ? `<div class="muted" style="font-size:13px;margin-top:4px">Model answer: ${esc(t.model_answer)}</div>` : ""}</div></div>`;
    const fb = () => `<div class="card"><h3>Feedback</h3><p><b>${esc(feedback.correctness.summary)}</b></p><p>${esc(feedback.encouragement)}</p>
      <p><b>Vocabulary:</b> ${esc(feedback.vocabulary)}</p><p><b>Grammar:</b> ${esc(feedback.grammar)}</p><p><b>Tip:</b> ${esc(feedback.hint)}</p><p><b>Next:</b> ${esc(feedback.next_step)}</p>
      <p class="muted" id="rp-pron">${esc(feedback.pronunciation.note)}</p>${xp ? `<p class="chip ok">+${xp} XP</p>` : ""}
      ${remediation.length ? `<div id="rp-remediation"><b>Practise next</b>${remediation.map((x) => `<div>• ${esc(x.title)} <span class="muted">${esc(x.reason)}</span></div>`).join("")}<a href="#/ai-insights">Open my practice drills</a></div>` : ""}
      <a class="btn btn-primary" href="#/ai-roleplay">More roleplays</a></div>`;
    const draw = () => {
      const p = s.progress, cur = s.current;
      el.innerHTML = rpShell(`<a class="back" href="#/ai-roleplay">← Roleplay</a><h3 style="margin:8px 0">${esc(s.situation.title)}</h3><p class="muted">${esc(s.scene)}</p>
        <div class="muted" id="rp-progress">${p.completed ? "Finished" : p.all_done ? "All steps done" : `Step ${p.current_step} of ${p.steps_total}`}</div><div class="bar" style="margin:6px 0 10px"><i style="width:${Math.round((100 * p.steps_resolved) / p.steps_total)}%"></i></div>
        ${s.turns.map(turn).join("")}
        ${feedback ? fb() : p.all_done ? `<button class="btn btn-primary" data-complete ${busy ? "disabled" : ""}>See my feedback</button>`
          : `<div class="card"><div><b>${esc(cur.objective)}</b></div>${cur.hint ? `<div class="muted" id="rp-hint">Hint: ${esc(cur.hint)}</div>` : ""}<div class="muted" style="font-size:12px">${cur.attempts_left} ${cur.attempts_left === 1 ? "try" : "tries"} left</div>
              <div class="row" style="margin-top:8px;flex-wrap:nowrap"><input id="rp-input" class="pc-in" style="flex:1" maxlength="500" enterkeyhint="send" aria-label="Your reply" placeholder="Your reply…" value="${esc(draft)}" ${busy ? "disabled" : ""} /><button class="btn btn-primary" data-say ${busy ? "disabled" : ""}>Send</button></div></div>`}
        ${error ? `<div class="muted" id="rp-error" style="color:var(--heart,#c33)">${esc(error)}</div>` : ""}`);
    };
    const reload = async () => { const r = await api("GET", base); if (r.ok) s = r.data.session; };
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t || busy) return;
      const d = t.dataset;
      if (d.say !== undefined) {
        const text = el.querySelector("#rp-input").value.trim();
        if (!text) { error = "Type your reply first."; draw(); return; }
        if (!pending || pending.text !== text) pending = { text, id: newId() };
        busy = true; error = ""; draft = text; draw();
        const r = await api("POST", base + "/turns", { text, client_id: pending.id });
        busy = false;
        if (!r.ok) error = errText(r); else { draft = ""; pending = null; await reload(); }
        draw();
      } else if (d.complete !== undefined) {
        busy = true; draw();
        const r = await api("POST", base + "/complete");
        busy = false;
        if (r.ok) { feedback = r.data.feedback; xp = r.data.xp_awarded; remediation = r.data.remediation || []; await reload(); } else error = errText(r);
        draw();
      }
    };
    draw();
  }

  window.AiTutorView = { page(arg) { setTimeout(() => (arg ? mountTutor(arg) : mountTutorList()), 0); return `<div id="aitutor-root"><div class="card muted">Loading…</div></div>`; } };
  window.AiRoleplayView = { page(arg) { setTimeout(() => (arg ? mountRoleplay(arg) : mountRoleplayList()), 0); return `<div id="airoleplay-root"><div class="card muted">Loading…</div></div>`; } };
})();
