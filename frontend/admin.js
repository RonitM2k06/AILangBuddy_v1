// Admin console (#/admin/...). Dashboard, curriculum CMS, analytics, learners, audit log and health, for accounts with the admin role.
// Everything here is presentation: the SERVER decides who is an admin (every /api/admin/* route checks the session) and what a response may contain. This file
// only hides what a non-admin has no use for, and a tampered client still gets 401/403 from every call. It never builds a request that deletes anything (the API
// has no delete), always sends the CSRF header on writes, and puts every piece of server text through esc() before it reaches the page.
// State lives in the URL (#/admin/audit?action=publish&offset=25), so pages are refresh-safe, back/forward work and pagination is plain links.
(function () {
  const { esc } = window.LBApi;
  const NAV = [["#/admin", "📊", "Dashboard"], ["#/admin/curriculum", "📚", "Curriculum"], ["#/admin/analytics", "📈", "Analytics"], ["#/admin/learners", "👥", "Learners"],
    ["#/admin/audit", "🧾", "Audit log"], ["#/admin/security", "🔐", "Security"], ["#/admin/health", "🩺", "Health"]];
  const PAGE = 25;
  const PLURAL = { lesson: "lessons", situation: "situations", listening_activity: "listening activities" };
  const root = () => document.getElementById("admin-root");
  const alive = (el) => document.body.contains(el);

  // ---------- http: writes always carry Content-Type: application/json and X-Requested-With, the API's CSRF contract ----------
  async function call(method, url, body) {
    const opts = { method, headers: {} };
    if (method !== "GET") { opts.headers["Content-Type"] = "application/json"; opts.headers["X-Requested-With"] = "XMLHttpRequest"; opts.body = JSON.stringify(body || {}); }
    let res;
    try { res = await fetch(url, opts); } catch (e) { return { ok: false, status: 0, data: null }; }
    let data = null;
    try { data = await res.json(); } catch (e) {}
    return { ok: res.ok, status: res.status, data };
  }
  const get = (url) => call("GET", url);

  // ---------- the URL is the state ----------
  function parseHash() {
    const raw = ((window.location && window.location.hash) || "").replace(/^#\/?/, "");
    const cut = raw.indexOf("?");
    const path = cut < 0 ? raw : raw.slice(0, cut);
    const query = {};
    (cut < 0 ? "" : raw.slice(cut + 1)).split("&").filter(Boolean).forEach((kv) => {
      const i = kv.indexOf("=");
      const k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i));
      query[k] = decodeURIComponent(i < 0 ? "" : kv.slice(i + 1).replace(/\+/g, " "));
    });
    return { segs: path.split("/").filter(Boolean).slice(1), query };   // segs without the leading "admin"
  }
  function hashFor(path, query) {
    const q = Object.keys(query || {}).filter((k) => query[k] !== "" && query[k] != null).map((k) => encodeURIComponent(k) + "=" + encodeURIComponent(query[k])).join("&");
    return "#/admin" + (path ? "/" + path : "") + (q ? "?" + q : "");
  }
  const go = (h) => { window.location.hash = h; };

  // ---------- small building blocks ----------
  const shell = (eyebrow, title, sub, inner, actions) => `<div class="page-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1>${sub ? `<p class="sub">${esc(sub)}</p>` : ""}</div>${actions || ""}</div>${inner}`;
  const loading = `<div class="card muted" data-state="loading">Loading…</div>`;
  const empty = (text) => `<div class="card muted ad-empty" data-state="empty">${esc(text)}</div>`;
  let mfaNeeded = false, forbidden = false;                                  // set when a response says "not an admin"; mount() then sends the visitor home
  function errorBox(res, what) {
    const d = res && res.data && res.data.detail;
    if (res.status === 403 && d && typeof d === "object" && d.code === "mfa_required") {            // Phase 14D: admins need a second factor
      mfaNeeded = true;
      return `<div class="card ad-error" data-state="mfa-required"><h2>Turn on two-factor authentication</h2>
        <p class="muted">The admin console needs a code from an authenticator app as well as your password. Set it up here; the console opens as soon as it is on.</p></div><div id="ad-2fa"></div>`;
    }
    if (res.status === 403) forbidden = true;
    if (res.status === 401) return `<div class="card ad-error" data-state="error"><h2>Sign in as an administrator</h2><p class="muted">Your session has ended or you are not signed in.</p><a class="btn btn-primary" href="#/profile">Sign in</a></div>`;
    if (res.status === 403) return `<div class="card ad-error" data-state="forbidden"><h2>Administrators only</h2><p class="muted">This area is for admin accounts.</p></div>`;
    if (res.status === 404) return `<div class="card ad-error" data-state="notfound"><h2>Not found</h2><a class="btn btn-ghost" href="#/admin">← Admin home</a></div>`;
    return `<div class="card ad-error" data-state="error"><h2>Couldn't load ${esc(what || "this page")}</h2><p class="muted">${esc(detailText(res) || "Please try again.")}</p><button class="btn btn-primary" data-act="retry">Retry</button></div>`;
  }
  function detailText(res) {
    const d = res && res.data && res.data.detail;
    if (Array.isArray(d)) return d.map((e) => e.msg).join(" · ");
    if (d && typeof d === "object") return d.message || d.code || "";
    return typeof d === "string" ? d : "";
  }
  const badge = (status) => `<span class="chip ad-status ad-${esc(status)} ${status === "published" ? "ok" : status === "archived" ? "warn" : "brand"}">${esc(status)}</span>`;
  const sev = (s) => `<span class="chip ${s === "error" ? "heart" : "warn"}">${esc(s)}</span>`;
  const opts = (values, selected, any) => (any ? `<option value="">${esc(any)}</option>` : "") + values.map((v) => { const [val, label] = Array.isArray(v) ? v : [v, v]; return `<option value="${esc(val)}" ${String(val) === String(selected || "") ? "selected" : ""}>${esc(label)}</option>`; }).join("");
  const table = (cols, rows) => `<div class="ad-table-wrap"><table class="ad-table"><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  const cell = (html) => `<td>${html}</td>`;

  function pager(path, query, total, limit, offset) {
    const prev = offset > 0 ? `<a class="btn btn-ghost btn-sm" data-act="prev" href="${hashFor(path, { ...query, offset: Math.max(0, offset - limit) || "" })}">← Previous</a>` : `<span class="btn btn-ghost btn-sm" disabled>← Previous</span>`;
    const next = offset + limit < total ? `<a class="btn btn-ghost btn-sm" data-act="next" href="${hashFor(path, { ...query, offset: offset + limit })}">Next →</a>` : `<span class="btn btn-ghost btn-sm" disabled>Next →</span>`;
    const from = total ? offset + 1 : 0;
    return `<div class="row between ad-pager" style="margin-top:12px"><span class="muted">${from}–${Math.min(total, offset + limit)} of ${total}</span><span class="row" style="gap:8px">${prev}${next}</span></div>`;
  }
  const valueOf = (el, id) => { const n = el.querySelector("#" + id); return n ? String(n.value == null ? "" : n.value).trim() : ""; };
  const intOrNull = (t) => (t === "" ? null : parseInt(t, 10));
  const num = (n) => (n == null ? "–" : Number(n).toLocaleString ? Number(n).toLocaleString("en-US") : String(n));
  const pct = (r) => Math.round(r * 1000) / 10 + "%";

  // ---------- metrics (every figure carries a status; a suppressed one shows no number at all) ----------
  const SUPPRESSED = `<span class="ad-sup" title="Fewer than 5 learners: not shown">hidden · fewer than 5 learners</span>`;
  const count = (m) => (!m ? "–" : m.status === "suppressed" ? SUPPRESSED : num(m.value));
  const rate = (m) => (!m ? "–" : m.status === "suppressed" ? SUPPRESSED : m.status === "no_data" ? `<span class="muted">no data</span>` : `${pct(m.rate)} <span class="muted">(${num(m.numerator)} of ${num(m.denominator)})</span>`);
  const stat = (label, html, hint) => `<div class="card ad-stat"><div class="muted">${esc(label)}</div><div class="ad-big">${html}</div>${hint ? `<div class="muted" style="font-size:12.5px">${esc(hint)}</div>` : ""}</div>`;

  // ---------- inline SVG charts ----------
  function lineChart(points, w, h) {
    // points: [{label, value|null}]; a null (suppressed) value is a gap, never a zero
    const max = Math.max(1, ...points.map((p) => (p.value == null ? 0 : p.value)));
    const x = (i) => 30 + (points.length <= 1 ? 0 : (i * (w - 40)) / (points.length - 1));
    const y = (v) => h - 22 - (v * (h - 40)) / max;
    let d = "", pen = false;
    points.forEach((p, i) => { if (p.value == null) { pen = false; return; } d += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(p.value).toFixed(1) + " "; pen = true; });
    const dots = points.map((p, i) => (p.value == null ? `<circle cx="${x(i).toFixed(1)}" cy="${h - 22}" r="2.5" class="ad-gap"><title>${esc(p.label)}: hidden</title></circle>` : `<circle cx="${x(i).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="3"><title>${esc(p.label)}: ${p.value}</title></circle>`)).join("");
    return `<svg class="ad-chart" data-chart="line" viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Active learners over time"><line x1="30" y1="${h - 22}" x2="${w - 10}" y2="${h - 22}" class="ad-axis"/><path d="${d}" class="ad-line" fill="none"/>${dots}<text x="4" y="14" class="ad-tick">${max}</text><text x="4" y="${h - 24}" class="ad-tick">0</text></svg>`;
  }
  function barChart(buckets, w) {
    // buckets: [{label, count|null, status}]
    const rows = buckets.filter(Boolean);
    const max = Math.max(1, ...rows.map((b) => (b.count == null ? 0 : b.count)));
    const rh = 26, h = rows.length * rh + 6;
    return `<svg class="ad-chart" data-chart="bar" viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Distribution">${rows.map((b, i) => {
      const bw = b.count == null ? 0 : Math.round(((w - 190) * b.count) / max);
      return `<text x="0" y="${i * rh + 17}" class="ad-tick">${esc(b.label)}</text><rect x="150" y="${i * rh + 4}" width="${bw}" height="16" rx="4" class="ad-bar"/><text x="${156 + bw}" y="${i * rh + 17}" class="ad-tick">${b.count == null ? "hidden" : esc(b.count)}</text>`;
    }).join("")}</svg>`;
  }
  const distribution = (title, d) => `<div class="card"><b>${esc(title)}</b><div class="muted" style="font-size:12.5px">${d.total.status === "suppressed" ? "Total hidden (fewer than 5 learners)" : num(d.total.value) + " learners"}</div>${d.buckets.length ? barChart(d.buckets.map((b) => ({ label: b.label, count: b.count })), 480) : `<div class="muted" style="margin-top:8px">No learners yet.</div>`}</div>`;

  // ---------- findings (publish validation) ----------
  function findings(list, ok) {
    if (!list || !list.length) return ok ? `<div class="card ad-findings ad-ok" data-findings="clean"><b>✓ No findings.</b> This passes every publish rule.</div>` : "";
    const errors = list.filter((f) => f.severity === "error").length, warnings = list.length - errors;
    return `<div class="card ad-findings" data-findings="${errors ? "blocked" : "warnings"}"><b>${errors ? "Publishing is blocked" : "Warnings"}</b> <span class="muted">${errors} error${errors === 1 ? "" : "s"}, ${warnings} warning${warnings === 1 ? "" : "s"}</span>
      <ul class="ad-list">${list.map((f) => `<li data-code="${esc(f.code)}">${sev(f.severity)} <code>${esc(f.code)}</code> ${esc(f.message)} <span class="muted">(${esc(f.entity)}${f.entity_status ? ", " + esc(f.entity_status) : ""})</span></li>`).join("")}</ul></div>`;
  }

  // =====================================================================================================================
  // pages
  // =====================================================================================================================
  const WINDOWS = ["7d", "30d", "90d"];

  async function dashboard(el, ctx) {
    const win = WINDOWS.includes(ctx.query.window) ? ctx.query.window : "30d";
    const [d, s] = await Promise.all([get(`/api/admin/dashboard?window=${win}`), get(`/api/admin/analytics/activity?window=${win}`)]);
    if (!alive(el)) return;
    if (!d.ok) { el.innerHTML = shell("Admin", "Dashboard", "", errorBox(d, "the dashboard")); return; }
    const x = d.data, sel = `<label class="muted">Window <select id="ad-window">${opts(WINDOWS, win)}</select></label>`;
    const series = s.ok ? lineChart(s.data.points.map((p) => ({ label: p.date, value: p.dau.status === "ok" ? p.dau.value : null })), 640, 160) : `<div class="muted">The activity chart could not be loaded.</div>`;
    el.innerHTML = shell("Admin", "Dashboard", `Aggregates over ${x.window.from} → ${x.window.to} (UTC). Figures that involve fewer than 5 learners are hidden.`,
      `<div class="grid g3" style="margin-bottom:14px">${stat("Learners", count(x.learners.total))}${stat("New in window", count(x.learners.new))}${stat("Active in window", count(x.learners.active), "any learning evidence")}
        ${stat("Active today (DAU)", count(x.activity.dau), "as of " + x.activity.as_of)}${stat("Last 7 days (WAU)", count(x.activity.wau))}${stat("Last 30 days (MAU)", count(x.activity.mau))}</div>
       <div class="card" style="margin-bottom:14px"><b>Daily active learners</b>${series}</div>
       <div class="grid g3" style="margin-bottom:14px">${distribution("Target language", x.distributions.language)}${distribution("CEFR level", x.distributions.cefr)}${distribution("Age group", x.distributions.age_group)}</div>
       <div class="grid g2"><div class="card"><b>Learning</b><table class="ad-kv"><tr><td>Lesson completion</td><td>${rate(x.learning.lesson_completion)}</td></tr><tr><td>Exercise accuracy</td><td>${rate(x.learning.exercise_accuracy)}</td></tr>
        <tr><td>Situation completion</td><td>${rate(x.learning.situation_completion)}</td></tr><tr><td>Listening accuracy</td><td>${rate(x.learning.listening_accuracy)}</td></tr></table></div>
        <div class="card"><b>Speaking and roleplay</b><table class="ad-kv"><tr><td>Speaking participation</td><td>${rate(x.speaking.speaking_participation)}</td></tr><tr><td>Pronunciation checks</td><td>${count(x.speaking.pronunciation_usage.attempts)}</td></tr>
        <tr><td>Roleplay success</td><td>${rate(x.speaking.roleplay.success)}</td></tr></table></div></div>
       <p class="muted" style="margin-top:14px">More detail: <a href="#/admin/analytics">Analytics</a> · <a href="#/admin/learners">Learners</a></p>`, sel);
    el.onchange = (ev) => { if (ev.target && ev.target.id === "ad-window") go(hashFor("", { window: ev.target.value })); };
  }

  // ---------- analytics ----------
  async function analytics(el, ctx) {
    const q = ctx.query, win = WINDOWS.includes(q.window) ? q.window : (q.from || q.to ? "" : "30d");
    const span = win ? `window=${win}` : `from=${encodeURIComponent(q.from || "")}&to=${encodeURIComponent(q.to || "")}`;
    const kind = ["lesson", "situation", "listening"].includes(q.kind) ? q.kind : "lesson", off = parseInt(q.offset || "0", 10) || 0, grain = q.grain === "week" ? "week" : "day";
    const [act, lrn, spk, cw, eng, ada, cp] = await Promise.all([get(`/api/admin/analytics/activity?${span}&grain=${grain}`), get(`/api/admin/analytics/learning?${span}`), get(`/api/admin/analytics/speaking?${span}`),
      get(`/api/admin/analytics/confidence-weakness?${span}`), get(`/api/admin/analytics/engagement?${span}`), get(`/api/admin/analytics/adaptive?${span}`),
      get(`/api/admin/analytics/content-performance?${span}&kind=${kind}&limit=${PAGE}&offset=${off}`)]);
    if (!alive(el)) return;
    const bad = [act, lrn, spk, cw, eng, ada, cp].find((r) => !r.ok);
    const controls = `<div class="row" style="gap:8px;flex-wrap:wrap"><select id="ad-window"><option value="">Custom dates</option>${opts(WINDOWS, win)}</select>
      <input id="ad-from" class="pc-in" type="text" placeholder="From YYYY-MM-DD" value="${esc(q.from || "")}" style="width:150px" /><input id="ad-to" class="pc-in" type="text" placeholder="To YYYY-MM-DD" value="${esc(q.to || "")}" style="width:150px" />
      <select id="ad-grain">${opts([["day", "Daily"], ["week", "Weekly"]], grain)}</select><button class="btn btn-primary btn-sm" data-act="apply-window">Apply</button></div>`;
    if (bad) { el.innerHTML = shell("Admin", "Analytics", "", `<div class="card" style="margin-bottom:12px">${controls}</div>` + errorBox(bad, "analytics")); bindAnalytics(el, ctx); return; }
    const a = act.data, l = lrn.data, s = spk.data, c = cw.data, e = eng.data, d = ada.data, p = cp.data;
    const series = a.points.length ? lineChart(a.points.map((pt) => { const m = pt.dau || pt.active_learners; return { label: pt.date, value: m.status === "ok" ? m.value : null }; }), 640, 160) : "";
    const conf = c.confidence_vs_performance.length ? table(["Topic", "Learners", "Mean confidence", "Mean accuracy", "Gap"], c.confidence_vs_performance.map((t) => `<tr data-topic="${esc(t.topic.slug)}">${cell(esc(t.topic.name))}${t.status === "suppressed" ? `<td colspan="4">${SUPPRESSED}</td>` : cell(num(t.learners)) + cell(t.mean_confidence + "%") + cell(t.mean_accuracy + "%") + cell((t.gap > 0 ? "+" : "") + t.gap)}</tr>`))
      : empty("No topic has both a confidence rating and practice in this window.");
    const perf = p.items.length ? table(["Title", "Status", "Attempts", "Learners", "Accuracy", "Completion", ""], p.items.map((i) => `<tr data-unit="${i.id}">${cell(esc(i.title))}${cell(badge(i.status))}${i.cell === "suppressed" ? `<td colspan="4">${SUPPRESSED}</td>` : cell(num(i.attempts)) + cell(num(i.learners)) + cell(pct(i.accuracy)) + cell(i.completion ? rate(i.completion) : "–") + cell(i.review_candidate ? `<span class="chip warn">review</span>` : "")}</tr>`)) + pager("analytics", { ...q, kind }, p.total, p.limit, p.offset)
      : empty("No learner activity on this kind of content in this window.");
    el.innerHTML = shell("Admin", "Analytics", `${a.window.from} → ${a.window.to} · ${a.window.days} days · UTC · fewer than 5 learners is always hidden`,
      `<div class="card" style="margin-bottom:12px">${controls}</div>
       <div class="card" style="margin-bottom:12px"><b>Active learners</b> <span class="muted">(${grain === "week" ? "per 7-day bucket" : "per day"}; evidence: ${esc(a.evidence_kinds.join(", ") || "none in this window")})</span>${series}</div>
       <div class="grid g2" style="margin-bottom:12px"><div class="card"><b>Learning</b><table class="ad-kv"><tr><td>Lesson completion</td><td>${rate(l.lesson_completion)}</td></tr><tr><td>Exercise accuracy</td><td>${rate(l.exercise_accuracy)}</td></tr>
        <tr><td>Situation completion</td><td>${rate(l.situation_completion)}</td></tr><tr><td>Listening accuracy</td><td>${rate(l.listening_accuracy)}</td></tr></table></div>
        <div class="card"><b>Speaking</b><table class="ad-kv"><tr><td>Participation</td><td>${rate(s.speaking_participation)}</td></tr><tr><td>Pronunciation checks</td><td>${count(s.pronunciation_usage.attempts)}</td></tr>
        <tr><td>Roleplay sessions started</td><td>${count(s.roleplay.started)}</td></tr><tr><td>Roleplay success</td><td>${rate(s.roleplay.success)}</td></tr></table></div></div>
       <div class="card" style="margin-bottom:12px"><b>Confidence versus measured accuracy</b><p class="muted" style="font-size:13px">Self-reported confidence beside what the same learners actually got right, per topic.</p>${conf}</div>
       <div class="grid g2" style="margin-bottom:12px"><div class="card"><b>Where learners struggle</b><div class="muted" style="font-size:12.5px">Active weaknesses now, by topic</div>${c.weaknesses.by_topic.length ? barChart(c.weaknesses.by_topic.map((b) => ({ label: b.label, count: b.learners })), 480) : `<div class="muted" style="margin-top:8px">No active weaknesses.</div>`}</div>
        <div class="card"><b>Engagement</b><table class="ad-kv"><tr><td>XP awarded</td><td>${count(e.xp.xp_awarded)}</td></tr><tr><td>Learners earning XP</td><td>${count(e.xp.learners_earning)}</td></tr><tr><td>Streak days</td><td>${count(e.streak.streak_days)}</td></tr>
        <tr><td>Achievements unlocked</td><td>${count(e.achievements.unlocks)}</td></tr><tr><td>Challenge claim rate</td><td>${rate(e.challenges.claim_rate)}</td></tr></table></div></div>
       <div class="card" style="margin-bottom:12px"><b>Adaptive learning</b><table class="ad-kv"><tr><td>Recommendations shown</td><td>${count(d.recommendations.shown)}</td></tr><tr><td>Recommendations applied</td><td>${rate(d.recommendations.applied_rate)}</td></tr>
        <tr><td>Micro-lessons made</td><td>${count(d.micro_lessons.generated)}</td></tr><tr><td>Micro-lesson accuracy</td><td>${rate(d.micro_lessons.attempt_accuracy)}</td></tr></table></div>
       <div class="card"><div class="row between"><b>Content performance</b><select id="ad-kind">${opts([["lesson", "Lessons"], ["situation", "Situations"], ["listening", "Listening"]], kind)}</select></div>${perf}</div>`);
    bindAnalytics(el, ctx);
  }
  function bindAnalytics(el, ctx) {
    el.onclick = (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      if (t.dataset.act === "retry") { mount(); return; }
      if (t.dataset.act !== "apply-window") return;
      const w = valueOf(el, "ad-window");
      go(hashFor("analytics", w ? { window: w, grain: valueOf(el, "ad-grain"), kind: ctx.query.kind } : { from: valueOf(el, "ad-from"), to: valueOf(el, "ad-to"), grain: valueOf(el, "ad-grain"), kind: ctx.query.kind }));
    };
    el.onchange = (ev) => { if (ev.target && ev.target.id === "ad-kind") go(hashFor("analytics", { ...ctx.query, kind: ev.target.value, offset: "" })); };
  }

  // ---------- curriculum home ----------
  async function curriculumHome(el) {
    el.innerHTML = shell("Curriculum", "Curriculum", "Draft, validate, publish and archive. Nothing here deletes content: archive it.",
      `<div class="grid g3">${[["lessons", "📘", "Lessons", "Exercises and vocabulary"], ["situations", "🧭", "Situations", "Steps for real-life scenes"], ["listening", "🎧", "Listening", "Activities with three options"],
        ["vocabulary", "🔤", "Vocabulary", "Words, phrases and translations"], ["topics", "🏷️", "Topics", "Names and icons"]].map(([k, i, t, s]) => `<a class="card hover" href="#/admin/curriculum/${k}" style="text-decoration:none;color:inherit;display:block"><div style="font-size:26px">${i}</div><b>${t}</b><div class="muted">${s}</div></a>`).join("")}</div>
       <div class="card" style="margin-top:14px"><div class="row between"><b>Integrity check</b><button class="btn btn-primary btn-sm" data-act="sweep">Run check</button></div><div id="ad-sweep" class="muted" style="margin-top:8px">Checks every lesson, situation and listening activity against the publish rules, plus the whole database.</div></div>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t || t.dataset.act !== "sweep") return;
      const out = el.querySelector("#ad-sweep"); out.innerHTML = "Checking…";
      const r = await get("/api/admin/validate/all");
      out.innerHTML = r.ok ? `<b>${r.data.ok ? "✓ Passes" : "✗ Problems found"}</b> · ${r.data.errors} errors, ${r.data.warnings} warnings · checked ${Object.keys(r.data.checked).map((k) => r.data.checked[k] + " " + PLURAL[k]).join(", ")}${findings(r.data.findings.slice(0, 50), false)}` : errorBox(r, "the check");
    };
  }

  // ---------- unit lists (lessons / situations / listening) ----------
  const UNITS = {
    lessons: { api: "lessons", singular: "lesson", entity: "lesson", title: "Lessons", icon: "📘", extra: ["Exercises", (i) => i.exercises, "Vocabulary", (i) => i.vocabulary] },
    situations: { api: "situations", singular: "situation", entity: "situation", title: "Situations", icon: "🧭", extra: ["Steps", (i) => i.steps] },
    listening: { api: "listening", singular: "activity", entity: "listening_activity", title: "Listening", icon: "🎧", extra: ["Options", (i) => i.options] },
  };

  async function unitList(el, ctx, kind) {
    const u = UNITS[kind], q = ctx.query, off = parseInt(q.offset || "0", 10) || 0;
    const params = ["status", "language", "cefr", "q"].filter((k) => q[k]).map((k) => `${k}=${encodeURIComponent(q[k])}`).concat([`limit=${PAGE}`, `offset=${off}`]).join("&");
    const [r, langs] = await Promise.all([get(`/api/admin/content/${u.api}?${params}`), get("/api/admin/content/languages")]);
    if (!alive(el)) return;
    if (!r.ok) { el.innerHTML = shell("Curriculum", u.title, "", errorBox(r, u.title.toLowerCase())); return; }
    const languages = langs.ok ? langs.data.items : [];
    const filters = `<div class="card ad-filters" style="margin-bottom:12px"><div class="row" style="gap:8px;flex-wrap:wrap">
      <select id="f-status">${opts(["draft", "published", "archived"], q.status, "Any status")}</select><select id="f-language">${opts(languages.map((l) => [l.code, l.name]), q.language, "Any language")}</select>
      <select id="f-cefr">${opts(["A1", "A2", "B1", "B2", "C1", "C2"], q.cefr, "Any level")}</select><input id="f-q" class="pc-in" placeholder="Search title or slug" value="${esc(q.q || "")}" />
      <button class="btn btn-primary btn-sm" data-act="filter">Filter</button><button class="btn btn-ghost btn-sm" data-act="clear">Clear</button></div></div>`;
    const extraCols = u.extra.filter((_, i) => i % 2 === 0), extraFns = u.extra.filter((_, i) => i % 2 === 1);
    const rows = r.data.items.map((i) => `<tr data-id="${i.id}">${cell(`<a href="#/admin/curriculum/${kind}/${i.id}"><b>${esc(i.title)}</b></a><div class="muted" style="font-size:12px">${esc(i.slug)}</div>`)}${cell(badge(i.status))}${cell(esc(i.language) + " · " + esc(i.cefr))}${extraFns.map((f) => cell(num(f(i)))).join("")}${cell("r" + i.revision)}${cell(esc((i.updated_at || "").slice(0, 10)))}</tr>`);
    const create = `<details class="card" style="margin-top:12px" id="ad-create"><summary><b>＋ New ${esc(u.singular)}</b> <span class="muted">(created as a draft)</span></summary><div id="ad-create-form">${createForm(kind, languages)}</div><div class="muted" id="ad-create-msg" style="margin-top:8px"></div></details>`;
    el.innerHTML = shell("Curriculum", u.title, "Drafts are invisible to learners until published.", filters + (rows.length ? table(["Title", "Status", "Language · level", ...extraCols, "Revision", "Updated"], rows) + pager("curriculum/" + kind, q, r.data.total, r.data.limit, r.data.offset) : empty("Nothing matches these filters.")) + create,
      `<a class="btn btn-ghost" href="#/admin/curriculum">← Curriculum</a>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      const a = t.dataset.act;
      if (a === "retry") mount();
      else if (a === "filter") go(hashFor("curriculum/" + kind, { status: valueOf(el, "f-status"), language: valueOf(el, "f-language"), cefr: valueOf(el, "f-cefr"), q: valueOf(el, "f-q") }));
      else if (a === "clear") go(hashFor("curriculum/" + kind, {}));
      else if (a === "create") {
        const body = createBody(kind, el), msg = el.querySelector("#ad-create-msg");
        const res = await call("POST", `/api/admin/content/${u.api}`, body);
        if (res.ok) go(`#/admin/curriculum/${kind}/${res.data.id}`); else msg.textContent = problem(res);
      }
    };
  }
  const problem = (res) => detailText(res) || (res.status === 0 ? "Network error: try again." : "Something went wrong.");
  const field = (id, label, input, hint) => `<label class="ad-field"><span>${esc(label)}</span>${input}${hint ? `<small class="muted">${esc(hint)}</small>` : ""}</label>`;
  const text = (id, value, ph) => `<input id="${id}" class="pc-in" value="${esc(value == null ? "" : value)}" ${ph ? `placeholder="${esc(ph)}"` : ""} />`;
  const area = (id, value, rows) => `<textarea id="${id}" class="pc-in" rows="${rows || 3}">${esc(value == null ? "" : value)}</textarea>`;
  const select = (id, values, selected) => `<select id="${id}">${opts(values, selected)}</select>`;
  const AGE = ["child", "teen", "adult"];

  function createForm(kind, languages) {
    const lang = field("c-language", "Language", select("c-language", languages.map((l) => [l.code, l.name]), "hi")), cefr = field("c-cefr", "CEFR level", select("c-cefr", ["A1", "A2", "B1", "B2", "C1", "C2"], "A1"));
    const common = field("c-slug", "Slug", text("c-slug", "", "lowercase-with-hyphens")) + lang + cefr + field("c-title", "Title", text("c-title", ""));
    const ages = field("c-ages", "Age groups", text("c-ages", "", "blank = everyone; or child, teen, adult"), "comma separated");
    const submit = `<button class="btn btn-primary" data-act="create">Create draft</button>`;
    if (kind === "lessons") return `<div class="ad-form">${common}${field("c-description", "Description", area("c-description", ""))}${field("c-topics", "Topics", text("c-topics", "", "food, greetings"), "topic slugs, comma separated")}${ages}${submit}</div>`;
    if (kind === "situations") return `<div class="ad-form">${common}${field("c-description", "Description", area("c-description", ""))}${field("c-topic", "Topic", text("c-topic", "", "food"))}${field("c-difficulty", "Difficulty (1–5)", text("c-difficulty", "1"))}${ages}${submit}</div>`;
    return `<div class="ad-form">${common}${field("c-prompt", "Prompt", area("c-prompt", "Listen, then choose."))}${field("c-topic", "Topic", text("c-topic", "", "food"))}${field("c-mode", "Mode", select("c-mode", ["choose_meaning", "choose_phrase"], "choose_meaning"))}
      ${field("c-item", "Target vocabulary item id", text("c-item", ""))}${field("c-difficulty", "Difficulty (1–3)", text("c-difficulty", "1"))}${ages}${submit}</div>`;
  }
  const csv = (t) => t.split(",").map((s) => s.trim()).filter(Boolean);
  function createBody(kind, el) {
    const base = { slug: valueOf(el, "c-slug"), language: valueOf(el, "c-language"), cefr: valueOf(el, "c-cefr"), title: valueOf(el, "c-title"), age_groups: csv(valueOf(el, "c-ages")) };
    if (kind === "lessons") return { ...base, description: valueOf(el, "c-description"), topics: csv(valueOf(el, "c-topics")) };
    if (kind === "situations") return { ...base, description: valueOf(el, "c-description"), topic: valueOf(el, "c-topic"), difficulty: intOrNull(valueOf(el, "c-difficulty")) || 1 };
    return { ...base, prompt: valueOf(el, "c-prompt"), topic: valueOf(el, "c-topic"), mode: valueOf(el, "c-mode"), item_id: intOrNull(valueOf(el, "c-item")), difficulty: intOrNull(valueOf(el, "c-difficulty")) || 1 };
  }

  // ---------- unit detail / editor ----------
  const answersText = (answers) => answers.map((a) => (a.is_correct ? "* " : "  ") + a.text).join("\n");
  function parseAnswers(t, existing) {
    // one answer per line; a leading "* " marks the correct one. Existing answers keep their id (matched by position), so they are corrected in place.
    return t.split("\n").map((l) => l.replace(/\s+$/, "")).filter((l) => l.trim()).map((l, i) => {
      const star = /^\s*\*\s?/.test(l), a = { text: l.replace(/^\s*\*\s?/, "").trim(), is_correct: star };
      if (existing && existing[i]) a.id = existing[i].id;
      return a;
    });
  }
  const typedKind = (k) => k === "translation" || k === "fill_blank" || k === "translate" || k === "conversation";
  function answersFor(kind, t, existing) {
    const list = parseAnswers(t, existing);
    return typedKind(kind) ? list.map((a) => ({ ...a, is_correct: true })) : list;
  }

  function actionBar(entity, unit) {
    const s = unit.status, b = (act, label, cls) => `<button class="btn ${cls || "btn-ghost"} btn-sm" data-act="${act}">${label}</button>`;
    return `<div class="row" style="gap:8px;flex-wrap:wrap">${b("validate", "Validate")}${s === "draft" ? b("publish", "Publish", "btn-primary") : ""}${s === "published" ? b("unpublish", "Unpublish") : ""}${s !== "archived" ? b("archive", "Archive") : ""}${s === "archived" ? b("restore", "Restore to draft") : ""}</div>`;
  }
  const readOnlyNote = (unit) => unit.status === "draft" ? "" : `<div class="card ad-note" data-readonly="${esc(unit.status)}"><b>${unit.status === "published" ? "Published content can't be edited." : "Archived content can't be edited."}</b> <span class="muted">${unit.status === "published" ? "Unpublish it to make it a draft, edit, then validate and publish again. Learners keep all their progress." : "Restore it to a draft first. It is validated again before it can be published."}</span></div>`;

  async function unitDetail(el, ctx, kind, id) {
    const u = UNITS[kind];
    const r = await get(`/api/admin/content/${u.api}/${encodeURIComponent(id)}`);
    if (!alive(el)) return;
    if (!r.ok) { el.innerHTML = shell("Curriculum", u.title, "", errorBox(r, u.singular)); return; }
    let unit = r.data, panel = "", banner = "", msg = "";
    const draw = () => {
      const editable = unit.status === "draft";
      el.innerHTML = shell("Curriculum · " + u.title, unit.title, `${unit.slug} · ${unit.language.name} · ${unit.cefr}`,
        `<div class="row between" style="margin-bottom:12px"><span class="row" style="gap:10px">${badge(unit.status)}<span class="muted">revision ${unit.revision}${unit.published_at ? " · published " + esc(unit.published_at.slice(0, 10)) : ""}${unit.archived_at ? " · archived " + esc(unit.archived_at.slice(0, 10)) : ""}</span></span>${actionBar(u.entity, unit)}</div>
         ${banner}<div id="ad-panel">${panel}</div>${readOnlyNote(unit)}${body(kind, unit, editable)}<div class="muted" id="ad-msg" style="margin-top:10px">${esc(msg)}</div>`,
        `<a class="btn btn-ghost" href="#/admin/curriculum/${kind}">← ${u.title}</a>`);
    };
    const reload = async () => { const x = await get(`/api/admin/content/${u.api}/${encodeURIComponent(id)}`); if (x.ok) { unit = x.data; banner = ""; } else { banner = errorBox(x, u.singular); } };
    const conflict = (res) => (res.status === 409 && res.data && res.data.detail && res.data.detail.code === "stale_revision")
      ? `<div class="card ad-conflict" data-conflict="1"><b>This ${esc(u.singular)} changed while you were editing.</b> <span class="muted">${esc(res.data.detail.message)}</span> <button class="btn btn-primary btn-sm" data-act="reload">Reload latest</button></div>` : null;

    const write = async (method, url, payload, ok) => {
      const res = await call(method, url, payload);
      if (res.ok) { msg = ok || "Saved ✓"; banner = ""; if (res.data && res.data.revision != null && res.data.id == null) unit = { ...unit, revision: res.data.revision }; await reload(); panel = ""; draw(); return res; }
      const c = conflict(res);
      if (c) { banner = c; msg = ""; draw(); return res; }
      msg = problem(res); draw(); return res;
    };

    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      const a = t.dataset.act, base = `/api/admin/content/${u.api}/${unit.id}`;
      if (a === "retry") mount();
      else if (a === "reload") { await reload(); msg = "Reloaded the latest version."; draw(); }
      else if (a === "validate") { const res = await call("POST", `/api/admin/validate/${u.entity}/${unit.id}`, {}); panel = res.ok ? findings(res.data.findings, true) : errorBox(res, "validation"); draw(); }
      else if (a === "publish" || a === "unpublish" || a === "restore") {
        const res = await call("POST", `/api/admin/${a}/${u.entity}/${unit.id}`, { revision: unit.revision });
        if (res.ok) { msg = a === "publish" ? "Published ✓" : a === "unpublish" ? "Unpublished: it is a draft again." : "Restored to a draft."; panel = a === "publish" && res.data.warnings.length ? findings(res.data.warnings, false) : ""; await reload(); draw(); }
        else if (res.status === 422 && res.data && res.data.detail && res.data.detail.findings) { panel = findings(res.data.detail.findings, false); msg = "Publishing was blocked by validation."; draw(); }
        else { const c = conflict(res); if (c) banner = c; msg = c ? "" : problem(res); draw(); }
      } else if (a === "archive") {
        if (window.confirm && !window.confirm(`Archive “${unit.title}”? Learners will no longer see it or get it in new plans. Their progress and history are kept, and you can restore it later.`)) return;
        const res = await call("POST", `/api/admin/archive/${u.entity}/${unit.id}`, { revision: unit.revision });
        if (res.ok) { msg = "Archived. Learner history is untouched."; panel = ""; await reload(); draw(); } else { const c = conflict(res); if (c) banner = c; msg = c ? "" : problem(res); draw(); }
      } else if (a === "save-meta") await write("PATCH", base, { revision: unit.revision, ...metaBody(kind, el) });
      else if (a === "save-vocab") await write("PUT", base + "/vocabulary", { revision: unit.revision, item_ids: csv(valueOf(el, "e-vocab")).map((x) => parseInt(x, 10)).filter((x) => !isNaN(x)) });
      else if (a === "add-exercise") await write("POST", base + "/exercises", { revision: unit.revision, kind: valueOf(el, "n-kind"), prompt: valueOf(el, "n-prompt"), item_id: intOrNull(valueOf(el, "n-item")), difficulty: intOrNull(valueOf(el, "n-difficulty")) || 1, answers: answersFor(valueOf(el, "n-kind"), valueOf(el, "n-answers")) }, "Exercise added ✓");
      else if (a === "save-exercise") {
        const ex = unit.exercises.find((x) => String(x.id) === t.dataset.id);
        await write("PATCH", base + "/exercises/" + ex.id, { revision: unit.revision, prompt: valueOf(el, "x-prompt-" + ex.id), item_id: intOrNull(valueOf(el, "x-item-" + ex.id)), difficulty: intOrNull(valueOf(el, "x-difficulty-" + ex.id)) || 1, answers: answersFor(ex.kind, valueOf(el, "x-answers-" + ex.id), ex.answers) }, "Exercise saved ✓");
      } else if (a === "add-step") await write("POST", base + "/steps", { revision: unit.revision, kind: valueOf(el, "n-kind"), prompt: valueOf(el, "n-prompt") || null, prompt_meaning: valueOf(el, "n-meaning") || null, item_id: intOrNull(valueOf(el, "n-item")), answers: answersFor(valueOf(el, "n-kind"), valueOf(el, "n-answers")) }, "Step added ✓");
      else if (a === "save-step") {
        const st = unit.steps.find((x) => String(x.id) === t.dataset.id);
        const payload = { revision: unit.revision, prompt_meaning: valueOf(el, "x-meaning-" + st.id) || null, item_id: intOrNull(valueOf(el, "x-item-" + st.id)) };
        if (st.kind !== "learn_phrase") { payload.prompt = valueOf(el, "x-prompt-" + st.id); payload.answers = answersFor(st.kind, valueOf(el, "x-answers-" + st.id), st.answers); }
        await write("PATCH", base + "/steps/" + st.id, payload, "Step saved ✓");
      } else if (a === "add-option") await write("POST", base + "/options", { revision: unit.revision, item_id: intOrNull(valueOf(el, "n-item")) }, "Option added ✓");
      else if (a === "save-option") await write("PATCH", base + "/options/" + t.dataset.id, { revision: unit.revision, item_id: intOrNull(valueOf(el, "x-item-" + t.dataset.id)) }, "Option saved ✓");
    };
    draw();
  }

  function metaForm(kind, unit) {
    const ages = field("e-ages", "Age groups", text("e-ages", unit.age_groups.join(", "), "blank = everyone"), "child, teen, adult");
    const common = field("e-slug", "Slug", text("e-slug", unit.slug)) + field("e-title", "Title", text("e-title", unit.title)) + field("e-cefr", "CEFR level", select("e-cefr", ["A1", "A2", "B1", "B2", "C1", "C2"], unit.cefr)) + field("e-sort", "Position at this level", text("e-sort", unit.sort_order));
    let more = "";
    if (kind === "lessons") more = field("e-description", "Description", area("e-description", unit.description)) + field("e-situation", "Situation", area("e-situation", unit.situation, 2)) + field("e-tip", "Tip", area("e-tip", unit.tip, 2)) + field("e-topics", "Topics", text("e-topics", unit.topics.map((t) => t.slug).join(", ")), "topic slugs");
    else if (kind === "situations") more = field("e-description", "Description", area("e-description", unit.description)) + field("e-goal", "Goal", text("e-goal", unit.goal)) + field("e-setting", "Setting", text("e-setting", unit.setting)) + field("e-pname", "Partner name", text("e-pname", unit.partner_name)) + field("e-prole", "Partner role", text("e-prole", unit.partner_role)) + field("e-topic", "Topic", text("e-topic", unit.topic)) + field("e-difficulty", "Difficulty (1–5)", text("e-difficulty", unit.difficulty));
    else more = field("e-prompt", "Prompt", area("e-prompt", unit.prompt)) + field("e-mode", "Mode", select("e-mode", ["choose_meaning", "choose_phrase"], unit.mode)) + field("e-topic", "Topic", text("e-topic", unit.topic)) + field("e-item", "Target vocabulary item id", text("e-item", unit.target.item_id)) + field("e-difficulty", "Difficulty (1–3)", text("e-difficulty", unit.difficulty));
    return `<div class="card" style="margin-bottom:12px"><b>Details</b><div class="ad-form">${common}${more}${ages}<button class="btn btn-primary" data-act="save-meta">Save changes</button></div></div>`;
  }
  function metaBody(kind, el) {
    const b = { slug: valueOf(el, "e-slug"), title: valueOf(el, "e-title"), cefr: valueOf(el, "e-cefr"), sort_order: intOrNull(valueOf(el, "e-sort")), age_groups: csv(valueOf(el, "e-ages")) };
    if (kind === "lessons") return { ...b, description: valueOf(el, "e-description"), situation: valueOf(el, "e-situation") || null, tip: valueOf(el, "e-tip") || null, topics: csv(valueOf(el, "e-topics")) };
    if (kind === "situations") return { ...b, description: valueOf(el, "e-description"), goal: valueOf(el, "e-goal") || null, setting: valueOf(el, "e-setting") || null, partner_name: valueOf(el, "e-pname") || null, partner_role: valueOf(el, "e-prole") || null, topic: valueOf(el, "e-topic"), difficulty: intOrNull(valueOf(el, "e-difficulty")) || 1 };
    return { ...b, prompt: valueOf(el, "e-prompt"), mode: valueOf(el, "e-mode"), topic: valueOf(el, "e-topic"), item_id: intOrNull(valueOf(el, "e-item")), difficulty: intOrNull(valueOf(el, "e-difficulty")) || 1 };
  }
  const ANSWER_HINT = "One per line. Start the correct one with “* ”. Typed answers list every accepted form. Answers can be corrected, never removed.";
  const answersList = (answers) => `<ul class="ad-list">${answers.map((a) => `<li>${a.is_correct ? "✅" : "▫️"} ${esc(a.text)}</li>`).join("")}</ul>`;

  function body(kind, unit, editable) {
    if (kind === "lessons") {
      const vocab = `<div class="card" style="margin-bottom:12px"><b>Vocabulary</b>${unit.vocabulary.length ? `<ul class="ad-list">${unit.vocabulary.map((v) => `<li><code>#${v.item_id}</code> ${esc(v.text)} <span class="muted">${esc(v.meaning_en || "no English translation")}</span></li>`).join("")}</ul>` : `<div class="muted" style="margin:6px 0">No vocabulary yet.</div>`}
        ${editable ? `<div class="ad-form">${field("e-vocab", "Vocabulary item ids (in order)", text("e-vocab", unit.vocabulary.map((v) => v.item_id).join(", ")), "browse ids under Vocabulary")}<button class="btn btn-ghost btn-sm" data-act="save-vocab">Save vocabulary</button></div>` : ""}</div>`;
      const ex = unit.exercises.map((e) => `<div class="card" style="margin-bottom:10px" data-exercise="${e.id}"><div class="row between"><b>${e.sort_order}. ${esc(e.prompt)}</b><span class="chip">${esc(e.kind)} · difficulty ${e.difficulty}</span></div>
        ${editable ? `<div class="ad-form">${field("x-prompt-" + e.id, "Prompt", text("x-prompt-" + e.id, e.prompt))}${field("x-item-" + e.id, "Vocabulary item id", text("x-item-" + e.id, e.item_id))}${field("x-difficulty-" + e.id, "Difficulty (1–3)", text("x-difficulty-" + e.id, e.difficulty))}${field("x-answers-" + e.id, "Answers", area("x-answers-" + e.id, answersText(e.answers), 4), ANSWER_HINT)}<button class="btn btn-ghost btn-sm" data-act="save-exercise" data-id="${e.id}">Save exercise</button></div>` : answersList(e.answers)}</div>`).join("");
      const add = editable ? `<div class="card"><b>Add an exercise</b><div class="ad-form">${field("n-kind", "Kind", select("n-kind", ["multiple_choice", "translation", "fill_blank"], "multiple_choice"))}${field("n-prompt", "Prompt", text("n-prompt", ""))}${field("n-item", "Vocabulary item id", text("n-item", ""))}${field("n-difficulty", "Difficulty (1–3)", text("n-difficulty", "1"))}${field("n-answers", "Answers", area("n-answers", "* Right answer\n  Wrong answer", 4), ANSWER_HINT)}<button class="btn btn-primary btn-sm" data-act="add-exercise">Add exercise</button></div></div>` : "";
      return (editable ? metaForm(kind, unit) : metaView(kind, unit)) + vocab + `<h3>Exercises (${unit.exercises.length})</h3>` + (ex || empty("No exercises yet: a lesson needs at least one to be published.")) + add;
    }
    if (kind === "situations") {
      const steps = unit.steps.map((s) => `<div class="card" style="margin-bottom:10px" data-step="${s.id}"><div class="row between"><b>${s.sort_order}. ${esc(s.prompt || "Learn a phrase")}</b><span class="chip">${esc(s.kind)}</span></div>
        ${editable ? `<div class="ad-form">${s.kind === "learn_phrase" ? "" : field("x-prompt-" + s.id, "Prompt", text("x-prompt-" + s.id, s.prompt))}${field("x-meaning-" + s.id, "Meaning", text("x-meaning-" + s.id, s.prompt_meaning))}${field("x-item-" + s.id, "Vocabulary item id", text("x-item-" + s.id, s.item_id))}${s.kind === "learn_phrase" ? "" : field("x-answers-" + s.id, "Answers", area("x-answers-" + s.id, answersText(s.answers), 3), ANSWER_HINT)}<button class="btn btn-ghost btn-sm" data-act="save-step" data-id="${s.id}">Save step</button></div>` : answersList(s.answers)}</div>`).join("");
      const add = editable ? `<div class="card"><b>Add a step</b><div class="ad-form">${field("n-kind", "Kind", select("n-kind", ["learn_phrase", "choose_response", "translate", "fill_blank", "conversation"], "choose_response"))}${field("n-prompt", "Prompt", text("n-prompt", ""))}${field("n-meaning", "Meaning", text("n-meaning", ""))}${field("n-item", "Vocabulary item id", text("n-item", ""), "required for learn_phrase")}${field("n-answers", "Answers", area("n-answers", "* Good reply\n  Other reply", 3), ANSWER_HINT)}<button class="btn btn-primary btn-sm" data-act="add-step">Add step</button></div></div>` : "";
      return (editable ? metaForm(kind, unit) : metaView(kind, unit)) + `<h3>Steps (${unit.steps.length})</h3>` + (steps || empty("No steps yet: a situation needs at least one to be published.")) + add;
    }
    const opts_ = unit.options.map((o) => `<div class="card" style="margin-bottom:10px" data-option="${o.id}"><div class="row between"><b>${o.sort_order}. ${esc(o.text || "item " + o.item_id)}</b><span class="chip ${o.is_target ? "ok" : ""}">${o.is_target ? "correct answer" : "distractor"}</span></div><div class="muted">${esc(o.meaning_en || "")}</div>
      ${editable ? `<div class="ad-form">${field("x-item-" + o.id, "Vocabulary item id", text("x-item-" + o.id, o.item_id))}<button class="btn btn-ghost btn-sm" data-act="save-option" data-id="${o.id}">Save option</button></div>` : ""}</div>`).join("");
    const add = editable && unit.options.length < 3 ? `<div class="card"><b>Add an option</b><div class="ad-form">${field("n-item", "Vocabulary item id", text("n-item", ""))}<button class="btn btn-primary btn-sm" data-act="add-option">Add option</button></div></div>` : "";
    return (editable ? metaForm(kind, unit) : metaView(kind, unit)) + `<h3>Options (${unit.options.length} of 3)</h3>` + (opts_ || empty("No options yet: an activity offers exactly three.")) + add;
  }
  function metaView(kind, unit) {
    const rows = [["Slug", unit.slug], ["Position", unit.sort_order], ["Age groups", unit.age_groups.length ? unit.age_groups.join(", ") : "everyone"]];
    if (kind === "lessons") rows.push(["Description", unit.description], ["Topics", unit.topics.map((t) => t.name).join(", ") || "–"]);
    if (kind === "situations") rows.push(["Description", unit.description], ["Topic", unit.topic], ["Difficulty", unit.difficulty], ["Partner", unit.partner_name ? unit.partner_name + " (" + unit.partner_role + ")" : "–"]);
    if (kind === "listening") rows.push(["Prompt", unit.prompt], ["Mode", unit.mode], ["Topic", unit.topic], ["Target", unit.target.text || "item " + unit.target.item_id], ["Difficulty", unit.difficulty]);
    return `<div class="card" style="margin-bottom:12px"><b>Details</b><table class="ad-kv">${rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v == null ? "–" : v)}</td></tr>`).join("")}</table></div>`;
  }

  // ---------- vocabulary ----------
  async function vocabulary(el, ctx) {
    const q = ctx.query, off = parseInt(q.offset || "0", 10) || 0;
    const params = ["language", "cefr", "kind", "q"].filter((k) => q[k]).map((k) => `${k}=${encodeURIComponent(q[k])}`).concat([`limit=${PAGE}`, `offset=${off}`]).join("&");
    const [r, langs, detail] = await Promise.all([get(`/api/admin/content/vocabulary?${params}`), get("/api/admin/content/languages"), q.item ? get(`/api/admin/content/vocabulary/${encodeURIComponent(q.item)}`) : Promise.resolve(null)]);
    if (!alive(el)) return;
    if (!r.ok) { el.innerHTML = shell("Curriculum", "Vocabulary", "", errorBox(r, "vocabulary")); return; }
    const languages = langs.ok ? langs.data.items : [];
    const filters = `<div class="card" style="margin-bottom:12px"><div class="row" style="gap:8px;flex-wrap:wrap"><select id="f-language">${opts(languages.map((l) => [l.code, l.name]), q.language, "Any language")}</select>
      <select id="f-cefr">${opts(["A1", "A2", "B1", "B2", "C1", "C2"], q.cefr, "Any level")}</select><select id="f-kind">${opts(["word", "phrase"], q.kind, "Word or phrase")}</select><input id="f-q" class="pc-in" placeholder="Search text or pronunciation" value="${esc(q.q || "")}" />
      <button class="btn btn-primary btn-sm" data-act="filter">Filter</button><button class="btn btn-ghost btn-sm" data-act="clear">Clear</button></div></div>`;
    const rows = r.data.items.map((i) => `<tr data-id="${i.id}">${cell("#" + i.id)}${cell(`<a href="${hashFor("curriculum/vocabulary", { ...q, item: i.id })}"><b>${esc(i.text)}</b></a><div class="muted" style="font-size:12px">${esc(i.pronunciation || "")}</div>`)}${cell(esc(i.language) + " · " + esc(i.cefr))}${cell(esc(i.kind))}${cell(i.has_english ? "✓" : `<span class="chip warn">no English</span>`)}</tr>`);
    const create = `<details class="card" style="margin-top:12px"><summary><b>＋ New vocabulary item</b></summary><div class="ad-form">${field("c-language", "Language", select("c-language", languages.map((l) => [l.code, l.name]), "hi"))}${field("c-cefr", "CEFR level", select("c-cefr", ["A1", "A2", "B1", "B2", "C1", "C2"], "A1"))}${field("c-kind", "Kind", select("c-kind", ["word", "phrase"], "word"))}${field("c-text", "Text", text("c-text", ""))}${field("c-pron", "Pronunciation guide", text("c-pron", ""))}${field("c-english", "English meaning", text("c-english", ""), "needed before it can appear in published content")}<button class="btn btn-primary" data-act="create-vocab">Create</button></div><div class="muted" id="ad-create-msg"></div></details>`;
    let panel = "";
    if (detail) panel = detail.ok ? vocabPanel(detail.data) : errorBox(detail, "that item");
    el.innerHTML = shell("Curriculum", "Vocabulary", "Shared by lessons, situations and listening. While anything uses an item its level, kind and meaning are locked; translations can always be added.",
      filters + panel + (rows.length ? table(["Id", "Text", "Language · level", "Kind", "English"], rows) + pager("curriculum/vocabulary", q, r.data.total, r.data.limit, r.data.offset) : empty("No vocabulary matches these filters.")) + create, `<a class="btn btn-ghost" href="#/admin/curriculum">← Curriculum</a>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      const a = t.dataset.act, msg = el.querySelector("#ad-create-msg") || el.querySelector("#ad-vmsg");
      if (a === "retry") mount();
      else if (a === "filter") go(hashFor("curriculum/vocabulary", { language: valueOf(el, "f-language"), cefr: valueOf(el, "f-cefr"), kind: valueOf(el, "f-kind"), q: valueOf(el, "f-q") }));
      else if (a === "clear") go(hashFor("curriculum/vocabulary", {}));
      else if (a === "create-vocab") {
        const english = valueOf(el, "c-english");
        const res = await call("POST", "/api/admin/content/vocabulary", { language: valueOf(el, "c-language"), cefr: valueOf(el, "c-cefr"), kind: valueOf(el, "c-kind"), text: valueOf(el, "c-text"), pronunciation: valueOf(el, "c-pron") || null, translations: english ? [{ language: "en", meaning: english }] : [] });
        if (res.ok) go(hashFor("curriculum/vocabulary", { item: res.data.id })); else msg.textContent = problem(res);
      } else if (a === "save-vocab-item") {
        const res = await call("PATCH", `/api/admin/content/vocabulary/${t.dataset.id}`, { text: valueOf(el, "v-text"), pronunciation: valueOf(el, "v-pron") || null, cefr: valueOf(el, "v-cefr"), kind: valueOf(el, "v-kind") });
        if (res.ok) mount(); else el.querySelector("#ad-vmsg").textContent = problem(res);
      } else if (a === "save-translation") {
        const res = await call("PUT", `/api/admin/content/vocabulary/${t.dataset.id}/translations/${encodeURIComponent(valueOf(el, "v-tlang"))}`, { meaning: valueOf(el, "v-tmeaning"), natural: valueOf(el, "v-tnatural") || null });
        if (res.ok) mount(); else el.querySelector("#ad-vmsg").textContent = problem(res);
      }
    };
  }
  function vocabPanel(v) {
    return `<div class="card" style="margin-bottom:12px" data-vocab="${v.id}"><div class="row between"><b>#${v.id} · ${esc(v.text)}</b><span class="chip ${v.referenced ? "warn" : ""}">${v.referenced ? "in use: level and kind locked" : "unused"}</span></div>
      <div class="muted">used by ${v.usage.lessons} lessons, ${v.usage.situations} situations, ${v.usage.listening_activities} listening activities${v.used_by_published ? " · published content uses it" : ""}</div>
      <table class="ad-kv">${v.translations.map((t) => `<tr><td>${esc(t.language)}</td><td>${esc(t.meaning)}${t.natural ? ` <span class="muted">· ${esc(t.natural)}</span>` : ""}</td></tr>`).join("") || `<tr><td colspan="2" class="muted">No translations yet.</td></tr>`}</table>
      <div class="ad-form">${field("v-text", "Text", text("v-text", v.text))}${field("v-pron", "Pronunciation guide", text("v-pron", v.pronunciation))}${field("v-cefr", "CEFR level", select("v-cefr", ["A1", "A2", "B1", "B2", "C1", "C2"], v.cefr))}${field("v-kind", "Kind", select("v-kind", ["word", "phrase"], v.kind))}<button class="btn btn-ghost btn-sm" data-act="save-vocab-item" data-id="${v.id}">Save item</button></div>
      <div class="ad-form">${field("v-tlang", "Translation language", text("v-tlang", "en"), "language code")}${field("v-tmeaning", "Meaning", text("v-tmeaning", ""))}${field("v-tnatural", "Natural phrasing", text("v-tnatural", ""))}<button class="btn btn-ghost btn-sm" data-act="save-translation" data-id="${v.id}">Add / update translation</button></div><div class="muted" id="ad-vmsg"></div></div>`;
  }

  // ---------- topics ----------
  async function topics(el) {
    const r = await get("/api/admin/content/topics");
    if (!alive(el)) return;
    if (!r.ok) { el.innerHTML = shell("Curriculum", "Topics", "", errorBox(r, "topics")); return; }
    const rows = r.data.items.map((t) => `<tr data-topic="${esc(t.slug)}">${cell(esc(t.icon))}${cell(`<input id="t-name-${t.id}" class="pc-in" value="${esc(t.name)}" />`)}${cell(`<input id="t-icon-${t.id}" class="pc-in" value="${esc(t.icon)}" style="width:70px" />`)}${cell(esc(t.slug))}${cell(`${t.lessons} / ${t.situations} / ${t.listening_activities}`)}${cell(`<button class="btn btn-ghost btn-sm" data-act="save-topic" data-id="${t.id}">Save</button>`)}</tr>`);
    el.innerHTML = shell("Curriculum", "Topics", "A topic's slug never changes; its name and icon can.", (rows.length ? table(["", "Name", "Icon", "Slug", "Lessons / situations / listening", ""], rows) : empty("No topics yet.")) +
      `<div class="card" style="margin-top:12px"><b>New topic</b><div class="ad-form">${field("n-slug", "Slug", text("n-slug", ""))}${field("n-name", "Name", text("n-name", ""))}${field("n-icon", "Icon", text("n-icon", ""))}<button class="btn btn-primary" data-act="create-topic">Create</button></div><div class="muted" id="ad-msg"></div></div>`, `<a class="btn btn-ghost" href="#/admin/curriculum">← Curriculum</a>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      const msg = el.querySelector("#ad-msg");
      if (t.dataset.act === "retry") mount();
      else if (t.dataset.act === "create-topic") { const res = await call("POST", "/api/admin/content/topics", { slug: valueOf(el, "n-slug"), name: valueOf(el, "n-name"), icon: valueOf(el, "n-icon") }); if (res.ok) mount(); else msg.textContent = problem(res); }
      else if (t.dataset.act === "save-topic") { const res = await call("PATCH", `/api/admin/content/topics/${t.dataset.id}`, { name: valueOf(el, "t-name-" + t.dataset.id), icon: valueOf(el, "t-icon-" + t.dataset.id) }); if (res.ok) msg.textContent = "Saved ✓"; else msg.textContent = problem(res); }
    };
  }

  // ---------- learners ----------
  async function learners(el, ctx) {
    const q = ctx.query, off = parseInt(q.offset || "0", 10) || 0;
    const params = ["language", "cefr", "age_group", "active_since"].filter((k) => q[k]).map((k) => `${k}=${encodeURIComponent(q[k])}`).concat([`limit=${PAGE}`, `offset=${off}`]).join("&");
    const r = await get(`/api/admin/learners?${params}`);
    if (!alive(el)) return;
    const filters = `<div class="card" style="margin-bottom:12px"><div class="row" style="gap:8px;flex-wrap:wrap"><input id="f-language" class="pc-in" placeholder="Language code" value="${esc(q.language || "")}" style="width:130px" /><select id="f-cefr">${opts(["A1", "A2", "B1", "B2", "C1", "C2"], q.cefr, "Any level")}</select>
      <select id="f-age">${opts(AGE, q.age_group, "Any age group")}</select><input id="f-since" class="pc-in" placeholder="Active since YYYY-MM-DD" value="${esc(q.active_since || "")}" style="width:190px" /><button class="btn btn-primary btn-sm" data-act="filter">Filter</button><button class="btn btn-ghost btn-sm" data-act="clear">Clear</button></div></div>`;
    if (!r.ok) { el.innerHTML = shell("Admin", "Learners", "", filters + errorBox(r, "learners")); bindLearners(el, q); return; }
    const note = `Aggregate, support-oriented view. Learners appear only as opaque references: no names, emails, messages or recordings, and nobody can be signed in as a learner.`;
    if (r.data.suppressed) { el.innerHTML = shell("Admin", "Learners", note, filters + `<div class="card ad-suppressed" data-state="suppressed"><b>Not shown</b><p class="muted">Fewer than 5 learners match, so no individual rows are shown.</p></div>`); bindLearners(el, q); return; }
    const rows = r.data.items.map((i) => `<tr data-ref="${esc(i.ref)}">${cell(`<a href="#/admin/learners/${esc(i.ref)}"><code>${esc(i.ref.slice(0, 10))}…</code></a>`)}${cell(esc(i.language || "–") + " · " + esc(i.cefr || "–") + " · " + esc(i.age_group || "–"))}${cell(esc(i.joined))}${cell(esc(i.last_active || "never"))}${cell(num(i.lessons_completed))}${cell(num(i.situations_completed))}${cell(num(i.exercise_attempts))}</tr>`);
    el.innerHTML = shell("Admin", "Learners", note, filters + (rows.length ? table(["Reference", "Language · level · age", "Joined", "Last active", "Lessons done", "Situations done", "Exercise attempts"], rows) + pager("learners", q, r.data.total, r.data.limit, r.data.offset) : empty("No learners match.")));
    bindLearners(el, q);
  }
  function bindLearners(el, q) {
    el.onclick = (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
      if (t.dataset.act === "retry") mount();
      else if (t.dataset.act === "clear") go(hashFor("learners", {}));
      else if (t.dataset.act === "filter") go(hashFor("learners", { language: valueOf(el, "f-language"), cefr: valueOf(el, "f-cefr"), age_group: valueOf(el, "f-age"), active_since: valueOf(el, "f-since") }));
    };
  }
  async function learnerDetail(el, ctx, ref) {
    const r = await get(`/api/admin/learners/${encodeURIComponent(ref)}`);
    if (!alive(el)) return;
    const back = `<a class="btn btn-ghost" href="#/admin/learners">← Learners</a>`;
    if (!r.ok) { el.innerHTML = shell("Admin", "Learner", "", errorBox(r, "this learner"), back); el.onclick = (ev) => { const t = ev.target.closest && ev.target.closest("button"); if (t && t.dataset.act === "retry") mount(); }; return; }
    const d = r.data;
    if (d.suppressed) { el.innerHTML = shell("Admin", "Learner", "", `<div class="card ad-suppressed" data-state="suppressed"><b>Not shown</b><p class="muted">Fewer than 5 learners are on the platform, so individual summaries are withheld.</p></div>`, back); return; }
    const t = d.totals, row = (k, v) => `<tr><td>${esc(k)}</td><td>${num(v)}</td></tr>`;
    el.innerHTML = shell("Admin", "Learner " + d.ref.slice(0, 10) + "…", `${d.language || "–"} · ${d.cefr || "–"} · ${d.age_group || "–"} · joined ${d.joined} · last active ${d.last_active || "never"}`,
      `<div class="grid g2"><div class="card"><b>Learning</b><table class="ad-kv">${row("Lessons started", t.lessons_started)}${row("Lessons completed", t.lessons_completed)}${row("Situations started", t.situations_started)}${row("Situations completed", t.situations_completed)}${row("Exercise attempts", t.exercise_attempts)}${row("Exercises right", t.exercise_correct)}${row("Listening attempts", t.listening_attempts)}${row("Listening right", t.listening_correct)}</table></div>
       <div class="card"><b>Activity</b><table class="ad-kv">${row("Speaking attempts", t.speaking_attempts)}${row("Roleplay sessions", t.roleplay_sessions_started)}${row("Roleplay completed", t.roleplay_sessions_completed)}${row("XP", t.xp_total)}${row("Achievements", t.achievements_unlocked)}${row("Active days (last 30)", t.active_days_30)}</table></div></div>
       <p class="muted" style="margin-top:12px">Numbers only. There is no way to view a learner's messages, recordings or answers, or to act as them.</p>`, back);
  }

  // ---------- audit ----------
  const ENTITY_TYPES = ["lesson", "exercise", "lesson_vocabulary", "situation", "situation_step", "listening_activity", "listening_option", "vocabulary", "vocabulary_translation", "topic"];
  const ACTIONS = ["create", "update", "publish", "unpublish", "archive", "restore", "validation_failed"];
  async function audit(el, ctx) {
    const q = ctx.query, off = parseInt(q.offset || "0", 10) || 0;
    const params = ["actor", "entity_type", "entity_id", "action", "outcome", "from", "to"].filter((k) => q[k]).map((k) => `${k}=${encodeURIComponent(q[k])}`).concat([`limit=${PAGE}`, `offset=${off}`]).join("&");
    const r = await get(`/api/admin/audit?${params}`);
    if (!alive(el)) return;
    const filters = `<div class="card" style="margin-bottom:12px"><div class="row" style="gap:8px;flex-wrap:wrap"><input id="f-actor" class="pc-in" placeholder="Actor" value="${esc(q.actor || "")}" style="width:130px" /><select id="f-entity">${opts(ENTITY_TYPES, q.entity_type, "Any entity")}</select>
      <input id="f-id" class="pc-in" placeholder="Entity id" value="${esc(q.entity_id || "")}" style="width:100px" /><select id="f-action">${opts(ACTIONS, q.action, "Any action")}</select><select id="f-outcome">${opts(["ok", "rejected"], q.outcome, "Any outcome")}</select>
      <input id="f-from" class="pc-in" placeholder="From YYYY-MM-DD" value="${esc(q.from || "")}" style="width:150px" /><input id="f-to" class="pc-in" placeholder="To YYYY-MM-DD" value="${esc(q.to || "")}" style="width:150px" /><button class="btn btn-primary btn-sm" data-act="filter">Filter</button><button class="btn btn-ghost btn-sm" data-act="clear">Clear</button></div></div>`;
    const bind = () => {
      el.onclick = (ev) => {
        const t = ev.target.closest && ev.target.closest("button"); if (!t) return;
        if (t.dataset.act === "retry") mount();
        else if (t.dataset.act === "clear") go(hashFor("audit", {}));
        else if (t.dataset.act === "filter") go(hashFor("audit", { actor: valueOf(el, "f-actor"), entity_type: valueOf(el, "f-entity"), entity_id: valueOf(el, "f-id"), action: valueOf(el, "f-action"), outcome: valueOf(el, "f-outcome"), from: valueOf(el, "f-from"), to: valueOf(el, "f-to") }));
      };
    };
    if (!r.ok) { el.innerHTML = shell("Admin", "Audit log", "", filters + errorBox(r, "the audit log")); bind(); return; }
    const meta = (m) => Object.keys(m).filter((k) => m[k] != null).map((k) => `${esc(k)}=${esc(Array.isArray(m[k]) ? m[k].join("|") : m[k])}`).join(" · ");
    const rows = r.data.items.map((e) => `<tr data-event="${e.id}">${cell(esc(e.occurred_at))}${cell(esc(e.actor))}${cell(`<b>${esc(e.action)}</b>`)}${cell(esc(e.entity_type) + (e.entity_id != null ? " #" + esc(e.entity_id) : "") + (e.entity_key ? ` <span class="muted">${esc(e.entity_key)}</span>` : ""))}${cell(`<span class="chip ${e.outcome === "ok" ? "ok" : "heart"}">${esc(e.outcome)}</span>`)}${cell(`<span class="muted" style="font-size:12px">${meta(e.meta)}</span>`)}${cell(`<code>${esc((e.request_id || "").slice(0, 8))}</code>`)}</tr>`);
    el.innerHTML = shell("Admin", "Audit log", "Append-only. Every content change and every refused publish is recorded with who made it; no answers, secrets or learner content are ever logged.",
      filters + (rows.length ? table(["Time (UTC)", "Actor", "Action", "Entity", "Outcome", "Details", "Request"], rows) + pager("audit", q, r.data.total, r.data.limit, r.data.offset) : empty("No events match.")));
    bind();
  }

  // ---------- security (Phase 14E): configuration warnings, security events (newest first, cursor), accounts (refs only) ----------
  const EVENT_TYPES = ["login_success", "login_failure", "login_throttled", "logout", "logout_all", "session_revoked", "password_changed", "password_change_failed",
    "password_change_throttled", "mfa_setup_started", "mfa_enabled", "mfa_challenge", "mfa_success", "mfa_failure", "mfa_throttled", "mfa_recovery_code_used",
    "mfa_recovery_codes_regenerated", "mfa_disabled", "mfa_disable_failed", "admin_login", "admin_access_denied_mfa"];
  const outcomeChip = (o) => `<span class="chip ${o === "ok" ? "ok" : o === "denied" ? "heart" : "warn"}">${esc(o)}</span>`;
  const shortRef = (r) => (r ? `<code title="${esc(r)}">${esc(r.slice(0, 10))}…</code>` : `<span class="muted">–</span>`);
  async function security(el, ctx) {
    const q = ctx.query, off = parseInt(q.offset || "0", 10) || 0;
    const evq = [`limit=${PAGE}`].concat(q.before ? [`before=${encodeURIComponent(q.before)}`] : []).concat(q.type ? [`type=${encodeURIComponent(q.type)}`] : []).join("&");
    const [h, ev, acc] = await Promise.all([get("/api/admin/health"), get(`/api/admin/security-events?${evq}`), get(`/api/admin/users?limit=${PAGE}&offset=${off}`)]);
    if (!alive(el)) return;
    const bad = [h, ev, acc].find((r) => !r.ok);
    if (bad) { el.innerHTML = shell("Admin", "Security", "", errorBox(bad, "security")); return; }
    const sec = h.data.security;
    const warnings = sec.warnings.length
      ? sec.warnings.map((w) => `<div class="row" style="gap:8px;margin:6px 0" data-warning="${esc(w.code)}"><span class="chip ${w.severity === "critical" ? "heart" : "warn"}">${esc(w.severity)}</span><span>${esc(w.message)}</span></div>`).join("")
      : `<p class="muted" data-state="no-warnings">No configuration warnings.</p>`;
    const flags = `<table class="ad-kv"><tr><td>Secure cookies</td><td>${sec.cookie_secure ? `<span class="chip ok">on</span>` : `<span class="chip warn">off</span>`}</td></tr>
      <tr><td>Two-factor key</td><td><span class="chip ${sec.totp_key === "valid" ? "ok" : "heart"}">${esc(sec.totp_key)}</span></td></tr>
      <tr><td>Administrators with two-factor</td><td>${num(sec.admins_with_two_factor)} of ${num(sec.admins)}</td></tr>
      <tr><td>Demo mode</td><td>${sec.demo_mode ? `<span class="chip warn">on</span>` : `<span class="chip ok">off</span>`}</td></tr></table>`;
    const evRows = ev.data.items.map((e) => `<tr>${cell(esc(e.occurred_at))}${cell(`<b>${esc(e.type)}</b>`)}${cell(outcomeChip(e.outcome))}${cell(shortRef(e.account))}
      ${cell(esc([e.method, e.reason, e.stage].filter(Boolean).join(" · ")) + (e.count != null ? ` <span class="muted">(${num(e.count)})</span>` : ""))}${cell(e.network ? `<code>${esc(e.network)}</code>` : "–")}</tr>`);
    const evMore = ev.data.next ? `<a class="btn btn-ghost btn-sm" data-act="older" href="${hashFor("security", { ...q, before: ev.data.next })}">Older events →</a>` : `<span class="muted">No older events.</span>`;
    const accRows = acc.data.items.map((a) => `<tr>${cell(shortRef(a.ref))}${cell(esc(a.roles.join(", ")))}${cell(esc(a.created))}${cell(a.two_factor ? `<span class="chip ok">on</span>` : `<span class="chip">off</span>`)}</tr>`);
    el.innerHTML = shell("Admin", "Security", "Statuses only: no key, password, code, token, e-mail address or network address is ever shown. Accounts appear as opaque references.",
      `<div class="grid g2" style="margin-bottom:14px"><div class="card" data-section="warnings"><b>Configuration</b>${warnings}</div><div class="card">${flags}</div></div>
       <div class="card" data-section="events" style="margin-bottom:14px"><div class="row between"><b>Security events</b><select id="f-type">${opts(EVENT_TYPES, q.type, "Every type")}</select></div>
         ${evRows.length ? table(["Time (UTC)", "Event", "Outcome", "Account", "Details", "Network"], evRows) : empty("No security events yet.")}
         <div class="row between" style="margin-top:10px">${q.before ? `<a class="btn btn-ghost btn-sm" href="${hashFor("security", { type: q.type })}">← Newest</a>` : "<span></span>"}${evMore}</div></div>
       <div class="card" data-section="accounts"><b>Accounts</b>${accRows.length ? table(["Account", "Roles", "Created", "Two-factor"], accRows) + pager("security", q, acc.data.total, acc.data.limit, acc.data.offset) : empty("No accounts.")}</div>`);
    el.onchange = (ev2) => { if (ev2.target && ev2.target.id === "f-type") go(hashFor("security", { type: ev2.target.value })); };
  }

  // ---------- health ----------
  async function health(el) {
    const r = await get("/api/admin/health");
    if (!alive(el)) return;
    if (!r.ok) { el.innerHTML = shell("Admin", "Health", "", errorBox(r, "health")); return; }
    const h = r.data, yes = (b) => (b ? `<span class="chip ok">configured</span>` : `<span class="chip">not configured</span>`);
    const counts = Object.keys(h.content).map((k) => `<tr><td>${esc(k.replace("_", " "))}</td><td>${h.content[k].draft}</td><td>${h.content[k].published}</td><td>${h.content[k].archived}</td></tr>`).join("");
    el.innerHTML = shell("Admin", "Health", "Safe facts only: provider keys, URLs and file paths are never shown.",
      `<div class="grid g3" style="margin-bottom:14px">${stat("App version", esc(h.app_version))}${stat("Last migration", esc(h.last_migration.version) + " " + esc(h.last_migration.name), "applied " + h.last_migration.applied_at)}${stat("Database", h.database.integrity === "ok" && h.database.foreign_keys === "ok" ? "✓ healthy" : "✗ check needed", "integrity " + h.database.integrity + ", references " + h.database.foreign_keys)}</div>
       <div class="grid g2"><div class="card"><b>Content</b><table class="ad-kv"><tr><th></th><th>draft</th><th>published</th><th>archived</th></tr>${counts}</table></div>
        <div class="card"><b>Configuration</b><table class="ad-kv"><tr><td>Demo mode</td><td>${h.demo_mode ? `<span class="chip warn">on</span>` : `<span class="chip ok">off</span>`}</td></tr><tr><td>LLM provider</td><td>${yes(h.providers.llm_configured)}</td></tr><tr><td>Speech-to-text</td><td>${yes(h.providers.speech_to_text_configured)}</td></tr>
        <tr><td>Pronunciation</td><td>${yes(h.providers.pronunciation_configured)}</td></tr><tr><td>Tutor uses the LLM</td><td>${yes(h.providers.tutor_uses_llm)}</td></tr></table></div></div>
       <div class="card" style="margin-top:14px"><div class="row between"><b>Integrity check</b><button class="btn btn-primary btn-sm" data-act="integrity">Run check</button></div><div id="ad-integrity" class="muted" style="margin-top:8px">Lifecycle state, curriculum rules, dangling references, orphans and incomplete content.</div></div>`);
    el.onclick = async (ev) => {
      const t = ev.target.closest && ev.target.closest("button"); if (!t || t.dataset.act !== "integrity") return;
      const out = el.querySelector("#ad-integrity"); out.innerHTML = "Checking…";
      const x = await get("/api/admin/health/integrity");
      out.innerHTML = x.ok ? `<b>${x.data.ok ? "✓ Nothing published is broken" : "✗ " + x.data.published_errors + " problem(s) in published content"}</b> · ${x.data.errors} errors, ${x.data.warnings} warnings${findings(x.data.findings.slice(0, 60), false)}` : errorBox(x, "the check");
    };
  }

  // =====================================================================================================================
  // router
  // =====================================================================================================================
  function choose(ctx) {
    const [a, b, c] = ctx.segs;
    if (!a) return (el) => dashboard(el, ctx);
    if (a === "analytics") return (el) => analytics(el, ctx);
    if (a === "audit") return (el) => audit(el, ctx);
    if (a === "health") return (el) => health(el);
    if (a === "security") return (el) => security(el, ctx);
    if (a === "learners") return b ? (el) => learnerDetail(el, ctx, b) : (el) => learners(el, ctx);
    if (a === "curriculum") {
      if (!b) return (el) => curriculumHome(el);
      if (UNITS[b]) return c ? (el) => unitDetail(el, ctx, b, c) : (el) => unitList(el, ctx, b);
      if (b === "vocabulary") return (el) => vocabulary(el, ctx);
      if (b === "topics") return (el) => topics(el);
    }
    return (el) => { el.innerHTML = shell("Admin", "Not found", "", errorBox({ status: 404 })); };
  }

  async function mount() {
    const el = root(); if (!el) return;
    const ctx = parseHash();
    el.innerHTML = loading;
    el.onchange = null;
    el.onclick = (ev) => { const t = ev.target.closest && ev.target.closest("button"); if (t && t.dataset.act === "retry") mount(); };   // so Retry works on a page that failed before it bound its own handlers
    forbidden = false;
    mfaNeeded = false;
    try { await choose(ctx)(el); } catch (e) { if (alive(el)) el.innerHTML = errorBox({ status: 500 }); }
    if (alive(el) && mfaNeeded && window.TwoFactorView) window.TwoFactorView.mount(el.querySelector("#ad-2fa"), { adminGate: true, onEnabled: mount });
    if (alive(el) && forbidden) window.location.hash = "#/";   // a non-admin is sent home (UX only: the server already refused)
  }

  window.AdminView = { NAV, page() { setTimeout(mount, 0); return `<div id="admin-root" class="admin">${loading}</div>`; }, lineChart, barChart, parseHash, hashFor };
})();
