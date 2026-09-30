// Views + router (hash-based SPA, no build step).
(function () {
  const E = Engine;
  const S = () => E.state;
  const $ = (sel) => document.querySelector(sel);
  const app = $("#app");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pack = () => PACKS[S().city] || PACKS.delhi;
  const cat = (k) => CATEGORIES.find((c) => c.key === k);
  const TOPIC_SCENARIO = { transport: "auto", food: "food", shopping: "shopping", directions: "directions", college: "college", smalltalk: "smalltalk", greetings: "greetings" };
  const barClass = (v) => (v >= 80 ? "ok" : v >= 60 ? "mid" : "low");
  const bar = (v, extra = "") => `<div class="bar ${barClass(v)} ${extra}"><i style="width:0" data-w="${v}"></i></div>`;

  // Phrase registry so inline handlers can reference phrases by index.
  let REG = (window.REG = []);
  const reg = (p) => REG.push(p) - 1;

  // ---------- UI helpers ----------
  let toastT;
  function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 2600); }
  function confetti() {
    const colors = ["#5b4bff", "#8b5cf6", "#ff4d6d", "#ff8a3d", "#14b87a"];
    for (let i = 0; i < 60; i++) {
      const c = document.createElement("i"); c.className = "confetti";
      c.style.left = Math.random() * 100 + "vw"; c.style.background = colors[i % 5];
      c.style.animationDelay = Math.random() * 0.4 + "s"; c.style.animationDuration = 1.2 + Math.random() + "s";
      document.body.appendChild(c); setTimeout(() => c.remove(), 2600);
    }
  }
  function animateBars() {
    requestAnimationFrame(() => setTimeout(() => {
      document.querySelectorAll(".bar i[data-w]").forEach((el) => (el.style.width = el.dataset.w + "%"));
      document.querySelectorAll("circle[data-off]").forEach((el) => (el.style.strokeDashoffset = el.dataset.off));
    }, 60));
  }
  function ring(pct, size = 190, stroke = 14) {
    const r = (size - stroke) / 2, c = 2 * Math.PI * r;
    return `<div class="ring" style="width:${size}px;height:${size}px"><svg width="${size}" height="${size}">
      <defs><linearGradient id="rg" x1="0" x2="1"><stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#ff4d6d"/></linearGradient></defs>
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" stroke="rgba(255,255,255,.12)" stroke-width="${stroke}" fill="none"/>
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" stroke="url(#rg)" stroke-width="${stroke}" fill="none" stroke-linecap="round" stroke-dasharray="${c}" style="stroke-dashoffset:${c}" data-off="${c * (1 - pct / 100)}"/>
    </svg><div class="val"><div><b data-count="${pct}" data-suffix="%">${pct}%</b></div></div></div>`;
  }
  function phraseDisplay(p) {
    const lang = S().language;
    if (lang === "hinglish") return { main: esc(p.roman), mainCls: "", second: `<span class="deva">${esc(p.hi)}</span>` };
    if (lang === "en") return { main: esc(p.natural || p.en), mainCls: "", second: `${esc(p.roman)} · <span class="deva">${esc(p.hi)}</span>` };
    return { main: esc(p.hi), mainCls: "deva", second: esc(p.roman) };
  }

  // ---------- Actions exposed to inline handlers ----------
  const A = (window.A = {
    go: (h) => (location.hash = h),
    say(i, slow) {
      const p = REG[i]; if (!p) return;
      const btn = window.event && window.event.currentTarget instanceof Element ? window.event.currentTarget : null;
      const label = btn ? btn.innerHTML : "";
      const ok = E.speak(p, {
        slow,
        onstart: () => { if (btn) btn.innerHTML = "🔊 Playing…"; },
        onend: () => { if (btn && label) btn.innerHTML = label; },
        onerror: () => toast(`🔈 Couldn't play audio here. Say it like this: “${p.roman || p.hi}”`),
      });
      if (!ok) toast(`🔈 Audio isn't available in this browser. Say it like this: “${p.roman || p.hi}”`);
      else if (btn) { btn.innerHTML = "🔊 Playing…"; setTimeout(() => { if (btn.innerHTML === "🔊 Playing…") btn.innerHTML = label; }, 6000); }
    },
    async practice(i, boxId, category) {
      const p = REG[i]; const box = document.getElementById(boxId); const btn = document.getElementById(boxId + "-btn");
      let transcript = null;
      if (E.canListen) {
        if (btn) { btn.classList.add("rec"); btn.innerHTML = "⏺ Listening…"; }
        box.innerHTML = `<div class="feedback"><span class="muted">🎤 Say: <b>${esc(p.roman)}</b></span></div>`;
        toast("🎤 Listening… say the phrase now");
        transcript = await E.listen("hi-IN");
        if (btn) { btn.classList.remove("rec"); btn.innerHTML = "🎤 Practice"; }
        micHint();
      }
      const r = E.score(p, transcript);
      const gain = E.bump(category || "smalltalk", r.pct >= 80 ? 4 : 2);
      const st = S(); st.skills.pronunciation = E.clamp(st.skills.pronunciation * 0.8 + r.pct * 0.2); st.skills.speaking = E.clamp(st.skills.speaking + 1); st.practiced[p.roman] = r.pct; E.save();
      box.innerHTML = feedbackHTML(r, gain, category);
      animateBars(); refreshChrome();
      const card = box.closest(".phrase"); if (card) card.classList.add("practiced");
    },
  });
  A.show = (i) => {
    const p = REG[i]; if (!p) return;
    let o = $("#show-overlay");
    if (!o) { document.body.insertAdjacentHTML("beforeend", `<div id="show-overlay" class="show-overlay" onclick="A.hideShow(event)"></div>`); o = $("#show-overlay"); }
    const main = p.hi && /[\u0900-\u097F]/.test(p.hi) ? p.hi : p.roman;
    o.innerHTML = `<div class="show-inner"><div class="show-tag">🙏 Please read / कृपया पढ़िए</div>
      <div class="show-main deva">${esc(main)}</div>
      ${main !== p.roman ? `<div class="show-roman">${esc(p.roman)}</div>` : ""}
      <div class="show-en">${esc(p.natural || p.en || "")}</div>
      <div class="row" style="justify-content:center;margin-top:28px"><button class="btn btn-ghost btn-lg" onclick="event.stopPropagation();A.say(${i})">🔊 Play aloud</button><button class="btn btn-primary btn-lg" onclick="A.hideShow()">✕ Close</button></div></div>`;
    o.classList.add("open");
    try { document.documentElement.requestFullscreen && window.innerWidth < 860 && document.documentElement.requestFullscreen(); } catch (e) {}
  };
  A.hideShow = (e) => { if (e && e.target.closest(".show-inner .btn-ghost")) return; $("#show-overlay")?.classList.remove("open"); try { document.fullscreenElement && document.exitFullscreen(); } catch (e) {} };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") A.hideShow(); });
  function micHint() {
    const e = E.micError;
    if (e === "not-allowed" || e === "service-not-allowed") toast("🎤 Microphone is blocked. Allow it from the icon in the address bar, then try again. Showing an estimate for now.");
    else if (e === "no-speech") toast("🎤 Didn't hear anything. Try again a little louder. Showing an estimate for now.");
    else if (e === "network") toast("🎤 Speech recognition needs internet (Chrome). Showing an estimate for now.");
    else if (e === "audio-capture") toast("🎤 No microphone found. Showing an estimate for now.");
  }
  function feedbackHTML(r, gain, category) {
    const verdict = r.pct >= 85 ? "Sounds like a local! 🎉" : r.pct >= 70 ? "Nice — clearly understandable 👍" : "Good try — let's polish a couple of words";
    return `<div class="feedback">
      <div class="row between"><div><div class="muted" style="font-size:12px;font-weight:700;letter-spacing:.06em">PRONUNCIATION</div><div class="score">${r.pct}%</div></div>
      <div style="text-align:right"><b>${verdict}</b><div class="muted" style="font-size:13px">${gain > 0 && category ? `❤️ +${gain}% ${esc(cat(category)?.label || "")} confidence` : ""}</div></div></div>
      <div style="margin:10px 0">${bar(r.pct)}</div>
      ${r.good.length ? `<div style="font-size:13px"><b>Good:</b> ${r.good.map((w) => `<span class="word good">${esc(w)}</span>`).join("")}</div>` : ""}
      ${r.bad.length ? `<div style="font-size:13px;margin-top:6px"><b>Practice:</b> ${r.bad.map((w) => `<span class="word bad">${esc(w)}</span>`).join("")}</div>` : ""}
      ${r.heard ? `<div class="muted" style="font-size:12.5px;margin-top:8px">We heard: “${esc(r.heard)}”</div>` : ""}
      ${r.estimated ? `<div class="muted" style="font-size:12.5px;margin-top:8px">Voice input isn't available in this browser, so this is an estimate. Use Chrome for live speech scoring.</div>` : ""}
    </div>`;
  }

  // ---------- Navigation chrome ----------
  const NAV = [
    ["#/", "🏠", "Home"], ["#/new", "🌍", "I'm New Here"], ["#/pack", "🗓️", "First Week"], ["#/tutor", "💬", "AI Tutor"],
    ["#/speaking", "🎤", "Speaking"], ["#/learn", "📚", "Learn"], ["#/confidence", "❤️", "Confidence"], ["#/progress", "🏆", "Progress"],
  ];
  const MOBILE = ["#/", "#/pack", "#/tutor", "#/learn", "#/confidence", "#/progress"];
  let sideLast = null;
  function refreshChrome() {
    const h = "#/" + (location.hash.replace(/^#\/?/, "").split("/")[0] || "");
    const act = { "#/lesson": "#/pack", "#/roleplay": "#/pack" }[h] || h;
    $("#nav").innerHTML = NAV.map(([href, ic, l]) => `<a href="${href}" class="${href === act ? "active" : ""}"><span class="ic">${ic}</span>${l}</a>`).join("");
    $("#bottom-nav").innerHTML = NAV.filter((n) => MOBILE.includes(n[0])).map(([href, ic, l]) => `<a href="${href}" class="${href === act ? "active" : ""}"><span class="ic">${ic}</span>${l.replace("I'm New Here", "New")}</a>`).join("");
    const o = E.overall();
    $("#side-card").innerHTML = `<div class="lbl"><span class="pulse-heart">❤️</span> Local confidence</div><div class="row between"><div class="big" data-count="${o}" data-suffix="%">${o}%</div><span class="chip brand">${S().level}</span></div>
      ${bar(o)}<div class="muted" style="font-size:12.5px;margin-top:8px">📍 ${esc(E.cityName())} · 🔥 ${S().streak}-day streak</div>
      <a class="btn btn-ghost btn-sm" style="width:100%;margin-top:12px" href="#/confidence">View dashboard</a>`;
    if (sideLast !== o) { sideLast = o; Bits.enhance($("#side-card")); }
    animateBars();
  }

  // ---------- Pages ----------
  function landing() {
    const p = pack()[1].phrases[0]; const i = reg(p);
    const top = E.sortedCats().slice(0, 3);
    return `
    <section class="hero">
      <div class="aurora"><i></i><i></i><i></i></div><div class="dots"></div>
      <div class="hero-grid">
        <div>
          <div class="eyebrow" style="color:#b4a7ff">🌍 AI-powered local language buddy</div>
          <h1 data-blur>New city.<br/>New language.<br/><span class="gradient-anim">No problem.</span></h1>
          <p class="sub">Your AI-powered local language buddy for navigating everyday life.</p>
          <div class="hero-line">Learn to handle <span class="rotating" data-rotate="auto rides 🛺|street food 🍛|market bargains 🛍️|metro lines 🚇|chai small talk ☕|campus life 🎓"></span> like a local.</div>
          <div class="row" style="gap:12px;margin-top:26px">
            <a class="btn btn-primary btn-lg" data-magnet href="#/new">🌍 I'm New Here</a>
            <a class="btn btn-ghost btn-lg" data-magnet href="#/tutor">💬 Practice with AI</a>
          </div>
          <div class="hero-stats">
            <div><b data-count="7">7</b><span>days to feel at home</span></div>
            <div><b data-count="${pack().reduce((n, d) => n + d.phrases.length, 0)}">0</b><span>real-life phrases</span></div>
            <div><b data-count="${Object.keys(SCENARIOS).length}">0</b><span>AI locals to talk to</span></div>
          </div>
        </div>
        <div>
          <div class="float-card">
            <div class="row between"><small>🚌 Day 2 · Transport</small><button class="chip" style="background:rgba(255,255,255,.12);color:#fff" onclick="A.say(${i})">🔊 Listen</button></div>
            <div class="deva" style="margin-top:8px">${esc(p.hi)}</div>
            <div style="color:#b4a7ff;font-weight:600">${esc(p.roman)}</div>
            <small>“${esc(p.natural)}”</small>
          </div>
          <div class="float-card">
            <div class="row between"><small><span class="pulse-heart">❤️</span> Your local confidence</small><b data-count="${E.overall()}" data-suffix="%">${E.overall()}%</b></div>
            ${top.map((c) => `<div style="margin-top:10px"><div class="row between" style="font-size:13px"><span>${c.icon} ${c.label}</span><span>${c.v}%</span></div><div class="mini-bar"><i style="width:${c.v}%"></i></div></div>`).join("")}
          </div>
        </div>
      </div>
    </section>
    <div style="margin-top:22px">${rightNow()}</div>
    <div class="quote">
      <div><div class="eyebrow" style="color:var(--ink-3)">Traditional language apps</div><div class="old">Teach you a language.</div></div>
      <div><div class="eyebrow">LingoBuddy</div><div class="new">Teaches you how to <span class="grad-text">live in a new place.</span></div></div>
    </div>
    <div class="loop"><div class="loop-track">${[0, 1].map(() => pack().flatMap((d) => d.phrases.slice(0, 2).map((p) => `<span class="loop-item" onclick="A.say(${reg(p)})"><span>${d.icon}</span><span class="deva">${esc(p.hi)}</span><small>${esc(p.natural)}</small></span>`)).join("")).join("")}</div></div>
    <div class="grid g5" style="margin-top:22px">
      ${[["🗣️", "Speak naturally", "Real phrases locals use, with pronunciation feedback."], ["📍", "Navigate locally", "Autos, metro lines and asking for directions."], ["🍜", "Order with confidence", "Street food, restaurants and “kam teekha”."], ["🤝", "Connect with people", "Small talk with classmates and neighbours."], ["❤️", "Build local confidence", "Track readiness by real-life situation, not XP."]]
        .map(([ic, t, d]) => `<div class="card feature"><div class="icon-tile">${ic}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}
    </div>
    <div style="margin-top:22px">${priceWidget("auto")}</div>
    <div class="card" style="margin-top:22px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
      <div class="row" style="gap:14px"><div class="icon-tile">👋</div><div><h3>Welcome back, ${esc(S().name)}</h3><div class="muted">You're on Day ${Math.min(7, S().completedDays.length + 1)} of your first week in ${esc(E.cityName())}.</div></div></div>
      <div class="row"><a class="btn btn-ghost" href="#/confidence">❤️ My confidence</a><span class="star-border"><a class="btn btn-brand" href="#/pack">Continue my week →</a></span></div>
    </div>`;
  }

  // ---------- 🕒 Right now: time-aware situation suggestion ----------
  function rightNow() {
    const h = new Date().getHours();
    const slots = [
      [5, 11, "🌅", "Morning commute", "Heading out? The metro is packed right now.", "directions", { roman: "Rajiv Chowk ke liye kaun si line?", hi: "राजीव चौक के लिए कौन सी लाइन?", en: "Which line for Rajiv Chowk?" }],
      [11, 15, "🍛", "Lunch time", "Street stalls are busiest now. Order like a local.", "food", { roman: "Ek plate chhole bhature dena.", hi: "एक प्लेट छोले भटूरे देना।", en: "One plate of chhole bhature, please." }],
      [15, 18, "🛍️", "Market hours", "Sarojini and Lajpat Nagar are open. Time to bargain.", "shopping", { roman: "Thoda kam kijiye na.", hi: "थोड़ा कम कीजिए ना।", en: "Can you do a better price?" }],
      [18, 22, "☕", "Chai o'clock", "Evening chai is where friendships start.", "smalltalk", { roman: "Chai piyenge?", hi: "चाय पिएँगे?", en: "Fancy a chai?" }],
      [22, 29, "🌙", "Late night ride home", "Autos charge extra at night. Agree on the fare first.", "auto", { roman: "Bhaiya, meter se chaloge?", hi: "भैया, मीटर से चलोगे?", en: "Will you go by the meter?" }],
    ];
    const hh = h < 5 ? h + 24 : h;
    const [, , ic, t, d, sc, p] = slots.find(([a, b]) => hh >= a && hh < b);
    const i = reg(p); const time = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return `<div class="card now-card"><div class="row" style="gap:16px;flex-wrap:nowrap">
      <div class="icon-tile" style="width:56px;height:56px;font-size:28px">${ic}</div>
      <div style="flex:1;min-width:0"><div class="eyebrow" style="margin:0">🕒 Right now in ${esc(E.cityName())} · ${time}</div>
        <h3>${t}: <span style="font-weight:500;color:var(--ink-2)">${d}</span></h3>
        <div style="margin-top:6px"><b style="font-size:17px">“${esc(p.roman)}”</b> <span class="deva muted">${esc(p.hi)}</span> <span class="muted" style="font-size:13px">· ${esc(p.en)}</span></div></div>
      <div class="row" style="flex:none"><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Listen</button><a class="btn btn-primary btn-sm" href="#/roleplay/${sc}">💬 Practice</a></div>
    </div></div>`;
  }

  let onboard = { city: null, lang: null };
  function onboarding() {
    const city = CITIES.find((c) => c.id === onboard.city);
    const langs = city ? city.langs.map((code) => LANGUAGES.find((l) => l.code === code)) : [];
    const LDESC = { hi: "Learn Devanagari script + pronunciation", hinglish: "How people actually talk on the street", en: "Navigate in English, with local phrases" };
    return `
    <div class="eyebrow">🌍 I'm new here</div>
    <h1>Where are you new?</h1>
    <p class="sub">Pick your city and we'll build a survival pack for your first week — real situations, zero awkward moments.</p>
    <div class="step"><b>1</b> Choose your city</div>
    <div class="grid g5">
      ${CITIES.map((c) => `<button data-tilt class="card hover city ${onboard.city === c.id ? "selected" : ""} ${c.ready ? "" : "locked"}" onclick="A.pickCity('${c.id}')">
        <span class="badge">${c.ready ? '<span class="chip ok">Ready</span>' : '<span class="chip">Soon</span>'}</span>
        <div class="emoji">${c.emoji}</div><h3 style="margin-top:10px">${c.flag} ${c.name}</h3><div class="muted" style="font-size:13px">${c.blurb}</div></button>`).join("")}
    </div>
    ${city ? `<div class="reveal" style="margin-top:34px">
      <div class="step"><b>2</b> What language do you want to learn?</div>
      <div class="grid g3">
        ${langs.map((l) => `<button data-tilt class="card hover lang ${onboard.lang === l.code ? "selected" : ""}" onclick="A.pickLang('${l.code}')">
          <div class="icon-tile">${l.code === "hi" ? "🇮🇳" : l.code === "hinglish" ? "🗣️" : "🌐"}</div>
          <div><div class="native ${l.code === "hi" ? "deva" : ""}">${l.native}</div><div class="muted" style="font-size:13px">${l.name} · ${LDESC[l.code] || ""}</div></div></button>`).join("")}
      </div>
      <div class="muted" style="font-size:13px;margin-top:12px">Also supported by the platform: ${LANGUAGES.filter((l) => !city.langs.includes(l.code)).map((l) => l.name).join(" · ")}</div>
      <div style="margin-top:26px" id="build-area">
        <span class="${onboard.lang ? "star-border" : ""}"><button class="btn btn-brand btn-lg" style="${onboard.lang ? "" : "opacity:.5"}" onclick="A.build()">Build My Survival Pack →</button></span>
      </div>
    </div>` : ""}`;
  }
  A.pickCity = (id) => {
    const c = CITIES.find((x) => x.id === id);
    if (!c.ready) return toast(`${c.flag} ${c.name} pack is coming soon — Delhi is fully ready today!`);
    onboard.city = id; render(); setTimeout(() => $("#build-area")?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
  };
  A.pickLang = (code) => { onboard.lang = code; render(); };
  A.build = () => {
    if (!onboard.city || !onboard.lang) return toast("👆 Pick a language first: Hindi, Hinglish or English.");
    const st = S(); st.city = onboard.city; st.language = onboard.lang; E.save();
    const steps = ["Mapping everyday situations in Delhi", "Picking beginner-friendly phrases", "Adding pronunciation guides", "Setting up AI roleplay partners"];
    $("#build-area").innerHTML = `<div class="card" style="max-width:520px"><h3>✨ Building your survival pack…</h3><div id="build-steps" style="margin-top:10px"></div></div>`;
    steps.forEach((s, i) => setTimeout(() => { $("#build-steps") && ($("#build-steps").innerHTML += `<div class="reveal" style="padding:5px 0">✅ ${s}</div>`); }, 280 * (i + 1)));
    setTimeout(() => { confetti(); A.go("#/pack"); }, 280 * steps.length + 450);
  };

  function dayState(d) {
    const done = S().completedDays.includes(d.day);
    const firstOpen = pack().find((x) => !S().completedDays.includes(x.day));
    return done ? "done" : firstOpen && firstOpen.day === d.day ? "current" : "locked";
  }
  function packPage() {
    const days = pack(); const done = S().completedDays.length;
    return `
    <div class="page-head"><div>
      <div class="eyebrow">🗓️ My first week survival pack</div>
      <h1>Your First Week in ${esc(E.cityName())}</h1>
      <p class="sub">7 days. Real situations. Zero awkward moments.</p></div>
      <div class="card" style="padding:16px 20px;min-width:260px">
        <div class="row between"><b><span data-count="${done}">${done}</span> / 7 days complete</b><span class="chip heart">❤️ ${E.overall()}%</span></div>
        <div style="margin-top:10px">${bar(Math.round((done / 7) * 100))}</div>
      </div></div>
    <div class="grid g4">
      ${days.map((d) => {
        const st = dayState(d); const v = S().confidence[d.key];
        const badge = st === "done" ? '<span class="chip ok">✓ Done</span>' : st === "current" ? '<span class="chip brand">→ Today</span>' : '<span class="chip">🔒 Upcoming</span>';
        return `<div data-tilt class="card hover day ${st} ${d.day === 7 ? "feature-day" : ""}" onclick="A.go('#/lesson/${d.day}')">
          <span class="state">${badge}</span>
          <div class="num">DAY ${d.day}</div>
          <div class="row" style="gap:12px"><div class="icon-tile" ${d.day === 7 ? 'style="background:rgba(255,255,255,.1)"' : ""}>${d.icon}</div><h3>${d.title}</h3></div>
          <p>${d.desc}</p>
          <div><div class="row between" style="font-size:12.5px;margin-bottom:5px"><span class="${d.day === 7 ? "" : "muted"}">Confidence</span><b data-count="${v}" data-suffix="%">${v}%</b></div>${bar(v)}</div>
        </div>`;
      }).join("")}
    </div>
    <div class="insight" style="margin-top:22px"><div class="spark">✨</div><div><b>Buddy tip</b><p>Each day takes about 10 minutes: learn 4–5 phrases, practise them out loud, then try a real conversation with an AI local.</p></div></div>`;
  }

  function lessonPage(dayNum) {
    const d = pack().find((x) => x.day === +dayNum) || pack()[0];
    const sc = SCENARIOS[d.scenario]; const st = dayState(d); const v = S().confidence[d.key];
    return `
    <a class="back" href="#/pack">← First week</a>
    <div class="page-head"><div>
      <div class="eyebrow">Day ${d.day} · ${d.icon} ${d.title}</div>
      <h1>Day ${d.day} — ${d.title}</h1>
      <p class="sub">${d.desc}</p></div>
      <div class="row"><span class="chip heart">❤️ ${v}% confident</span>${st === "done" ? '<span class="chip ok">✓ Completed</span>' : ""}</div></div>
    <div class="situation"><div class="icon-tile">${sc.icon}</div><div><div class="lbl">Situation</div><div class="txt">“${esc(d.situation)}”</div></div>
      <a class="btn btn-primary" style="margin-left:auto" href="#/roleplay/${d.scenario}">💬 Try Conversation</a></div>
    <div class="grid g2">
      ${d.phrases.map((p, n) => {
        const i = reg(p); const disp = phraseDisplay(p); const box = `fb-${d.day}-${n}`;
        return `<div class="card phrase ${S().practiced[p.roman] ? "practiced" : ""}">
          <div class="row between"><span class="chip">Phrase ${n + 1}</span>${S().practiced[p.roman] ? `<span class="chip ok">✓ ${S().practiced[p.roman]}%</span>` : ""}</div>
          <div class="main ${disp.mainCls}" style="margin-top:12px">${disp.main}</div>
          <div class="roman">${disp.second}</div>
          <div class="meta">
            <div><div class="k">Translation</div><div class="v">${esc(p.en)}</div></div>
            <div><div class="k">Natural meaning</div><div class="v">${esc(p.natural)}</div></div>
            <div style="grid-column:1/-1"><div class="k">Pronunciation</div><div class="v"><b>${esc(p.roman)}</b></div></div>
          </div>
          <div class="row">
            <button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Listen</button>
            <button class="btn btn-ghost btn-sm" onclick="A.say(${i}, true)">🐢 Slow</button>
            <button class="btn btn-ghost btn-sm mic-btn" id="${box}-btn" onclick="A.practice(${i}, '${box}', '${d.key}')">🎤 Practice</button>
            <button class="btn btn-ghost btn-sm" onclick="A.show(${i})">📱 Show to local</button>
            <a class="btn btn-ghost btn-sm" href="#/roleplay/${d.scenario}">💬 Try Conversation</a>
          </div>
          <div id="${box}"></div>
        </div>`;
      }).join("")}
    </div>
    <div class="tipbox" style="margin-top:20px"><span>💡</span><div><b>Local tip:</b> ${esc(d.tip)}</div></div>
    ${d.key === "transport" ? `<div style="margin-top:20px">${priceWidget("auto")}</div>` : d.key === "shopping" ? `<div style="margin-top:20px">${priceWidget("jacket")}</div>` : d.key === "food" ? `<div style="margin-top:20px">${priceWidget("chhole")}</div>` : ""}
    <div class="card reco" style="margin-top:20px">
      <div class="row" style="gap:14px"><div class="icon-tile">${sc.icon}</div><div><h3>Ready for the real thing?</h3><div class="muted">Practice with ${esc(sc.partner)} (${esc(sc.role)}) — ${esc(sc.goal)}</div></div></div>
      <div class="row">${st !== "done" ? `<button class="btn btn-ghost" onclick="A.completeDay(${d.day})">✓ Mark day complete</button>` : ""}<a class="btn btn-brand" href="#/roleplay/${d.scenario}">💬 Practice Conversation →</a></div>
    </div>`;
  }
  A.completeDay = (day) => {
    const st = S(); const d = pack().find((x) => x.day === day);
    if (!st.completedDays.includes(day)) { st.completedDays.push(day); st.xp += 50; }
    const g = E.bump(d.key, 6); confetti(); toast(`🎉 Day ${day} complete! ❤️ ${d.title} confidence +${g}%`);
    setTimeout(() => A.go("#/pack"), 700);
  };

  // ---------- Roleplay ----------
  let RP = null;
  function roleplayPage(sid) {
    const sc = SCENARIOS[sid] || SCENARIOS.auto; sid = SCENARIOS[sid] ? sid : "auto";
    if (!RP || RP.sid !== sid) RP = { sid, msgs: [{ role: "ai", text: sc.opening.text, en: sc.opening.en }], used: [], suggestions: sc.start, turns: 0, ended: false, lastVoice: null, gained: 0 };
    const c = cat(sc.category); const day = pack().find((d) => d.key === sc.category);
    return `
    <a class="back" href="${day ? `#/lesson/${day.day}` : "#/pack"}">← ${day ? `Day ${day.day} lesson` : "First week"}</a>
    <div class="chat-wrap">
      <div class="card chat">
        <div class="chat-head"><div class="avatar">${sc.icon}</div><div><b>${esc(sc.partner)}</b><div class="muted" style="font-size:13px"><span class="online"></span>${esc(sc.role)} · ${esc(sc.place)}</div></div>
          <span style="margin-left:auto">${aiChip()}</span></div>
        <div class="msgs" id="msgs">${RP.msgs.map(msgHTML).join("")}</div>
        <div class="suggest" id="suggest">${suggestHTML()}</div>
        <form class="composer" onsubmit="event.preventDefault();A.rpSend()">
          <button type="button" class="mic" id="rp-mic" onclick="A.rpMic()" title="Speak">🎤</button>
          <input id="rp-input" autocomplete="off" placeholder="Type in Hinglish (or English) — e.g. “${esc(sc.start[0])}”" />
          <button class="send" type="submit">➤</button>
        </form>
      </div>
      <div class="stack chat-side">
        <div class="card"><div class="eyebrow">🎬 Scenario</div><h3>${sc.icon} ${esc(sc.title)}</h3><div class="muted" style="font-size:14px">📍 ${esc(sc.place)}</div>
          <div class="tipbox" style="margin-top:12px;font-size:13.5px"><span>🎯</span><div><b>Your goal:</b> ${esc(sc.goal)}</div></div></div>
        <div class="card"><div class="row between"><b>${c.icon} ${c.label}</b><b id="rp-conf">${S().confidence[c.key]}%</b></div><div style="margin-top:8px" id="rp-bar">${bar(S().confidence[c.key])}</div>
          <div class="muted" style="font-size:12.5px;margin-top:8px">Every natural reply builds your local confidence.</div></div>
        <div class="card"><b>🎙️ Pronunciation</b><div class="muted" style="font-size:13px;margin:4px 0 10px">Check how your last reply sounded.</div>
          <button class="btn btn-ghost btn-sm" style="width:100%" onclick="A.rpFeedback()">Get pronunciation feedback</button><div id="rp-fb"></div></div>
        <div class="card"><b>More scenarios</b><div class="row" style="margin-top:10px">${Object.entries(SCENARIOS).filter(([k]) => k !== sid).map(([k, s]) => `<a class="chip" href="#/roleplay/${k}">${s.icon} ${esc(s.title)}</a>`).join("")}</div></div>
      </div>
    </div>`;
  }
  function msgHTML(m, idx) {
    if (m.role === "me") return `<div class="msg me"><div class="bubble">${esc(m.text)}</div></div>`;
    const i = reg({ roman: m.text, hi: m.text });
    const fresh = m.fresh; m.fresh = false;
    return `<div class="msg ai"><div class="bubble" ${fresh ? "data-type" : ""}>${esc(m.text)}</div>${m.en ? `<div class="tr">${esc(m.en)}</div>` : ""}
      <div class="tools"><button onclick="A.say(${i})">🔊 Listen</button><button onclick="A.say(${i}, true)">🐢 Slow</button></div>
      ${m.tip ? `<div class="coach">${esc(m.tip)}</div>` : ""}
      ${m.end ? `<div class="card" style="margin-top:10px;padding:16px"><b>🎉 Conversation complete!</b><div class="muted" style="font-size:13.5px">You handled it like a local. ❤️ +${RP.gained}% confidence this conversation.</div>
        <div class="row" style="margin-top:10px"><a class="btn btn-brand btn-sm" href="#/confidence">See my confidence →</a><button class="btn btn-ghost btn-sm" onclick="A.rpRestart()">↺ Try again</button></div></div>` : ""}</div>`;
  }
  const aiChip = () => (E.aiProvider ? `<span class="chip live"><i></i> Live AI</span>` : `<span class="chip brand">✨ AI roleplay</span>`);
  function suggestHTML() { return RP.ended ? "" : (RP.suggestions || []).map((s, i) => `<button onclick="A.rpSuggest(${i})">${esc(s)}</button>`).join(""); }
  function rpRedraw() {
    const box = $("#msgs"); if (!box) return;
    box.innerHTML = RP.msgs.map(msgHTML).join("") + (RP.typing ? `<div class="msg ai"><div class="typing"><i></i><i></i><i></i></div></div>` : "");
    $("#suggest").innerHTML = RP.typing ? "" : suggestHTML();
    Bits.enhance(box); box.scrollTop = box.scrollHeight;
    const c = SCENARIOS[RP.sid].category; $("#rp-conf").textContent = S().confidence[c] + "%"; $("#rp-bar").innerHTML = bar(S().confidence[c]); animateBars(); refreshChrome();
  }
  A.rpSuggest = (i) => A.rpSend(RP.suggestions[i]);
  A.rpRestart = () => { RP = null; render(); };
  A.rpSend = async (forced) => {
    const input = $("#rp-input"); const text = (forced || input.value).trim();
    if (!text || RP.typing) return; input.value = "";
    if (RP.ended) { RP = null; render(); return; }
    const sc = SCENARIOS[RP.sid];
    RP.msgs.push({ role: "me", text }); RP.typing = true; RP.turns++; rpRedraw();
    const [ai] = await Promise.all([E.askAI({ mode: "roleplay", scenario: sc, history: RP.msgs }), new Promise((r) => setTimeout(r, 750))]);
    let reply;
    const local = E.roleplayReply(RP.sid, text, RP.used);
    if (ai) reply = { text: ai.reply, en: ai.translation, tip: ai.tip || local.tip, s: ai.suggestions?.length ? ai.suggestions : local.s, end: local.end && local.matched };
    else reply = local;
    const g = E.bump(sc.category, E.looksEnglish(text) ? 1 : 3); RP.gained += g;
    if (reply.end) {
      RP.ended = true; RP.gained += E.bump(sc.category, 6); S().roleplays++;
      const d = pack().find((x) => x.key === sc.category); if (d && !S().completedDays.includes(d.day)) S().completedDays.push(d.day);
      if (!S().achievements.includes("first-chat")) S().achievements.push("first-chat");
      E.save(); setTimeout(confetti, 200);
    }
    RP.typing = false; RP.msgs.push({ role: "ai", text: reply.text, en: reply.en, tip: reply.tip, end: reply.end, fresh: true }); RP.suggestions = reply.s; rpRedraw();
    if (g > 0) toast(`❤️ ${cat(sc.category).label} confidence +${g}%`);
  };
  A.rpMic = async () => {
    const mic = $("#rp-mic");
    if (!E.canListen) { toast("🎤 Voice input needs Chrome/Edge — type your reply instead."); $("#rp-input").focus(); return; }
    mic.classList.add("rec"); $("#rp-input").placeholder = "Listening… speak now";
    const t = await E.listen("hi-IN"); mic.classList.remove("rec"); $("#rp-input").placeholder = "Type in Hinglish (or English)";
    if (!t) { if (E.micError && E.micError !== "no-speech" && E.micError !== "aborted") micHint(); else toast("Didn't catch that. Try again or type it."); return; }
    const first = t.split(" | ")[0]; RP.lastVoice = t; A.rpSend(first);
  };
  A.rpFeedback = () => {
    const last = [...RP.msgs].reverse().find((m) => m.role === "me");
    if (!last) return toast("Say or type a reply first, then check your pronunciation.");
    const sc = SCENARIOS[RP.sid];
    const cands = [...sc.start, ...sc.rules.flatMap((r) => r.s)];
    const target = cands.map((c) => ({ c, s: sharedWords(c, last.text) })).sort((a, b) => b.s - a.s)[0];
    const phrase = { roman: target && target.s > 0 ? target.c : last.text, hi: last.text };
    const r = E.score(phrase, RP.lastVoice); RP.lastVoice = null;
    $("#rp-fb").innerHTML = feedbackHTML(r, 0); animateBars();
  };
  const sharedWords = (a, b) => { const w = new Set(a.toLowerCase().match(/\w+/g)); return (b.toLowerCase().match(/\w+/g) || []).filter((x) => w.has(x)).length; };

  // ---------- Confidence ----------
  function confidencePage() {
    const o = E.overall(); const ins = E.insight(); const low = ins.low;
    return `
    <div class="page-head"><div><div class="eyebrow">❤️ Local confidence</div><h1>Your Local Confidence</h1>
      <p class="sub">Not XP. Not streaks. How ready you actually feel for real life in ${esc(E.cityName())}.</p></div></div>
    <div class="conf-hero">
      <div class="card ring-card"><div class="aurora"><i></i><i></i><i></i></div>${ring(o)}<div class="ready" data-decrypt>${E.readiness(o)}</div><div style="color:#9fa2c4;font-size:13px;margin-top:6px">Weighted by how often you'll need it in week one</div></div>
      <div class="card">
        ${E.sortedCats().sort((a, b) => CATEGORIES.indexOf(cat(a.key)) - CATEGORIES.indexOf(cat(b.key))).map((c) => `
          <div class="conf-row"><span>${c.icon}</span><b>${c.label}</b>${bar(c.v)}<span class="pct" data-count="${c.v}" data-suffix="%">${c.v}%</span></div>`).join("")}
      </div>
    </div>
    <div class="insight" style="margin-top:20px"><div class="spark">✨</div><div><b>AI insight</b><p>${esc(ins.text)}</p></div></div>
    <div class="card reco" style="margin-top:16px">
      <div class="row" style="gap:14px"><div class="icon-tile">${low.icon}</div><div><div class="eyebrow" style="margin:0">Recommended next</div><h3>💬 Practice ${esc(low.label)}</h3>
        <div class="muted">${esc(SCENARIOS[TOPIC_SCENARIO[low.key]].title)} with ${esc(SCENARIOS[TOPIC_SCENARIO[low.key]].partner)} · ~3 min</div></div></div>
      <span class="star-border"><a class="btn btn-brand btn-lg" href="#/roleplay/${TOPIC_SCENARIO[low.key]}">Practice Now →</a></span>
    </div>`;
  }

  // ---------- Tutor ----------
  let tutorBusy = false;
  function tutorPage() {
    const hist = S().tutor;
    const starters = ["I need to ask an auto driver to go to the airport.", "How do I order food less spicy?", "How can I bargain at Sarojini?", "What does 'jugaad' mean?", "How do I make friends in class?"];
    return `
    <div class="page-head"><div><div class="eyebrow">💬 AI tutor</div><h1>Your LingoBuddy Tutor</h1><p class="sub">Describe any situation — I'll give you the exact words locals use.</p></div>
      ${hist.length ? `<button class="btn btn-ghost btn-sm" onclick="A.tutorClear()">↺ New chat</button>` : ""}</div>
    <div class="card chat" style="height:calc(100vh - 230px)">
      <div class="chat-head"><div class="avatar">🌍</div><div><b>LingoBuddy</b><div class="muted" style="font-size:13px"><span class="online"></span>Knows ${esc(E.cityName())} · remembers this conversation</div></div><span style="margin-left:auto">${aiChip()}</span></div>
      <div class="msgs" id="tmsgs">${tutorMsgs()}</div>
      <div class="suggest" id="tsuggest">${hist.length ? "" : starters.map((s) => `<button onclick="A.tutorSend(this.textContent)">${esc(s)}</button>`).join("")}</div>
      <form class="composer" onsubmit="event.preventDefault();A.tutorSend()">
        <button type="button" class="mic" id="t-mic" onclick="A.tutorMic()" title="Speak">🎤</button>
        <input id="t-input" autocomplete="off" placeholder="e.g. How do I ask for the bill politely?" />
        <button class="send" type="submit">➤</button>
      </form>
    </div>`;
  }
  function tutorMsgs() {
    const hist = S().tutor;
    const hello = `<div class="msg ai"><div class="bubble">Namaste ${esc(S().name)}! 👋 I'm your local buddy for ${esc(E.cityName())}. Tell me where you're going or what you need to say, and I'll teach you the words.</div></div>`;
    return hello + hist.map((m, mi) => {
      if (m.role === "me") return `<div class="msg me"><div class="bubble">${esc(m.text)}</div></div>`;
      const sc = TOPIC_SCENARIO[m.topic] || "smalltalk";
      const fresh = m.fresh; delete m.fresh;
      return `<div class="msg ai" style="max-width:86%"><div class="bubble"><span ${fresh ? "data-type" : ""}>${esc(m.intro || m.text)}</span>
        ${(m.phrases || []).map((p, n) => { const i = reg(p); const box = `tfb-${mi}-${n}`; return `<div class="phrase-mini">${p.label ? `<div class="lab">${esc(p.label)}</div>` : ""}
          <div class="r">“${esc(p.roman)}”</div>${p.hi ? `<div class="h">${esc(p.hi)}</div>` : ""}<div class="e">${esc(p.en)}</div>
          <div class="row" style="margin-top:8px;gap:6px"><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Hear it</button><button class="btn btn-ghost btn-sm" id="${box}-btn" onclick="A.practice(${i}, '${box}', '${m.topic || "smalltalk"}')">🎤 Say it</button><button class="btn btn-ghost btn-sm" onclick="A.show(${i})">📱 Show</button><a class="btn btn-ghost btn-sm" href="#/roleplay/${sc}">💬 Practice</a></div><div id="${box}"></div></div>`; }).join("")}
        ${m.note ? `<div style="margin-top:10px;font-size:14px">💡 ${esc(m.note)}</div>` : ""}</div>
        ${m.en ? `<div class="tr">${esc(m.en)}</div>` : ""}
        ${m.suggestions && m.suggestions.length ? `<div class="tools">${m.suggestions.map((s) => `<button onclick="A.tutorSend(this.textContent)">${esc(s)}</button>`).join("")}</div>` : ""}
        ${!m.phrases || !m.phrases.length ? `<div class="tools"><button onclick="A.say(${reg({ roman: m.text || m.intro })})">🔊 Hear it</button><a href="#/roleplay/${sc}"><button>💬 Practice</button></a></div>` : ""}</div>`;
    }).join("") + (tutorBusy ? `<div class="msg ai"><div class="typing"><i></i><i></i><i></i></div></div>` : "");
  }
  function tutorRedraw() { const b = $("#tmsgs"); if (!b) return; b.innerHTML = tutorMsgs(); Bits.enhance(b); b.scrollTop = b.scrollHeight; $("#tsuggest").innerHTML = ""; }
  A.tutorClear = () => { S().tutor = []; E.save(); render(); };
  A.tutorSend = async (forced) => {
    const input = $("#t-input"); const text = (forced || input.value).trim(); if (!text || tutorBusy) return; input.value = "";
    const st = S(); st.tutor.push({ role: "me", text }); tutorBusy = true; tutorRedraw();
    // Curated phrases win for known situations; the live LLM handles open-ended questions.
    const local = E.tutorReply(text, st.tutor.slice(0, -1));
    const [ai] = await Promise.all([local.generic ? E.askAI({ mode: "tutor", history: st.tutor.map((m) => ({ role: m.role, text: m.text || [m.intro, ...(m.phrases || []).map((p) => p.roman)].join(" ") })) }) : null, new Promise((r) => setTimeout(r, 700))]);
    const hasP = ai && ai.phrases && ai.phrases.length;
    const msg = ai ? { role: "ai", intro: ai.reply, text: hasP ? undefined : ai.reply, phrases: hasP ? ai.phrases : undefined, en: hasP ? "" : ai.translation, note: ai.note || ai.tip, suggestions: ai.suggestions, topic: local.topic } : { role: "ai", ...local };
    st.tutor.push(msg); st.tutor = st.tutor.slice(-30); st.xp += 5;
    tutorBusy = false; msg.fresh = true; tutorRedraw(); E.save();
  };
  A.tutorMic = async () => {
    if (!E.canListen) { toast("🎤 Voice input needs Chrome/Edge — type your question instead."); return; }
    const mic = $("#t-mic"); mic.classList.add("rec"); const t = await E.listen("en-IN"); mic.classList.remove("rec");
    if (t) A.tutorSend(t.split(" | ")[0]); else if (E.micError && E.micError !== "no-speech" && E.micError !== "aborted") micHint(); else toast("Didn't catch that. Try again or type it.");
  };

  // ---------- Speaking ----------
  let spk = { day: 2, idx: 0 };
  function speakingPage() {
    const d = pack().find((x) => x.day === spk.day); const p = d.phrases[spk.idx % d.phrases.length]; const i = reg(p); const disp = phraseDisplay(p);
    return `
    <div class="page-head"><div><div class="eyebrow">🎤 Speaking studio</div><h1>Say it like a local</h1><p class="sub">Listen, repeat, and get instant pronunciation feedback.</p></div>
      <div class="card" style="padding:14px 18px"><div class="muted" style="font-size:12.5px;font-weight:600">Pronunciation skill</div><div class="row between" style="gap:20px"><b style="font-size:22px">${S().skills.pronunciation}%</b><span class="chip ${E.canListen ? "ok" : "warn"}">${E.canListen ? "🎙️ Live scoring" : "⌨️ Estimate mode"}</span></div></div></div>
    <div class="tabs">${pack().map((x) => `<button class="${x.day === spk.day ? "active" : ""}" onclick="A.spkDay(${x.day})">${x.icon} ${x.title}</button>`).join("")}</div>
    <div class="card phrase" style="max-width:760px;padding:34px;text-align:center;margin:0 auto">
      <span class="chip">${d.icon} ${d.title} · ${spk.idx % d.phrases.length + 1} / ${d.phrases.length}</span>
      <div class="main ${disp.mainCls}" style="font-size:40px;margin-top:18px">${disp.main}</div>
      <div class="roman" style="font-size:19px">${disp.second}</div>
      <div class="muted" style="margin-top:8px;font-size:16px">“${esc(p.natural)}”</div>
      <div class="row" style="justify-content:center;margin-top:24px;gap:12px">
        <button class="btn btn-ghost btn-lg" onclick="A.say(${i})">🔊 Listen</button>
        <button class="btn btn-ghost btn-lg" onclick="A.say(${i}, true)">🐢 Slow</button>
        <button class="btn btn-brand btn-lg" id="spk-btn" onclick="A.practice(${i}, 'spk', '${d.key}')">🎤 Practice</button>
      </div>
      <div id="spk" style="text-align:left"></div>
      <div class="row" style="justify-content:center;margin-top:20px"><button class="btn btn-primary" onclick="A.spkNext()">Next phrase →</button></div>
    </div>`;
  }
  A.spkDay = (d) => { spk = { day: d, idx: 0 }; render(); };
  A.spkNext = () => { spk.idx++; render(); };

  // ---------- Learn (flashcards, reading, listening, placement) ----------
  let learnTab = "flash", flashFlipped = false, flashSession = null, readIdx = 0, readShow = false, listenQ = null, placeAns = {};
  function learnPage() {
    const tabs = [["flash", "🃏 Flashcards"], ["reading", "📖 Reading"], ["listening", "🎧 Listening"], ["placement", "🎯 Level test"]];
    const body = { flash: flashView, reading: readingView, listening: listeningView, placement: placementView }[learnTab]();
    return `<div class="page-head"><div><div class="eyebrow">📚 Learn</div><h1>Build your foundations</h1><p class="sub">Vocabulary, reading and listening — all built from real ${esc(E.cityName())} situations. Level: <b>${S().level}</b></p></div></div>
      <div class="tabs">${tabs.map(([k, l]) => `<button class="${learnTab === k ? "active" : ""}" onclick="A.learnTab('${k}')">${l}</button>`).join("")}</div>${body}`;
  }
  A.learnTab = (t) => { learnTab = t; flashFlipped = false; render(); };
  function flashView() {
    if (!flashSession) flashSession = E.dueCards().slice(0, 12);
    const c = flashSession[0];
    const learned = Object.values(S().srs).filter((x) => x.reps > 0).length;
    if (!c) return `<div class="card" style="text-align:center;padding:40px"><div style="font-size:44px">🎉</div><h2>All caught up!</h2><p class="muted">${learned} cards in long-term memory. Come back tomorrow for spaced review.</p><button class="btn btn-primary" onclick="A.flashAll()">Review everything anyway</button></div>`;
    const i = reg(c);
    return `<div class="row between" style="max-width:520px;margin:0 auto 14px"><span class="chip brand">${flashSession.length} due</span><span class="chip ok">🧠 ${learned} learned</span></div>
      <div class="flash ${flashFlipped ? "flipped" : ""}" onclick="A.flip()"><div class="flash-inner">
        <div class="flash-face flash-front"><span class="chip">${esc(c.category)}</span><div class="deva" style="margin-top:18px">${esc(c.hi)}</div><div class="muted" style="margin-top:14px">Tap to reveal</div></div>
        <div class="flash-face flash-back"><div style="font-size:28px;font-weight:700">${esc(c.natural)}</div><div style="color:#b4a7ff;margin-top:10px;font-weight:600">🗣 ${esc(c.roman)}</div><div style="color:#9fa2c4;margin-top:6px;font-size:14px">Literal: ${esc(c.en)}</div><div style="margin-top:14px"><span class="chip" style="background:rgba(255,255,255,.1);color:#fff">${esc(c.category)}</span></div></div>
      </div></div>
      <div class="row" style="justify-content:center;margin-top:22px">
        <button class="btn btn-ghost" onclick="A.say(${i})">🔊</button>
        <button class="btn btn-ghost" onclick="A.card(false)">× Practice again</button>
        <button class="btn btn-primary" onclick="A.card(true)">✓ Know it</button></div>`;
  }
  A.flip = () => { flashFlipped = !flashFlipped; document.querySelector(".flash")?.classList.toggle("flipped", flashFlipped); };
  A.card = (knew) => { const c = flashSession.shift(); E.review(c.id, knew); if (!knew) flashSession.push(c); flashFlipped = false; render(); };
  A.flashAll = () => { flashSession = E.allCards().sort(() => Math.random() - 0.5).slice(0, 12); render(); };

  function readingView() {
    const r = READINGS[readIdx];
    return `<div class="grid g2" style="align-items:start">
      <div class="card"><div class="row between"><h2>${esc(r.title)}</h2><span class="chip brand">${r.level}</span></div>
        ${r.lines.map((l) => { const i = reg(l); return `<div class="reading-line"><div class="row between"><div class="deva">${esc(l.hi)}</div><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊</button></div><div class="muted" style="font-size:14px">${esc(l.roman)}</div>${readShow ? `<div style="font-size:14.5px;color:var(--brand)">${esc(l.en)}</div>` : ""}</div>`; }).join("")}
        <div class="row" style="margin-top:14px"><button class="btn btn-ghost btn-sm" onclick="A.readToggle()">${readShow ? "Hide" : "Show"} English translation</button>
        <button class="btn btn-ghost btn-sm" onclick="A.readNext()">Next passage →</button></div></div>
      <div class="card"><h3>Comprehension check</h3><div class="muted" style="font-size:14px">Answer in any order.</div>
        ${r.questions.map((q, qi) => `<div style="margin-top:16px"><b>${qi + 1}. ${esc(q.q)}</b>${q.options.map((o, oi) => `<button class="opt" id="rq-${qi}-${oi}" onclick="A.readAns(${qi}, ${oi})">${esc(o)}</button>`).join("")}</div>`).join("")}</div></div>`;
  }
  A.readToggle = () => { readShow = !readShow; render(); };
  A.readNext = () => { readIdx = (readIdx + 1) % READINGS.length; readShow = false; render(); };
  A.readAns = (qi, oi) => {
    const q = READINGS[readIdx].questions[qi]; const ok = q.a === oi;
    document.getElementById(`rq-${qi}-${oi}`).classList.add(ok ? "right" : "wrong");
    if (!ok) document.getElementById(`rq-${qi}-${q.a}`).classList.add("right");
    if (ok) { S().xp += 10; S().skills.vocabulary = E.clamp(S().skills.vocabulary + 1); E.save(); toast("✅ Correct! +10 XP"); }
  };

  function listeningView() {
    const cards = E.allCards();
    if (!listenQ) {
      const ans = cards[Math.floor(Math.random() * cards.length)];
      const opts = [ans, ...cards.filter((c) => c.id !== ans.id).sort(() => Math.random() - 0.5).slice(0, 3)].sort(() => Math.random() - 0.5);
      listenQ = { ans, opts, done: false };
    }
    const i = reg(listenQ.ans);
    return `<div class="card" style="max-width:640px;margin:0 auto;text-align:center;padding:34px">
      <div class="eyebrow">🎧 Listen and choose</div><h2>What did you hear?</h2>
      <div class="row" style="justify-content:center;margin:20px 0"><button class="btn btn-brand btn-lg" onclick="A.say(${i})">▶ Play</button><button class="btn btn-ghost btn-lg" onclick="A.say(${i}, true)">🐢 Slow</button></div>
      ${!E.canSpeak ? `<div class="tipbox" style="text-align:left;margin-bottom:12px">🔈 Audio isn't supported here. Hint: <b>${esc(listenQ.ans.roman)}</b></div>` : ""}
      <div style="text-align:left">${listenQ.opts.map((o, oi) => `<button class="opt ${listenQ.done ? (o.id === listenQ.ans.id ? "right" : listenQ.pick === oi ? "wrong" : "") : ""}" onclick="A.listenAns(${oi})">${esc(o.natural)}</button>`).join("")}</div>
      ${listenQ.done ? `<div style="margin-top:16px"><div class="deva" style="font-size:22px">${esc(listenQ.ans.hi)}</div><div class="muted">${esc(listenQ.ans.roman)}</div><button class="btn btn-primary" style="margin-top:14px" onclick="A.listenNext()">Next →</button></div>` : ""}</div>`;
  }
  A.listenAns = (oi) => {
    if (listenQ.done) return; listenQ.done = true; listenQ.pick = oi;
    const ok = listenQ.opts[oi].id === listenQ.ans.id;
    if (ok) { S().skills.listening = E.clamp(S().skills.listening + 1); S().xp += 10; E.save(); toast("🎧 Nice ear! +10 XP"); }
    render();
  };
  A.listenNext = () => { listenQ = null; render(); setTimeout(() => document.querySelector(".btn-brand")?.click(), 200); };

  function placementView() {
    const pl = S().placement;
    const answered = Object.keys(placeAns).length;
    if (pl && answered === 0) return `<div class="card" style="max-width:640px;margin:0 auto;text-align:center;padding:36px"><div style="font-size:44px">🎯</div><h2>Your level: ${esc(S().level)} ${S().level === "A1" ? "Beginner" : "Elementary"}</h2><p class="muted">Placement score ${pl.score}/${PLACEMENT.length}. Your survival pack is tuned to this level.</p>
      <div class="row" style="justify-content:center;gap:6px;margin:14px 0">${["A1", "A2", "B1", "B2", "C1", "C2"].map((l) => `<span class="chip ${l === S().level ? "brand" : ""}">${l}</span>`).join("")}</div>
      <button class="btn btn-ghost" onclick="A.placeRetake()">Retake test</button></div>`;
    return `<div class="card" style="max-width:720px;margin:0 auto"><div class="row between"><h2>Quick level check</h2><span class="chip">${answered} / ${PLACEMENT.length}</span></div><p class="muted">5 questions · CEFR placement (A1 → C2)</p>
      ${PLACEMENT.map((q, qi) => `<div style="margin-top:18px"><b>${qi + 1}. ${esc(q.q)}</b>${q.options.map((o, oi) => `<button class="opt ${placeAns[qi] !== undefined ? (oi === q.a ? "right" : placeAns[qi] === oi ? "wrong" : "") : ""}" onclick="A.placeAns(${qi}, ${oi})">${esc(o)}</button>`).join("")}</div>`).join("")}
      <button class="btn btn-brand" style="margin-top:22px" ${answered === PLACEMENT.length ? "" : "disabled"} onclick="A.placeFinish()">See my level →</button></div>`;
  }
  A.placeAns = (qi, oi) => { if (placeAns[qi] === undefined) { placeAns[qi] = oi; render(); } };
  A.placeFinish = () => {
    const score = PLACEMENT.filter((q, i) => placeAns[i] === q.a).length;
    S().placement = { score, at: Date.now() }; S().level = score >= 5 ? "A2" : "A1"; E.save(); placeAns = {}; confetti(); render(); refreshChrome();
  };
  A.placeRetake = () => { placeAns = {}; S().placement = null; render(); };

  // ---------- Progress ----------
  function progressPage() {
    const st = S(); const done = st.completedDays.length; const cur = pack().find((d) => !st.completedDays.includes(d.day));
    const ACH = [["first-words", "👋", "First words", "Said your first Hindi phrase"], ["auto-pro", "🛺", "Auto pro", "Negotiated an auto fare"], ["foodie", "🍛", "Dilli foodie", "Ordered street food"], ["first-chat", "💬", "Conversationalist", "Finished an AI roleplay"], ["bargainer", "🛍️", "Sarojini bargainer", "Won a bargain"], ["local", "❤️", "Basically local", "Reached 90% confidence"]];
    if (E.overall() >= 90 && !st.achievements.includes("local")) st.achievements.push("local");
    return `
    <div class="page-head"><div><div class="eyebrow">🏆 Progress</div><h1>Your journey so far</h1><p class="sub">Every day in ${esc(E.cityName())} gets a little easier.</p></div></div>
    <div class="grid g4">
      <div class="card stat"><div class="k">Current level</div><div class="v">${st.level} <span style="font-size:16px;color:var(--ink-3)">${st.level === "A1" ? "Beginner" : "Elementary"}</span></div></div>
      <div class="card stat"><div class="k">Weekly goal</div><div class="v"><span data-count="${done}">${done}</span> / 7</div><div class="muted" style="font-size:13px">situations completed</div></div>
      <div class="card stat"><div class="k">Streak</div><div class="v">🔥 <span data-count="${st.streak}">${st.streak}</span> days</div></div>
      <div class="card stat" style="cursor:pointer" onclick="A.go('#/confidence')"><div class="k">❤️ Local confidence</div><div class="v grad-text" data-count="${E.overall()}" data-suffix="%">${E.overall()}%</div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Your journey</h3><div class="journey" style="margin-top:12px">
      ${pack().map((d) => { const isDone = st.completedDays.includes(d.day); const isCur = cur && cur.day === d.day; return `<a class="j ${isDone ? "done" : isCur ? "cur" : ""}" href="#/lesson/${d.day}"><span>${isDone ? "✓" : isCur ? "→" : "🔒"}</span>Day ${d.day}</a>`; }).join("")}</div></div>
    <div class="grid g2" style="margin-top:16px;align-items:start">
      <div class="card"><h3>Skills</h3>${[["🗣️", "Speaking", "speaking"], ["🎧", "Listening", "listening"], ["📚", "Vocabulary", "vocabulary"], ["🎙️", "Pronunciation", "pronunciation"]].map(([ic, l, k]) => `<div class="conf-row" style="grid-template-columns:26px 120px 1fr 48px"><span>${ic}</span><b>${l}</b>${bar(st.skills[k])}<span class="pct">${st.skills[k]}%</span></div>`).join("")}</div>
      <div class="card"><div class="row between"><h3>Achievements</h3><span class="chip warn">⚡ <span data-count="${st.xp}">${st.xp}</span> XP</span></div>
        <div class="grid g2" style="margin-top:12px;gap:10px">${ACH.map(([id, ic, t, d]) => `<div class="ach ${st.achievements.includes(id) ? "" : "off"}"><div class="icon-tile">${ic}</div><div><b style="font-size:14px">${t}</b><div class="muted" style="font-size:12.5px">${d}</div></div></div>`).join("")}</div></div>
    </div>
    <div class="row" style="margin-top:22px"><button class="btn btn-ghost btn-sm" onclick="A.resetDemo()">↺ Reset demo data</button></div>`;
  }
  A.resetDemo = () => { E.reset(); RP = null; flashSession = null; toast("Demo data reset — Alex is back to Day 4."); render(); };

  // ---------- Router ----------
  function render() {
    REG = window.REG = [];
    const [route, arg] = location.hash.replace(/^#\/?/, "").split("/");
    const views = { "": landing, new: onboarding, pack: packPage, lesson: () => lessonPage(arg), roleplay: () => roleplayPage(arg), confidence: confidencePage, tutor: tutorPage, speaking: speakingPage, learn: learnPage, progress: progressPage };
    let html;
    try { html = (views[route] || landing)(); } catch (e) { console.error(e); html = landing(); }
    app.innerHTML = html;
    app.querySelectorAll("h1:not([data-blur])").forEach((h) => h.setAttribute("data-blur", ""));
    Bits.enhance(app);
    app.style.animation = "none"; void app.offsetWidth; app.style.animation = "";
    refreshChrome();
    const m = $("#msgs") || $("#tmsgs"); if (m) m.scrollTop = m.scrollHeight;
  }
  let lastRoute = null;
  // Clicking a link to the page you're already on should still do something: re-open it fresh.
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href^='#/']");
    if (!a || a.getAttribute("href") !== location.hash || (location.hash === "" && a.getAttribute("href") !== "#/")) return;
    if (location.hash.startsWith("#/roleplay") && RP && RP.ended) RP = null;
    if (location.hash === "#/new") onboard = { city: null, lang: null };
    render(); window.scrollTo(0, 0);
  });
  window.addEventListener("hashchange", () => {
    const r = location.hash.split("/")[1] || "";
    if (r === "roleplay" && lastRoute !== "roleplay" && RP && RP.ended) RP = null; // finished chats restart when re-entered
    if (r === "new" && lastRoute !== "new") onboard = { city: null, lang: null };
    if (r !== "learn") flashSession = null;
    lastRoute = r; render(); window.scrollTo(0, 0);
  });
  // ---------- 💰 Fair Price Check (approximate typical Delhi prices) ----------
  const PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km)", min: 80, max: 120, cat: "transport" },
    { id: "rick", label: "🚲 Cycle-rickshaw (1–2 km)", min: 20, max: 50, cat: "transport" },
    { id: "jacket", label: "🧥 Street-market jacket", min: 300, max: 600, cat: "shopping" },
    { id: "kurta", label: "👕 Cotton kurta (market)", min: 250, max: 500, cat: "shopping" },
    { id: "chhole", label: "🍛 Plate of chhole bhature", min: 60, max: 120, cat: "food" },
    { id: "chai", label: "☕ Cutting chai", min: 10, max: 20, cat: "food" },
  ];
  function priceWidget(pick) {
    return `<div class="card price-card"><div class="row between"><div><div class="eyebrow" style="margin:0">💰 Fair price check</div><h3>Getting a fair deal?</h3></div><span class="chip">Delhi · approx.</span></div>
      <div class="row" style="margin-top:12px">
        <select id="pc-item" class="pc-in">${PRICES.map((p) => `<option value="${p.id}" ${p.id === pick ? "selected" : ""}>${p.label}</option>`).join("")}</select>
        <input id="pc-quote" class="pc-in" type="number" min="1" placeholder="They said ₹…" style="width:130px" onkeydown="if(event.key==='Enter')A.priceCheck()" />
        <button class="btn btn-primary btn-sm" onclick="A.priceCheck()">Check</button>
      </div><div id="pc-out"></div></div>`;
  }
  A.priceCheck = () => {
    const item = PRICES.find((p) => p.id === $("#pc-item").value); const q = parseInt($("#pc-quote").value, 10);
    if (!q || q < 1) return toast("💰 Type the price they quoted, e.g. 150");
    const mid = Math.round((item.min + item.max) / 2 / 10) * 10 || item.min;
    let v, cls, phrase;
    if (q <= item.max) { v = "✅ Fair price. Go for it!"; cls = "ok"; phrase = { roman: "Theek hai, chaliye.", hi: "ठीक है, चलिए।", en: "Okay, let's go / deal." }; }
    else if (q <= item.max * 1.35) { v = "🤏 A little high. Counter politely:"; cls = "warn"; phrase = { roman: `Bhaiya, ${item.max} mein doge?`, hi: `भैया, ${item.max} में दोगे?`, en: `Will you do it for ₹${item.max}?` }; }
    else { v = "🚩 Too high. Bargain or walk away:"; cls = "heart"; phrase = { roman: `Bahut mehenga hai, bhaiya. ${mid} mein doge?`, hi: `बहुत महंगा है, भैया। ${mid} में दोगे?`, en: `That's too expensive. Will you do ₹${mid}?` }; }
    const i = reg(phrase);
    $("#pc-out").innerHTML = `<div class="feedback"><div class="row between"><b>${v}</b><span class="chip ${cls}">Typical ₹${item.min}–${item.max}</span></div>
      <div style="margin-top:8px;font-size:18px;font-weight:700">“${esc(phrase.roman)}”</div><div class="deva muted">${esc(phrase.hi)}</div><div class="muted" style="font-size:13px">${esc(phrase.en)}</div>
      <div class="row" style="margin-top:10px"><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Listen</button><button class="btn btn-ghost btn-sm" onclick="A.say(${i}, true)">🐢 Slow</button><button class="btn btn-ghost btn-sm" onclick="A.show(${i})">📱 Show to local</button></div></div>`;
    const g = E.bump(item.cat, 1); refreshChrome(); if (g > 0) toast(`❤️ ${cat(item.cat).label} confidence +${g}%`);
  };

  // ---------- 🆘 Help me now (global floating panel) ----------
  const SOS = (window.SOS_LIST = [
    { hi: "मुझे मदद चाहिए!", roman: "Mujhe madad chahiye!", en: "I need help!" },
    { hi: "पास में हॉस्पिटल कहाँ है?", roman: "Paas mein hospital kahan hai?", en: "Where's the nearest hospital?" },
    { hi: "पुलिस को बुलाइए!", roman: "Police ko bulaiye!", en: "Please call the police!" },
    { hi: "मैं खो गया हूँ।", roman: "Main kho gaya hoon.", en: "I'm lost." },
    { hi: "मुझे हिंदी नहीं आती।", roman: "Mujhe Hindi nahi aati.", en: "I don't speak Hindi." },
  ]);
  document.body.insertAdjacentHTML("beforeend", `
    <button class="sos-fab" onclick="A.sos()" aria-label="Help me now">🆘</button>
    <div class="sos-panel" id="sos-panel">
      <div class="row between"><b>🆘 Help me now</b><button class="btn btn-ghost btn-sm" onclick="A.sos()">✕</button></div>
      <div class="muted" style="font-size:13px;margin:4px 0 10px">Tap 🔊 to play a phrase out loud to someone nearby.</div>
      ${SOS.map((p, i) => `<div class="sos-row"><div><div class="deva" style="font-weight:700">${esc(p.hi)}</div><div style="font-size:13px;color:var(--brand);font-weight:600">${esc(p.roman)}</div><div class="muted" style="font-size:12.5px">${esc(p.en)}</div></div><div class="row" style="gap:6px;flex-wrap:nowrap"><button class="btn btn-ghost btn-sm" onclick="A.sosSay(${i})">🔊</button><button class="btn btn-ghost btn-sm" onclick="A.show(REG.push(SOS_LIST[${i}]) - 1)">📱</button></div></div>`).join("")}
      <a class="btn btn-brand" style="width:100%;margin-top:10px" href="tel:112">📞 Emergency: 112</a>
    </div>`);
  A.sos = () => $("#sos-panel").classList.toggle("open");
  A.sosSay = (i) => { const p = SOS[i]; if (!E.speak(p, { slow: true, onerror: () => toast(`Show them: “${p.hi}”`) })) toast(`Show them: “${p.hi}”`); };

  E.hydrate().finally(render);
  render();
})();
