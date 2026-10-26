// Views + router (hash-based SPA, no build step).
(function () {
  const E = Engine;
  const S = () => E.state;
  const $ = (sel) => document.querySelector(sel);
  const app = $("#app");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // Saved state is data from storage, not code: a value used as a number in markup is forced to be one (anything else shows as 0), so it
  // can never carry markup into text, an attribute or a style.
  const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };
  const pack = () => E.pack();                              // the learner's city, in the language they chose
  // A pack in a language other than Hindi (Marathi in Mumbai, Kannada in Bengaluru): it is read only by a voice of that language, and
  // practice is a word check of what was really recognised, never a score.
  const ownLang = () => E.packLanguage() !== "hi";
  const langName = () => (LANGUAGES.find((l) => l.code === E.packLanguage()) || { name: "Hindi" }).name;
  const replyLang = () => (ownLang() ? langName() : "Hinglish");
  // An honest note where the learner's pack has not been checked by a native speaker yet (content.js CONTENT_REVIEW).
  const reviewNote = () => "";   // review notices are hidden; the review records in content.js are kept
  // A phrase whose words change with the speaker's gender also shows the feminine form (content.js `fem`).
  // The second line under a phrase: its pronunciation guide (French), else its romanised form when that is not just the same text again.
  const alt = (p) => p.pron || (p.roman !== p.hi ? p.roman : "");
  const femNote = (p) => (p.fem ? `<div class="fem-note"><span class="k">Women say</span> <span class="deva">${esc(p.fem.hi)}</span>${alt(p.fem) ? ` · <b>${esc(alt(p.fem))}</b>` : ""}
    <button class="btn btn-ghost btn-sm" onclick="A.say(${reg({ ...p, hi: p.fem.hi, roman: p.fem.roman })})" aria-label="Listen to the feminine form">🔊</button></div>` : "");
  const cat = (k) => CATEGORIES.find((c) => c.key === k);
  const TOPIC_SCENARIO = { transport: "auto", food: "food", shopping: "shopping", directions: "directions", college: "college", smalltalk: "smalltalk", greetings: "greetings" };
  // The roleplay for a topic in the learner's own city: that day's scenario in their pack (Mumbai has its own), Delhi's as the fallback.
  const topicScenario = (key) => { const d = pack().find((x) => x.key === key); return d && SCENARIOS[d.scenario] ? d.scenario : TOPIC_SCENARIO[key]; };
  const barClass = (v) => (v >= 80 ? "ok" : v >= 60 ? "mid" : "low");
  const bar = (v, extra = "") => `<div class="bar ${barClass(num(v))} ${extra}"><i style="width:0" data-w="${num(v)}"></i></div>`;

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
    const lang = E.language();
    if (lang === "hinglish") return { main: esc(p.roman), mainCls: "", second: `<span class="deva">${esc(p.hi)}</span>` };
    if (lang === "en") return { main: esc(p.natural || p.en), mainCls: "", second: `${esc(p.roman)} · <span class="deva">${esc(p.hi)}</span>` };
    return { main: esc(p.hi), mainCls: "deva", second: esc(alt(p)) };
  }

  // ---------- Actions exposed to inline handlers ----------
  const A = (window.A = {
    go: (h) => (location.hash = h),
    say(i, slow) {
      const p = REG[i]; if (!p) return;
      const btn = window.event && window.event.currentTarget instanceof Element ? window.event.currentTarget : null;
      const label = btn ? btn.innerHTML : "";
      if (ownLang() && E.voiceKind() !== E.packLanguage()) {              // never a Hindi voice for a Marathi or Kannada phrase
        return toast(`🔈 This device has no ${langName()} voice, so the phrase can't be played. Read it like this: “${p.roman || p.hi}”`);
      }
      const ok = E.speak(p, {
        slow,
        onstart: () => { if (btn) btn.innerHTML = "🔊 Playing…"; },
        onend: () => { if (btn && label) btn.innerHTML = label; },
        onerror: () => toast(`🔈 Couldn't play audio here. Say it like this: “${p.roman || p.hi}”`),
      });
      if (!ok) toast(`🔈 Audio isn't available in this browser. Say it like this: “${p.roman || p.hi}”`);
      if (ok && btn) { btn.innerHTML = "🔊 Playing…"; setTimeout(() => { if (btn.innerHTML === "🔊 Playing…") btn.innerHTML = label; }, 6000); }
    },
    async practice(i, boxId, category) {
      const p = REG[i]; const box = document.getElementById(boxId); const btn = document.getElementById(boxId + "-btn");
      let transcript = null;
      if (E.canListen) {
        if (btn) { btn.classList.add("rec"); btn.innerHTML = "⏺ Listening…"; }
        box.innerHTML = `<div class="feedback"><span class="muted">🎤 Say: <b>${esc(p.roman)}</b></span></div>`;
        toast("🎤 Listening… say the phrase now");
        transcript = await E.listen();
        if (btn) { btn.classList.remove("rec"); btn.innerHTML = "🎤 Practice"; }
        micHint();
      }
      if (ownLang()) {                                   // no invented score: only a word check of what was really recognised, never "pronunciation"
        box.innerHTML = wordCheckHTML(p, transcript);
        if (transcript) { const st = S(); st.skills.speaking = E.clamp(st.skills.speaking + 1); E.save(); refreshChrome(); }
        return;
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
    const main = p.hi && (/[^\p{Script=Latin}\P{L}]/u.test(p.hi) || E.packLanguage() === "fr") ? p.hi : p.roman;   // the phrase as written: its own script, or French with its accents
    const PLEASE_READ = { mr: "कृपया वाचा", kn: "ದಯವಿಟ್ಟು ಓದಿ", ta: "தயவுசெய்து படியுங்கள்", fr: "Merci de lire", bn: "অনুগ্রহ করে পড়ুন", te: "దయచేసి చదవండి", ur: "براہ کرم پڑھیے", ks: "مہربٲنی کٔرِتھ پٔرِو", doi: "किरपा करियै पढ़ो" };
    o.innerHTML = `<div class="show-inner"><div class="show-tag">🙏 Please read / ${PLEASE_READ[E.packLanguage()] || "कृपया पढ़िए"}</div>
      <div class="show-main deva">${esc(main)}</div>
      ${alt({ ...p, hi: main }) ? `<div class="show-roman">${esc(alt({ ...p, hi: main }))}</div>` : ""}
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
    else if (e === "language-not-supported") toast(`🎤 This browser can't recognise ${ownLang() ? langName() : "this language"} speech. Type your answer instead.`);
  }
  // Marathi and Kannada practice: what speech recognition heard, compared word by word. It is not a pronunciation score and says so;
  // without a transcript nothing was assessed, and the page says that instead of estimating.
  function wordCheckHTML(p, transcript) {
    if (!transcript) {
      const why = !E.canListen ? "This browser has no speech recognition" : E.micError === "language-not-supported" ? `This browser can't recognise ${langName()} speech` : "Nothing was recognised";
      return `<div class="feedback" data-no-score><b>${why}, so nothing was assessed.</b>
        <div class="muted" style="font-size:13px;margin-top:6px">No score is shown: LingoBuddy never guesses one. Say it aloud anyway, or try again in Chrome.</div>
        <div style="margin-top:8px">Say: <b>${esc(p.roman)}</b> <span class="deva muted">${esc(p.hi)}</span></div></div>`;
    }
    const r = E.score(p, transcript);
    return `<div class="feedback" data-word-check><div class="muted" style="font-size:12px;font-weight:700;letter-spacing:.06em">WORD CHECK (NOT A PRONUNCIATION SCORE)</div>
      <div style="margin-top:6px"><b>${r.good.length} of ${r.good.length + r.bad.length} words recognised.</b></div>
      ${r.bad.length ? `<div style="font-size:13px;margin-top:6px"><b>Not recognised:</b> ${r.bad.map((w) => `<span class="word bad">${esc(w)}</span>`).join("")}</div>` : ""}
      <div class="muted" style="font-size:12.5px;margin-top:8px">We heard: “${esc(r.heard || transcript)}”. This compares the words speech recognition heard with the phrase; it does not measure how you pronounced them.</div></div>`;
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
    ["#/lessons", "📘", "My Lessons"], ["#/situations", "🧭", "Situations"], ["#/listening", "🎧", "Listening"], ["#/voice", "🎙️", "Voice Practice"], ["#/plan", "🎯", "My Plan"], ["#/ai-insights", "🧠", "Adaptive Learning"], ["#/ai-tutor", "🤖", "Tutor Chat"], ["#/ai-roleplay", "🎭", "Roleplay"], ["#/rewards", "⭐", "Rewards"], ["#/friends", "👥", "Friends"], ["#/profile", "⚙️", "Profile"],
  ];
  // Phones (Phase 15A): the bottom bar shows a few of the mode's pages and a "More" button that opens the rest of the SAME navigation the
  // sidebar shows (AgeMode.filterNav), so nothing is out of reach on a phone and nothing new is offered. Presentation only.
  const PINNED = { admin: ["#/admin", "#/admin/curriculum", "#/admin/analytics", "#/admin/learners"], parent: ["#/parent", "#/", "#/progress", "#/profile"],
                   teen: ["#/", "#/path", "#/tutor", "#/learn"] };
  const PIN_DEFAULT = ["#/", "#/pack", "#/tutor", "#/learn"];
  function mobileNav(nav, mode) {
    if (nav.length <= 5) return { pinned: nav, more: [] };
    const pinned = (PINNED[mode] || PIN_DEFAULT).map((h) => nav.find((n) => n[0] === h)).filter(Boolean);
    return { pinned, more: nav.filter((n) => !pinned.includes(n)) };
  }
  A.mobileNav = mobileNav;
  A.refreshChrome = () => refreshChrome();
  let sideLast = null;
  function refreshChrome() {
    const h = "#/" + (location.hash.replace(/^#\/?/, "").split("/")[0] || "");
    let act = { "#/lesson": "#/pack", "#/roleplay": "#/pack" }[h] || h;
    const nav = window.AgeMode ? window.AgeMode.filterNav(NAV) : NAV;
    if (window.AgeMode && window.AgeMode.mode() === "admin") {            // admin console pages nest (#/admin/curriculum/lessons/3): the active item is the longest nav link that starts the path
      const here = location.hash.split("?")[0];
      act = nav.map((n) => n[0]).filter((x) => here === x || here.startsWith(x + "/")).sort((a, b) => b.length - a.length)[0] || "#/admin";
    }
    const link = ([href, ic, l]) => `<a href="${href}"${href === act ? ' class="active" aria-current="page"' : ""}><span class="ic" aria-hidden="true">${ic}</span><span class="lb">${l}</span></a>`;
    $("#nav").innerHTML = nav.map(link).join("");
    const { pinned, more } = mobileNav(nav, window.AgeMode ? window.AgeMode.mode() : null);
    const sheet = document.getElementById("more-sheet");
    const open = !!(sheet && !sheet.hidden);
    $("#bottom-nav").innerHTML = pinned.map(link).join("")
      + (more.length ? `<button type="button" class="bn-more${more.some((n) => n[0] === act) ? " active" : ""}" aria-haspopup="dialog" aria-controls="more-sheet" aria-expanded="${open}" onclick="A.moreMenu()"><span class="ic" aria-hidden="true">☰</span><span class="lb">More</span></button>` : "");
    if (sheet) sheet.querySelector(".more-links").innerHTML = more.map(link).join("");
    if (!more.length && open) A.moreMenu(false);
    // Who is signed in, always in view: a Sign in button for visitors, the account's name (to its profile) once signed in. An admin's
    // console has no profile page, so their name is shown as plain text.
    const acct = E.account, mode = window.AgeMode ? window.AgeMode.mode() : null;
    const signOut = `<button type="button" class="account-out" onclick="A.signOut()">Sign out</button>`;
    const accountHTML = !acct ? `<a class="btn btn-primary btn-sm account-btn" href="#/profile">Sign in</a>`
      : (mode === "admin" ? `<span class="account-chip"><span aria-hidden="true">👤</span><span class="lb">${esc(acct.name)}</span></span>`
        : `<a class="account-chip" href="#/profile" aria-label="Your profile: ${esc(acct.name)}"><span aria-hidden="true">👤</span><span class="lb">${esc(acct.name)}</span></a>`) + signOut;
    ["#account", "#account-top"].forEach((sel) => { const el = $(sel); if (el) el.innerHTML = accountHTML; });
    const o = E.overall();
    $("#side-card").innerHTML = `<div class="lbl"><span class="pulse-heart">❤️</span> Local confidence</div><div class="row between"><div class="big" data-count="${o}" data-suffix="%">${o}%</div><span class="chip brand">${esc(S().level)}</span></div>
      ${bar(o)}<div class="muted" style="font-size:12.5px;margin-top:8px">📍 ${esc(E.cityName())} · 🔥 ${num(S().streak)}-day streak</div>
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
      <div class="hero-grid">
        <div>
          <div class="eyebrow">a little language buddy for new cities</div>
          <h1>Just moved here?<br/>Let's get you talking.</h1>
          <p class="sub">LingoBuddy teaches you the stuff you actually need in your first week: getting an auto, ordering food, finding the right metro line, and not panicking when someone talks to you.</p>
          <div class="row" style="gap:12px;margin-top:22px">
            <a class="btn btn-primary btn-lg" href="#/new">I'm New Here →</a>
            <a class="btn btn-ghost btn-lg" href="#/tutor">Practice with the AI</a>
          </div>
          <div class="hero-stats">
            <div><b>7</b><span>days to settle in</span></div>
            <div><b>${pack().reduce((n, d) => n + d.phrases.length, 0)}</b><span>everyday phrases</span></div>
            <div><b>${new Set(pack().map((d) => d.scenario)).size}</b><span>locals to chat with</span></div>
          </div>
        </div>
        <div>
          <div class="float-card note">
            <div class="row between"><small>phrase of the day · day 2, transport</small><button class="chip" onclick="A.say(${i})">🔊 listen</button></div>
            <div class="deva" style="margin-top:8px">${esc(p.hi)}</div>
            <div class="roman">${esc(p.roman)}</div>
            <small>means: “${esc(p.natural)}”</small>
          </div>
          <div class="float-card note">
            <div class="row between"><small>how ready you are</small><b>${E.overall()}%</b></div>
            ${top.map((c) => `<div style="margin-top:10px"><div class="row between" style="font-size:13px"><span>${c.icon} ${c.label}</span><span>${num(c.v)}%</span></div><div class="mini-bar"><i style="width:${num(c.v)}%"></i></div></div>`).join("")}
          </div>
        </div>
      </div>
    </section>
    <div style="margin-top:22px">${rightNow()}</div>
    <div class="quote">
      <div><div class="eyebrow">most language apps</div><div class="old">teach you a language.</div></div>
      <div><div class="eyebrow">this one</div><div class="new">helps you actually live somewhere new.</div></div>
    </div>
    <h2 style="margin-top:28px">Phrases people here really use <small class="muted">(tap one to hear it)</small></h2>
    <div class="loop static"><div class="loop-track">${pack().flatMap((d) => d.phrases.slice(0, 2).map((p) => `<span class="loop-item" onclick="A.say(${reg(p)})"><span>${d.icon}</span><span class="deva">${esc(p.hi)}</span><small>${esc(p.natural)}</small></span>`)).join("")}</div></div>
    <h2 style="margin-top:28px">What you'll get better at</h2>
    <div class="grid g5" style="margin-top:12px">
      ${[["🗣️", "Speaking", "Real phrases, plus feedback on how you say them."], ["📍", "Getting around", "Autos, metro lines and asking for directions."], ["🍜", "Ordering food", "Street food, restaurants and “kam teekha”."], ["🤝", "Making friends", "Small talk with classmates and neighbours."], ["❤️", "Feeling at home", "We track real situations you can handle, not points."]]
        .map(([ic, t, d]) => `<div class="card feature"><div class="icon-tile">${ic}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}
    </div>
    <div style="margin-top:22px">${priceWidget("auto")}</div>
    <div class="card welcome-back" style="margin-top:22px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
      <div class="row" style="gap:14px"><div class="icon-tile">👋</div><div><h3>Hey ${esc(S().name)}, welcome back</h3><div class="muted">You're on day ${Math.min(7, E.daysDone().length + 1)} of your first week in ${esc(E.cityName())}.</div></div></div>
      <div class="row"><a class="btn btn-ghost" href="#/confidence">My progress</a><a class="btn btn-brand" href="#/pack">Keep going →</a></div>
    </div>`;
  }

  // ---------- 🕒 Right now: time-aware situation suggestion ----------
  function rightNow() {
    const h = new Date().getHours();
    const slots = E.local().rightNow || (S().city === "mumbai" && E.language() === "mr" ? [
      [5, 11, "🚆", "Morning commute", "The locals are packed right now. Check fast or slow before you board.", "mum_mr_taxi", { roman: "Hi fast local aahe ki slow?", hi: "ही फास्ट लोकल आहे की स्लो?", en: "Is this the fast train or the slow one?" }],
      [11, 15, "🍔", "Lunch time", "Stalls and canteens are busiest now. Order like a local.", "mum_mr_food", { roman: "Ek vadapav dya.", hi: "एक वडापाव द्या.", en: "One vada pav, please." }],
      [15, 18, "🛍️", "Market hours", "Dadar's markets and Linking Road are open. Time to bargain.", "mum_mr_shopping", { roman: "Shevatcha bhaav sanga.", hi: "शेवटचा भाव सांगा.", en: "What's your best price?" }],
      [18, 22, "🌊", "Sea-face chai", "Marine Drive at sunset is where friendships start.", "mum_mr_smalltalk", { roman: "Ek cutting chaha.", hi: "एक कटिंग चहा.", en: "One half-glass chai, please." }],
      [22, 29, "🌙", "Late night ride home", "Taxis and autos still go by the meter, with a night surcharge after midnight.", "mum_mr_taxi", { roman: "Dada, meterne yenar ka?", hi: "दादा, मीटरने येणार का?", en: "Will you go by the meter?" }],
    ] : S().city === "mumbai" ? [
      [5, 11, "🚆", "Morning commute", "The locals are packed right now. Check fast or slow before you board.", "mum_taxi", { roman: "Yeh fast local hai ya slow?", hi: "ये फ़ास्ट लोकल है या स्लो?", en: "Is this the fast train or the slow one?" }],
      [11, 15, "🍔", "Lunch time", "Stalls and canteens are busiest now. Order like a local.", "mum_food", { roman: "Ek vada pav dena.", hi: "एक वड़ा पाव देना।", en: "One vada pav, please." }],
      [15, 18, "🛍️", "Market hours", "Colaba Causeway and Linking Road are open. Time to bargain.", "mum_shopping", { roman: "Aakhri daam bolo.", hi: "आख़िरी दाम बोलो।", en: "What's your best price?" }],
      [18, 22, "🌊", "Sea-face chai", "Marine Drive at sunset is where friendships start.", "mum_smalltalk", { roman: "Ek cutting chai.", hi: "एक कटिंग चाय।", en: "One half-glass chai, please." }],
      [22, 29, "🌙", "Late night ride home", "Taxis and autos still go by the meter, with a night surcharge after midnight.", "mum_taxi", { roman: "Bhaiya, meter se chaloge?", hi: "भैया, मीटर से चलोगे?", en: "Will you go by the meter?" }],
    ] : [
      [5, 11, "🌅", "Morning commute", "Heading out? The metro is packed right now.", "directions", { roman: "Rajiv Chowk ke liye kaun si line?", hi: "राजीव चौक के लिए कौन सी लाइन?", en: "Which line for Rajiv Chowk?" }],
      [11, 15, "🍛", "Lunch time", "Street stalls are busiest now. Order like a local.", "food", { roman: "Ek plate chhole bhature dena.", hi: "एक प्लेट छोले भटूरे देना।", en: "One plate of chhole bhature, please." }],
      [15, 18, "🛍️", "Market hours", "Sarojini and Lajpat Nagar are open. Time to bargain.", "shopping", { roman: "Thoda kam kijiye na.", hi: "थोड़ा कम कीजिए ना।", en: "Can you do a better price?" }],
      [18, 22, "☕", "Chai o'clock", "Evening chai is where friendships start.", "smalltalk", { roman: "Chai piyenge?", hi: "चाय पिएँगे?", en: "Fancy a chai?" }],
      [22, 29, "🌙", "Late night ride home", "Autos charge extra at night. Agree on the fare first.", "auto", { roman: "Bhaiya, meter se chaloge?", hi: "भैया, मीटर से चलोगे?", en: "Will you go by the meter?" }],
    ]);
    const hh = h < 5 ? h + 24 : h;
    const [, , ic, t, d, sc, p] = slots.find(([a, b]) => hh >= a && hh < b);
    const i = reg(p); const time = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    return `<div class="card now-card"><div class="row" style="gap:16px;flex-wrap:nowrap">
      <div class="icon-tile" style="width:56px;height:56px;font-size:28px">${ic}</div>
      <div style="flex:1;min-width:0"><div class="eyebrow" style="margin:0">🕒 Right now in ${esc(E.cityName())} · ${time}</div>
        <h3>${t}: <span style="font-weight:500;color:var(--ink-2)">${d}</span></h3>
        <div style="margin-top:6px"><b style="font-size:17px">“${esc(p.roman)}”</b> ${p.hi !== p.roman ? `<span class="deva muted">${esc(p.hi)}</span>` : ""} <span class="muted" style="font-size:13px">· ${esc(p.en)}</span></div></div>
      <div class="row" style="flex:none"><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Listen</button><a class="btn btn-primary btn-sm" href="#/roleplay/${sc}">💬 Practice</a></div>
    </div></div>`;
  }

  let onboard = { city: null, lang: null };
  // ---------- "I'm New Here" destinations (frontend/content.js DESTINATIONS: display data; CITIES holds the learning packs) ----------
  const STATUS = { available: ["ok", "Available"], in_development: ["warn", "In Development"], coming_soon: ["", "Coming Soon"] };
  const destCity = (d) => CITIES.find((c) => c.id === d.city);
  const selectable = (d) => d.status !== "coming_soon" && !!destCity(d) && destCity(d).ready;   // never more than the packs allow
  const region = (d) => d.serves.map((s) => s.name).join(" · ") + (d.note ? " · " + d.note : "");
  function destinationCard(d) {
    const [cls, label] = STATUS[d.status] || STATUS.coming_soon;
    const on = selectable(d), chosen = on && onboard.city === d.city;
    if (on) {
      const c = destCity(d);
      return `<button data-tilt class="card hover city ${chosen ? "selected" : ""}" onclick="A.pickCity('${d.id}')" aria-pressed="${chosen}">
        <span class="badge"><span class="chip ${cls}">${label}</span></span>
        <div class="emoji">${d.emoji}</div><h3 style="margin-top:10px">${c.flag} ${esc(c.name)}</h3>${d.alt ? `<div class="muted" style="font-size:12px">Also called ${esc(d.alt)}</div>` : ""}<div class="muted" style="font-size:13px">${esc(c.blurb)}</div>
        ${d.status === "in_development" ? `<div class="dest-note">Early version: content is still being refined.</div>`
          : ""}</button>`;
    }
    return `<button class="card city dest-soon" aria-disabled="true" onclick="A.pickCity('${d.id}')">
      <span class="emoji" aria-hidden="true">${d.emoji}</span><span class="dest-text"><b>${esc(d.name)}</b><small>${esc(region(d))}</small>
      <span class="chip ${cls}">${label}</span></span></button>`;
  }
  function destinationsGrid() {
    const open = DESTINATIONS.filter(selectable), soon = DESTINATIONS.filter((d) => !selectable(d));
    const isUt = (d) => d.serves.every((s) => s.type === "ut");
    const states = soon.filter((d) => !isUt(d)), uts = soon.filter(isUt);
    return `<div class="grid g5">${open.map(destinationCard).join("")}</div>
      <div class="card dest-banner" role="note"><span class="dest-banner-ic" aria-hidden="true">🚧</span>
        <div><b>Coming soon to every state capital and union territory</b><div class="muted">${soon.length} more destinations are on the way. They can't be picked yet: we only open a city once its survival pack is ready.</div></div></div>
      <div class="dest-group"><h3>State capitals <span class="muted">· ${states.length}</span></h3><div class="dest-grid">${states.map(destinationCard).join("")}</div></div>
      <div class="dest-group"><h3>Union territories <span class="muted">· ${uts.length}</span></h3><div class="dest-grid">${uts.map(destinationCard).join("")}</div></div>`;
  }
  // A destination's introduction and First Week preview (content.js DESTINATIONS `intro`, `preview`), where it has them.
  function cityPreview(d) {
    if (!d || (!d.intro && !d.preview)) return "";
    return `<div class="card city-preview" data-city-preview style="margin-bottom:26px"><div class="eyebrow">${d.emoji} About ${esc(d.name)}${d.alt ? ` (${esc(d.alt)})` : ""}</div>
      ${d.intro ? `<p style="margin:6px 0 0">${esc(d.intro)}</p>` : ""}
      ${d.preview ? `<div style="margin-top:12px"><b>Your first week</b><ol class="muted" style="margin:6px 0 0;padding-left:20px;font-size:14px">${d.preview.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>` : ""}</div>`;
  }
  A.destinations = { selectable: (id) => { const d = DESTINATIONS.find((x) => x.id === id); return !!d && selectable(d); } };
  function onboarding() {
    const city = CITIES.find((c) => c.id === onboard.city);
    const langs = city ? city.langs.map((code) => LANGUAGES.find((l) => l.code === code)) : [];
    const LDESC = { hi: "Learn Devanagari script + pronunciation", hinglish: "How people actually talk on the street", en: "Navigate in English, with local phrases",
      mr: "The city's own language: neighbours, markets and the local", kn: "The city's own language: neighbours, autos and darshinis",
      ta: "The city's own language: neighbours, autos and tiffin centres", fr: "The language of White Town, the Lycée and the Alliance française",
      bn: "The city's own language: neighbours, taxis and tea stalls", te: "The city's own language: offices, autos and markets",
      ur: "Hyderabadi Urdu: the old city, the Charminar and the bazaars", ks: "The Valley's own language: Srinagar, the Dal and its markets (draft)",
      doi: "Jammu's own language: the temples, the bazaars and the matadors (draft)" };
    return `
    <div class="eyebrow">🌍 I'm new here</div>
    <h1>Where are you new?</h1>
    <p class="sub">Pick your city and we'll build a survival pack for your first week — real situations, zero awkward moments.</p>
    <div class="step"><b>1</b> Choose your city</div>
    ${destinationsGrid()}
    ${city ? `<div class="reveal" style="margin-top:34px">${cityPreview(DESTINATIONS.find((d) => d.city === city.id))}
      <div class="step"><b>2</b> What language do you want to learn?</div>
      <div class="grid g3">
        ${langs.map((l) => `<button data-tilt class="card hover lang ${onboard.lang === l.code ? "selected" : ""}" onclick="A.pickLang('${l.code}')">
          <div class="icon-tile">${l.code === "hi" ? "🇮🇳" : l.code === "hinglish" ? "🗣️" : ["mr", "kn", "ta", "bn", "te", "ks", "doi"].includes(l.code) ? "🏙️" : l.code === "ur" ? "🕌" : l.code === "fr" ? "🥐" : "🌐"}</div>
          <div><div class="native ${["hi", "mr", "kn", "ta", "bn", "te", "ur", "ks", "doi"].includes(l.code) ? "deva" : ""}">${l.native}</div><div class="muted" style="font-size:13px">${l.name} · ${LDESC[l.code] || ""}</div></div></button>`).join("")}
      </div>
      <div class="muted" style="font-size:13px;margin-top:12px">Also supported by the platform: ${LANGUAGES.filter((l) => !city.langs.includes(l.code)).map((l) => l.name).join(" · ")}</div>
      <div style="margin-top:26px" id="build-area">
        <span class="${onboard.lang ? "star-border" : ""}"><button class="btn btn-brand btn-lg" style="${onboard.lang ? "" : "opacity:.5"}" onclick="A.build()">Build My Survival Pack →</button></span>
      </div>
    </div>` : ""}`;
  }
  A.pickCity = (id) => {
    const d = DESTINATIONS.find((x) => x.id === id) || DESTINATIONS.find((x) => x.city === id);
    if (!d || !selectable(d)) {
      const open = DESTINATIONS.filter(selectable).map((x) => destCity(x).name).join(" and ");
      return toast(`🚧 ${d ? d.name : "That city"} is coming soon. You can start today in ${open}.`);
    }
    const offered = (CITIES.find((x) => x.id === d.city) || { langs: [] }).langs;
    onboard.city = d.city; if (!offered.includes(onboard.lang)) onboard.lang = null;   // a language the new city does not offer is not kept
    render(); setTimeout(() => $("#build-area")?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
  };
  A.pickLang = (code) => { onboard.lang = code; render(); };
  A.build = () => {
    const chosen = CITIES.find((x) => x.id === onboard.city);
    if (!chosen || !chosen.langs.includes(onboard.lang)) {
      const names = chosen ? chosen.langs.map((code) => (LANGUAGES.find((l) => l.code === code) || { name: code }).name) : [];
      return toast(`👆 Pick a language first${names.length ? ": " + names.slice(0, -1).join(", ") + " or " + names[names.length - 1] : ""}.`);
    }
    const st = S(); st.city = onboard.city; st.language = onboard.lang; E.save();
    const steps = [`Mapping everyday situations in ${(CITIES.find((x) => x.id === onboard.city) || CITIES[0]).name}`, "Picking beginner-friendly phrases", "Adding pronunciation guides", "Setting up AI roleplay partners"];
    $("#build-area").innerHTML = `<div class="card" style="max-width:520px"><h3>✨ Building your survival pack…</h3><div id="build-steps" style="margin-top:10px"></div></div>`;
    steps.forEach((s, i) => setTimeout(() => { $("#build-steps") && ($("#build-steps").innerHTML += `<div class="reveal" style="padding:5px 0">✅ ${s}</div>`); }, 280 * (i + 1)));
    setTimeout(() => { confetti(); A.go("#/pack"); }, 280 * steps.length + 450);
  };

  function dayState(d) {
    const done = E.daysDone().includes(d.day);
    const firstOpen = pack().find((x) => !E.daysDone().includes(x.day));
    return done ? "done" : firstOpen && firstOpen.day === d.day ? "current" : "locked";
  }
  function packPage() {
    const days = pack(); const done = E.daysDone().length;
    return `
    <div class="page-head"><div>
      <div class="eyebrow">🗓️ My first week survival pack</div>
      <h1>Your First Week in ${esc(E.cityName())}</h1>
      <p class="sub">7 days. Real situations. Zero awkward moments.</p>${reviewNote()}</div>
      <div class="card" style="padding:16px 20px;min-width:260px">
        <div class="row between"><b><span data-count="${num(done)}">${num(done)}</span> / 7 days complete</b><span class="chip heart">❤️ ${E.overall()}%</span></div>
        <div style="margin-top:10px">${bar(Math.round((done / 7) * 100))}</div>
      </div></div>
    <div class="grid g4">
      ${days.map((d) => {
        const st = dayState(d); const v = num(S().confidence[d.key]);
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
    const sc = SCENARIOS[d.scenario]; const st = dayState(d); const v = num(S().confidence[d.key]);
    return `
    <a class="back" href="#/pack">← First week</a>
    <div class="page-head"><div>
      <div class="eyebrow">Day ${d.day} · ${d.icon} ${d.title}</div>
      <h1>Day ${d.day} — ${d.title}</h1>
      <p class="sub">${d.desc}</p>${reviewNote()}</div>
      <div class="row"><span class="chip heart">❤️ ${v}% confident</span>${st === "done" ? '<span class="chip ok">✓ Completed</span>' : ""}</div></div>
    <div class="situation"><div class="icon-tile">${sc.icon}</div><div><div class="lbl">Situation</div><div class="txt">“${esc(d.situation)}”</div></div>
      <a class="btn btn-primary" style="margin-left:auto" href="#/roleplay/${d.scenario}">💬 Try Conversation</a></div>
    <div class="grid g2">
      ${d.phrases.map((p, n) => {
        const i = reg(p); const disp = phraseDisplay(p); const box = `fb-${d.day}-${n}`;
        return `<div class="card phrase ${S().practiced[p.roman] ? "practiced" : ""}">
          <div class="row between"><span class="chip">Phrase ${n + 1}</span>${S().practiced[p.roman] ? `<span class="chip ok">✓ ${num(S().practiced[p.roman])}%</span>` : ""}</div>
          <div class="main ${disp.mainCls}" style="margin-top:12px">${disp.main}</div>
          <div class="roman">${disp.second}</div>
          <div class="meta">
            <div><div class="k">Translation</div><div class="v">${esc(p.en)}</div></div>
            <div><div class="k">Natural meaning</div><div class="v">${esc(p.natural)}</div></div>
            <div style="grid-column:1/-1"><div class="k">Pronunciation</div><div class="v"><b>${esc(p.pron || p.roman)}</b></div></div>
          </div>${femNote(p)}
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
    if (!E.daysDone().includes(day)) { E.daysDone().push(day); st.xp += 50; }
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
          <input id="rp-input" autocomplete="off" enterkeyhint="send" aria-label="Your reply" placeholder="Type in ${replyLang()} (or English) — e.g. “${esc(sc.start[0])}”" />
          <button class="send" type="submit">➤</button>
        </form>
      </div>
      <div class="stack chat-side">
        <div class="card"><div class="eyebrow">🎬 Scenario</div><h3>${sc.icon} ${esc(sc.title)}</h3><div class="muted" style="font-size:14px">📍 ${esc(sc.place)}</div>
          <div class="tipbox" style="margin-top:12px;font-size:13.5px"><span>🎯</span><div><b>Your goal:</b> ${esc(sc.goal)}</div></div></div>
        <div class="card"><div class="row between"><b>${c.icon} ${c.label}</b><b id="rp-conf">${num(S().confidence[c.key])}%</b></div><div style="margin-top:8px" id="rp-bar">${bar(S().confidence[c.key])}</div>
          <div class="muted" style="font-size:12.5px;margin-top:8px">Every natural reply builds your local confidence.</div></div>
        <div class="card"><b>🎙️ Pronunciation</b><div class="muted" style="font-size:13px;margin:4px 0 10px">Check how your last reply sounded.</div>
          <button class="btn btn-ghost btn-sm" style="width:100%" onclick="A.rpFeedback()">Get pronunciation feedback</button><div id="rp-fb"></div></div>
        <div class="card"><b>More scenarios</b><div class="row" style="margin-top:10px">${Object.entries(SCENARIOS).filter(([k]) => k !== sid && pack().some((d) => d.scenario === k)).map(([k, s]) => `<a class="chip" href="#/roleplay/${k}">${s.icon} ${esc(s.title)}</a>`).join("")}</div></div>
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
    const [ai] = await Promise.all([E.askAI({ mode: "roleplay", scenario: RP.sid, history: RP.msgs }), new Promise((r) => setTimeout(r, 750))]);
    let reply;
    const local = E.roleplayReply(RP.sid, text, RP.used);
    if (ai) reply = { text: ai.reply, en: ai.translation, tip: ai.tip || local.tip, s: ai.suggestions?.length ? ai.suggestions : local.s, end: local.end && local.matched };
    else reply = local;
    const g = E.bump(sc.category, E.looksEnglish(text) ? 1 : 3); RP.gained += g;
    if (reply.end) {
      RP.ended = true; RP.gained += E.bump(sc.category, 6); S().roleplays++;
      const d = pack().find((x) => x.key === sc.category); if (d && !E.daysDone().includes(d.day)) E.daysDone().push(d.day);
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
    const t = await E.listen(); mic.classList.remove("rec"); $("#rp-input").placeholder = `Type in ${replyLang()} (or English)`;
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
    if (ownLang()) { $("#rp-fb").innerHTML = wordCheckHTML(phrase, RP.lastVoice); RP.lastVoice = null; return; }
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
          <div class="conf-row"><span>${c.icon}</span><b>${c.label}</b>${bar(c.v)}<span class="pct" data-count="${num(c.v)}" data-suffix="%">${num(c.v)}%</span></div>`).join("")}
      </div>
    </div>
    <div class="insight" style="margin-top:20px"><div class="spark">✨</div><div><b>AI insight</b><p>${esc(ins.text)}</p></div></div>
    <div class="card reco" style="margin-top:16px">
      <div class="row" style="gap:14px"><div class="icon-tile">${low.icon}</div><div><div class="eyebrow" style="margin:0">Recommended next</div><h3>💬 Practice ${esc(low.label)}</h3>
        <div class="muted">${esc(SCENARIOS[topicScenario(low.key)].title)} with ${esc(SCENARIOS[topicScenario(low.key)].partner)} · ~3 min</div></div></div>
      <span class="star-border"><a class="btn btn-brand btn-lg" href="#/roleplay/${topicScenario(low.key)}">Practice Now →</a></span>
    </div>`;
  }

  // ---------- Tutor ----------
  let tutorBusy = false;
  function tutorPage() {
    const hist = S().tutor;
    const starters = (E.local().tutor || {}).starters || ["I need to ask an auto driver to go to the airport.", "How do I order food less spicy?", "How can I bargain at Sarojini?", "What does 'jugaad' mean?", "How do I make friends in class?"];
    return `
    <div class="page-head"><div><div class="eyebrow">💬 AI tutor</div><h1>Your LingoBuddy Tutor</h1><p class="sub">Describe any situation — I'll give you the exact ${ownLang() ? langName() + " " : ""}words locals use.</p></div>
      ${hist.length ? `<button class="btn btn-ghost btn-sm" onclick="A.tutorClear()">↺ New chat</button>` : ""}</div>
    <div class="card chat" style="height:calc(100vh - 230px)">
      <div class="chat-head"><div class="avatar">🌍</div><div><b>LingoBuddy</b><div class="muted" style="font-size:13px"><span class="online"></span>Knows ${esc(E.cityName())} · remembers this conversation</div></div><span style="margin-left:auto">${aiChip()}</span></div>
      <div class="msgs" id="tmsgs">${tutorMsgs()}</div>
      <div class="suggest" id="tsuggest">${hist.length ? "" : starters.map((s) => `<button onclick="A.tutorSend(this.textContent)">${esc(s)}</button>`).join("")}</div>
      <form class="composer" onsubmit="event.preventDefault();A.tutorSend()">
        <button type="button" class="mic" id="t-mic" onclick="A.tutorMic()" title="Speak">🎤</button>
        <input id="t-input" autocomplete="off" enterkeyhint="send" aria-label="Ask your tutor" placeholder="e.g. How do I ask for the bill politely?" />
        <button class="send" type="submit">➤</button>
      </form>
    </div>`;
  }
  function tutorMsgs() {
    const hist = S().tutor;
    const hello = `<div class="msg ai"><div class="bubble">${esc((E.local().tutor || {}).greet || "Namaste")} ${esc(S().name)}! 👋 I'm your local buddy for ${esc(E.cityName())}. Tell me where you're going or what you need to say, and I'll teach you the words.</div></div>`;
    return hello + hist.map((m, mi) => {
      if (m.role === "me") return `<div class="msg me"><div class="bubble">${esc(m.text)}</div></div>`;
      const topic = Object.prototype.hasOwnProperty.call(TOPIC_SCENARIO, m.topic) ? m.topic : "smalltalk";   // a known key only: it goes into an onclick
      const sc = topicScenario(topic);
      const fresh = m.fresh; delete m.fresh;
      return `<div class="msg ai" style="max-width:86%"><div class="bubble"><span ${fresh ? "data-type" : ""}>${esc(m.intro || m.text)}</span>
        ${(m.phrases || []).map((p, n) => { const i = reg(p); const box = `tfb-${mi}-${n}`; return `<div class="phrase-mini">${p.label ? `<div class="lab">${esc(p.label)}</div>` : ""}
          <div class="r">“${esc(p.roman)}”</div>${p.hi && p.hi !== p.roman ? `<div class="h">${esc(p.hi)}</div>` : ""}<div class="e">${esc(p.en)}</div>
          <div class="row" style="margin-top:8px;gap:6px"><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊 Hear it</button><button class="btn btn-ghost btn-sm" id="${box}-btn" onclick="A.practice(${i}, '${box}', '${topic}')">🎤 Say it</button><button class="btn btn-ghost btn-sm" onclick="A.show(${i})">📱 Show</button><a class="btn btn-ghost btn-sm" href="#/roleplay/${sc}">💬 Practice</a></div><div id="${box}"></div></div>`; }).join("")}
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
      <div class="card" style="padding:14px 18px"><div class="muted" style="font-size:12.5px;font-weight:600">Pronunciation skill</div><div class="row between" style="gap:20px"><b style="font-size:22px">${num(S().skills.pronunciation)}%</b><span class="chip ${E.canListen ? "ok" : "warn"}">${E.canListen ? "🎙️ Live scoring" : "⌨️ Estimate mode"}</span></div></div></div>
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
    return `<div class="page-head"><div><div class="eyebrow">📚 Learn</div><h1>Build your foundations</h1><p class="sub">Vocabulary, reading and listening — all built from real ${esc(E.cityName())} situations. Level: <b>${esc(S().level)}</b></p></div></div>
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
    const r = E.readings()[readIdx % E.readings().length];
    return `<div class="grid g2" style="align-items:start">
      <div class="card"><div class="row between"><h2>${esc(r.title)}</h2><span class="chip brand">${r.level}</span></div>
        ${r.lines.map((l) => { const i = reg(l); return `<div class="reading-line"><div class="row between"><div class="deva">${esc(l.hi)}</div><button class="btn btn-ghost btn-sm" onclick="A.say(${i})">🔊</button></div>${alt(l) ? `<div class="muted" style="font-size:14px">${esc(alt(l))}</div>` : ""}${readShow ? `<div style="font-size:14.5px;color:var(--brand)">${esc(l.en)}</div>` : ""}</div>`; }).join("")}
        <div class="row" style="margin-top:14px"><button class="btn btn-ghost btn-sm" onclick="A.readToggle()">${readShow ? "Hide" : "Show"} English translation</button>
        <button class="btn btn-ghost btn-sm" onclick="A.readNext()">Next passage →</button></div></div>
      <div class="card"><h3>Comprehension check</h3><div class="muted" style="font-size:14px">Answer in any order.</div>
        ${r.questions.map((q, qi) => `<div style="margin-top:16px"><b>${qi + 1}. ${esc(q.q)}</b>${q.options.map((o, oi) => `<button class="opt" id="rq-${qi}-${oi}" onclick="A.readAns(${qi}, ${oi})">${esc(o)}</button>`).join("")}</div>`).join("")}</div></div>`;
  }
  A.readToggle = () => { readShow = !readShow; render(); };
  A.readNext = () => { readIdx = (readIdx + 1) % E.readings().length; readShow = false; render(); };
  A.readAns = (qi, oi) => {
    const q = E.readings()[readIdx % E.readings().length].questions[qi]; const ok = q.a === oi;
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
      ${listenQ.done ? `<div style="margin-top:16px"><div class="deva" style="font-size:22px">${esc(listenQ.ans.hi)}</div>${alt(listenQ.ans) ? `<div class="muted">${esc(alt(listenQ.ans))}</div>` : ""}<button class="btn btn-primary" style="margin-top:14px" onclick="A.listenNext()">Next →</button></div>` : ""}</div>`;
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
    if (pl && answered === 0) return `<div class="card" style="max-width:640px;margin:0 auto;text-align:center;padding:36px"><div style="font-size:44px">🎯</div><h2>Your level: ${esc(S().level)} ${S().level === "A1" ? "Beginner" : "Elementary"}</h2><p class="muted">Placement score ${pl.score}/${E.placement().length}. Your survival pack is tuned to this level.</p>
      <div class="row" style="justify-content:center;gap:6px;margin:14px 0">${(window.CEFR_LEVELS || ["A1", "A2", "B1", "B2", "C1", "C2"]).map((l) => `<span class="chip ${l === S().level ? "brand" : ""}">${l}</span>`).join("")}</div>
      <button class="btn btn-ghost" onclick="A.placeRetake()">Retake test</button></div>`;
    return `<div class="card" style="max-width:720px;margin:0 auto"><div class="row between"><h2>Quick level check</h2><span class="chip">${answered} / ${E.placement().length}</span></div><p class="muted">5 questions · CEFR placement (A1 → C2)</p>
      ${E.placement().map((q, qi) => `<div style="margin-top:18px"><b>${qi + 1}. ${esc(q.q)}</b>${q.options.map((o, oi) => `<button class="opt ${placeAns[qi] !== undefined ? (oi === q.a ? "right" : placeAns[qi] === oi ? "wrong" : "") : ""}" onclick="A.placeAns(${qi}, ${oi})">${esc(o)}</button>`).join("")}</div>`).join("")}
      <button class="btn btn-brand" style="margin-top:22px" ${answered === E.placement().length ? "" : "disabled"} onclick="A.placeFinish()">See my level →</button></div>`;
  }
  A.placeAns = (qi, oi) => { if (placeAns[qi] === undefined) { placeAns[qi] = oi; render(); } };
  A.placeFinish = () => {
    const score = E.placement().filter((q, i) => placeAns[i] === q.a).length;
    S().placement = { score, at: Date.now() }; S().level = score >= 5 ? "A2" : "A1"; E.save(); placeAns = {}; confetti(); render(); refreshChrome();
  };
  A.placeRetake = () => { placeAns = {}; S().placement = null; render(); };

  // ---------- Progress ----------
  function progressPage() {
    const st = S(); const done = E.daysDone().length; const cur = pack().find((d) => !E.daysDone().includes(d.day));
    const named = E.local().achievements || {};            // the same achievements, named for the learner's city and language (content.js LOCAL_CONTENT)
    const ACH = [["first-words", "👋", "First words", "Said your first Hindi phrase"], ["auto-pro", "🛺", "Auto pro", "Negotiated an auto fare"], ["foodie", "🍛", "Dilli foodie", "Ordered street food"], ["first-chat", "💬", "Conversationalist", "Finished an AI roleplay"], ["bargainer", "🛍️", "Sarojini bargainer", "Won a bargain"], ["local", "❤️", "Basically local", "Reached 90% confidence"]]
      .map(([id, ...rest]) => [id, ...(named[id] || rest)]);
    if (E.overall() >= 90 && !st.achievements.includes("local")) st.achievements.push("local");
    return `
    <div class="page-head"><div><div class="eyebrow">🏆 Progress</div><h1>Your journey so far</h1><p class="sub">Every day in ${esc(E.cityName())} gets a little easier.</p></div></div>
    <div class="grid g4">
      <div class="card stat"><div class="k">Current level</div><div class="v">${esc(st.level)} <span style="font-size:16px;color:var(--ink-3)">${st.level === "A1" ? "Beginner" : "Elementary"}</span></div></div>
      <div class="card stat"><div class="k">Weekly goal</div><div class="v"><span data-count="${num(done)}">${num(done)}</span> / 7</div><div class="muted" style="font-size:13px">situations completed</div></div>
      <div class="card stat"><div class="k">Streak</div><div class="v">🔥 <span data-count="${num(st.streak)}">${num(st.streak)}</span> days</div></div>
      <div class="card stat" style="cursor:pointer" onclick="A.go('#/confidence')"><div class="k">❤️ Local confidence</div><div class="v grad-text" data-count="${E.overall()}" data-suffix="%">${E.overall()}%</div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Your journey</h3><div class="journey" style="margin-top:12px">
      ${pack().map((d) => { const isDone = E.daysDone().includes(d.day); const isCur = cur && cur.day === d.day; return `<a class="j ${isDone ? "done" : isCur ? "cur" : ""}" href="#/lesson/${d.day}"><span>${isDone ? "✓" : isCur ? "→" : "🔒"}</span>Day ${d.day}</a>`; }).join("")}</div></div>
    <div class="grid g2" style="margin-top:16px;align-items:start">
      <div class="card"><h3>Skills</h3>${[["🗣️", "Speaking", "speaking"], ["🎧", "Listening", "listening"], ["📚", "Vocabulary", "vocabulary"], ["🎙️", "Pronunciation", "pronunciation"]].map(([ic, l, k]) => `<div class="conf-row" style="grid-template-columns:26px 120px 1fr 48px"><span>${ic}</span><b>${l}</b>${bar(st.skills[k])}<span class="pct">${num(st.skills[k])}%</span></div>`).join("")}</div>
      <div class="card"><div class="row between"><h3>Achievements</h3><span class="chip warn">⚡ <span data-count="${num(st.xp)}">${num(st.xp)}</span> XP</span></div>
        <div class="grid g2" style="margin-top:12px;gap:10px">${ACH.map(([id, ic, t, d]) => `<div class="ach ${st.achievements.includes(id) ? "" : "off"}"><div class="icon-tile">${ic}</div><div><b style="font-size:14px">${t}</b><div class="muted" style="font-size:12.5px">${d}</div></div></div>`).join("")}</div></div>
    </div>
    <div class="row" style="margin-top:22px"><button class="btn btn-ghost btn-sm" onclick="A.resetDemo()">${E.account ? "↺ Start my progress over" : "↺ Reset demo data"}</button></div>`;
  }
  A.resetDemo = () => { E.reset(); RP = null; flashSession = null; toast(E.account ? "Your progress has been reset." : "Demo data reset — Alex is back to Day 4."); render(); };

  // ---------- Router ----------
  // Signed-in accounts only (Phase 15A): until we know who is looking nothing is shown, and a visitor who is not signed in gets the sign-in
  // screen (with the 🆘 help button, which needs no account) instead of any page. The server enforces its own rules on every API call.
  function gate() {
    document.body.classList.add("gated");
    A.moreMenu(false, true);
    app.innerHTML = E.ready ? ProfileView.gate() : `<div class="gate"><div class="card muted gate-wait">Loading…</div></div>`;
    Bits.enhance(app);
  }
  // Sign out from anywhere (every mode, admins included): the server ends the session and clears the cookie, then the sign-in screen returns.
  A.signOut = async () => {
    const btns = document.querySelectorAll(".account-out");
    btns.forEach((b) => { b.disabled = true; });
    try { await window.LBApi.api("POST", "/api/auth/logout"); } catch (e) {}
    await A.identityChanged();
    toast("You're signed out. See you soon! 👋");
  };
  A.identityChanged = async () => {
    await E.hydrate();
    if (window.AgeMode) await window.AgeMode.refresh();
    render();
  };
  function render() {
    if (!E.ready || !E.account) return gate();
    document.body.classList.remove("gated");
    REG = window.REG = [];
    let [route, arg] = location.hash.replace(/^#\/?/, "").split("/");
    if (window.AgeMode) { const r = window.AgeMode.routeFor(route); if (r !== route) { route = r; arg = undefined; } }
    const views = { "": landing, new: onboarding, pack: packPage, lesson: () => lessonPage(arg), roleplay: () => roleplayPage(arg), confidence: confidencePage, tutor: tutorPage, speaking: speakingPage, learn: learnPage, progress: progressPage, profile: ProfileView.page, lessons: () => LessonsView.page(arg), situations: () => SituationsView.page(arg), listening: () => ListeningView.page(arg), voice: VoiceView.page, plan: PlanView.page, kids: () => KidsView.page(arg), path: () => TeenView.page(), parent: () => ParentView.page(arg), rewards: () => RewardsView.page(), friends: () => FriendsView.page(), "ai-tutor": () => AiTutorView.page(arg), "ai-roleplay": () => AiRoleplayView.page(arg), "ai-insights": () => AdaptiveView.page(), admin: () => AdminView.page() };
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
    A.moreMenu(false, true);                                         // a page was chosen: the menu closes, focus stays with the new page
    lastRoute = r; render(); window.scrollTo(0, 0);
  });
  // ---------- 💰 Fair Price Check (approximate typical prices, per city) ----------
  const DELHI_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km)", min: 80, max: 120, cat: "transport" },
    { id: "rick", label: "🚲 Cycle-rickshaw (1–2 km)", min: 20, max: 50, cat: "transport" },
    { id: "jacket", label: "🧥 Street-market jacket", min: 300, max: 600, cat: "shopping" },
    { id: "kurta", label: "👕 Cotton kurta (market)", min: 250, max: 500, cat: "shopping" },
    { id: "chhole", label: "🍛 Plate of chhole bhature", min: 60, max: 120, cat: "food" },
    { id: "chai", label: "☕ Cutting chai", min: 10, max: 20, cat: "food" },
  ];
  const MUMBAI_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, by meter)", min: 70, max: 110, cat: "transport", meter: true },
    { id: "taxi", label: "🚕 Kaali-peeli taxi (~5 km, by meter)", min: 90, max: 150, cat: "transport", meter: true },
    { id: "local", label: "🚆 Local train ticket (second class)", min: 5, max: 20, cat: "transport", fixed: true },
    { id: "jacket", label: "🧥 Street-market jacket (Colaba / Linking Road)", min: 350, max: 700, cat: "shopping" },
    { id: "kurta", label: "👕 Cotton kurta (Colaba Causeway / Dadar market)", min: 300, max: 600, cat: "shopping" },
    { id: "vadapav", label: "🍔 Vada pav", min: 15, max: 30, cat: "food" },
    { id: "chai", label: "☕ Cutting chai", min: 10, max: 20, cat: "food" },
  ];
  // Bengaluru: autos ₹36 for the first 2 km then ₹18/km (the Bengaluru Urban fare revision in force from 1 August 2025), so ~5 km ≈ ₹90; Namma Metro
  // ₹10–90 (BMRCL fare table, February 2025), with up to 5% a year allowed from February 2026, hence ₹95. Sources: docs/CONTENT_REVIEW.md.
  const BENGALURU_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, by meter)", min: 80, max: 120, cat: "transport", meter: true,
      high: "🚩 Too high. Bengaluru autos should go by the meter (₹36 for the first 2 km, then ₹18 a km): ask for it, or book through an app." },
    { id: "metro", label: "🚇 Namma Metro ticket", min: 10, max: 95, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹10–90 in the 2025 table, up to 5% more after a yearly revision): buy a token at the counter or a QR ticket in the Namma Metro app." },
    { id: "kurta", label: "👕 Cotton kurta (Commercial Street)", min: 300, max: 700, cat: "shopping" },
    { id: "tshirt", label: "👕 T-shirt (street market)", min: 200, max: 500, cat: "shopping" },
    { id: "dosa", label: "🥞 Masala dosa (darshini)", min: 50, max: 120, cat: "food" },
    { id: "coffee", label: "☕ Filter coffee", min: 15, max: 40, cat: "food" },
  ];
  // Chennai: the official auto meter fare (₹25 for the first 1.8 km, then ₹12/km) dates from 2013 and a revision is pending, so drivers
  // quote their own fares: the auto range is an agreed fare, not a meter reading. Chennai Metro tokens ₹10–50. Sources: docs/CONTENT_REVIEW.md.
  const CHENNAI_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, agreed fare)", min: 80, max: 150, cat: "transport" },
    { id: "metro", label: "🚇 Chennai Metro token", min: 10, max: 50, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹10–50 for a token): buy a token at the counter or a QR ticket in the CMRL app." },
    { id: "kurta", label: "👕 Cotton kurta (Ranganathan Street)", min: 300, max: 700, cat: "shopping" },
    { id: "tshirt", label: "👕 T-shirt (street market)", min: 200, max: 500, cat: "shopping" },
    { id: "idli", label: "🍚 Plate of idli (tiffin centre)", min: 30, max: 70, cat: "food" },
    { id: "coffee", label: "☕ Filter coffee", min: 15, max: 35, cat: "food" },
  ];
  // Puducherry: scooter rental ₹300–700 a day (rental shops' published rates); autos don't use meters, so the auto item is an agreed fare.
  // The other ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const PUDUCHERRY_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~3 km, agreed fare)", min: 100, max: 200, cat: "transport" },
    { id: "scooter", label: "🛵 Scooter rental (one day)", min: 300, max: 700, cat: "transport" },
    { id: "bicycle", label: "🚲 Bicycle rental (one day)", min: 100, max: 200, cat: "transport" },
    { id: "bag", label: "👜 Handloom bag (Goubert Market)", min: 250, max: 600, cat: "shopping" },
    { id: "fishmeal", label: "🐟 Fish curry meal (seaside restaurant)", min: 150, max: 350, cat: "food" },
    { id: "coffee", label: "☕ Filter coffee", min: 15, max: 35, cat: "food" },
  ];
  // Jaipur: Jaipur Metro (Pink Line) ₹10–30 since the fare revision of 31 January 2025; autos rarely use the meter, so the auto item is an
  // agreed fare. The other ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const JAIPUR_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, agreed fare)", min: 80, max: 150, cat: "transport" },
    { id: "metro", label: "🚇 Jaipur Metro token", min: 10, max: 30, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹10–30 on the Pink Line): buy a token at the counter." },
    { id: "mojdi", label: "👞 Pair of mojaris (Bapu Bazaar)", min: 300, max: 700, cat: "shopping" },
    { id: "kurta", label: "👕 Block-print cotton kurta (market)", min: 300, max: 700, cat: "shopping" },
    { id: "kachori", label: "🥟 Pyaaz kachori", min: 20, max: 40, cat: "food" },
    { id: "lassi", label: "🥛 Lassi in a kulhad", min: 30, max: 70, cat: "food" },
  ];
  // Lucknow: Lucknow Metro (Red Line) ₹10–60; shared autos and tempos charge per seat on fixed routes (the transport department's per-km
  // rates), private autos an agreed fare. The other ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const LUCKNOW_PRICES = [
    { id: "auto", label: "🛺 Private auto (~5 km, agreed fare)", min: 80, max: 150, cat: "transport" },
    { id: "shared", label: "🛺 Shared auto or tempo seat (~3 km)", min: 10, max: 30, cat: "transport" },
    { id: "metro", label: "🚇 Lucknow Metro token", min: 10, max: 60, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹10–60 on the Red Line): buy a token at the counter or a QR ticket." },
    { id: "chikan", label: "🧵 Chikankari kurta (Chowk, handwork)", min: 500, max: 1200, cat: "shopping" },
    { id: "kebab", label: "🍢 Plate of galouti kebabs (Aminabad)", min: 80, max: 200, cat: "food" },
    { id: "chai", label: "☕ Chai", min: 10, max: 20, cat: "food" },
  ];
  // Kolkata: Metro Blue Line ₹5–25 (Metro Railway Kolkata's fare slabs); yellow taxis go by the meter, but published tariffs disagree, so the
  // taxi range is an estimate. The other ranges are estimates too. Sources: docs/CONTENT_REVIEW.md.
  const KOLKATA_PRICES = [
    { id: "taxi", label: "🚕 Yellow taxi (~5 km, by meter)", min: 100, max: 160, cat: "transport", meter: true,
      high: "🚩 Too high. Kolkata's yellow taxis should go by the meter: ask for it, or book an app cab." },
    { id: "metro", label: "🚇 Kolkata Metro token (Blue Line)", min: 5, max: 25, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹5–25 on the Blue Line): buy a token at the counter or a QR ticket." },
    { id: "saree", label: "🥻 Taant cotton saree (Gariahat)", min: 500, max: 1200, cat: "shopping" },
    { id: "kurta", label: "👕 Cotton kurta (New Market)", min: 300, max: 700, cat: "shopping" },
    { id: "roll", label: "🌯 Egg roll", min: 50, max: 100, cat: "food" },
    { id: "cha", label: "☕ Tea in a clay cup", min: 10, max: 20, cat: "food" },
  ];
  // Hyderabad: Hyderabad Metro ₹11–69 (the fare chart in force from 24 May 2025); autos should use the meter but many drivers quote a fare, so
  // the auto range is an agreed fare. The other ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const HYDERABAD_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, agreed fare)", min: 80, max: 150, cat: "transport" },
    { id: "metro", label: "🚇 Hyderabad Metro ticket", min: 11, max: 69, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹11–69): buy a ticket at the counter or a QR ticket in the app." },
    { id: "bangles", label: "💍 Set of lac bangles (Laad Bazaar)", min: 300, max: 800, cat: "shopping" },
    { id: "pearls", label: "🦪 String of pearls (Pathargatti)", min: 1500, max: 3000, cat: "shopping" },
    { id: "biryani", label: "🍛 Plate of biryani", min: 200, max: 350, cat: "food" },
    { id: "chai", label: "☕ Irani chai", min: 15, max: 30, cat: "food" },
  ];
  // Bhopal: Bhopal Metro's Orange Line ₹20–40 (Subhash Nagar–AIIMS, open since December 2025); autos rarely use the meter, so the auto item is
  // an agreed fare; shared "magic" vans are paid per seat. The other ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const BHOPAL_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, agreed fare)", min: 70, max: 130, cat: "transport" },
    { id: "magic", label: "🚐 Shared 'magic' van seat (~3 km)", min: 10, max: 20, cat: "transport" },
    { id: "metro", label: "🚇 Bhopal Metro token", min: 20, max: 40, cat: "transport", fixed: true,
      high: "🚩 Metro fares are fixed (₹20–40 on the Orange Line): buy a token at the counter." },
    { id: "batua", label: "👛 Zari batua (Chowk Bazaar)", min: 300, max: 700, cat: "shopping" },
    { id: "poha", label: "🥣 Plate of poha-jalebi", min: 30, max: 60, cat: "food" },
    { id: "chai", label: "☕ Chai", min: 10, max: 20, cat: "food" },
  ];
  // Shimla: no autos (the hills are too steep), so the ride is a taxi at an agreed union rate; the public Lift from Cart Road to the Mall and
  // HRTC town buses are cheap. All ranges are estimates. Sources: docs/CONTENT_REVIEW.md.
  const SHIMLA_PRICES = [
    { id: "taxi", label: "🚕 Taxi ride (~5 km, agreed fare)", min: 250, max: 400, cat: "transport" },
    { id: "bus", label: "🚌 HRTC town bus", min: 10, max: 30, cat: "transport" },
    { id: "lift", label: "🛗 Lift, Cart Road to the Mall", min: 10, max: 20, cat: "transport" },
    { id: "topi", label: "🧢 Himachali topi (Lakkar Bazaar)", min: 200, max: 450, cat: "shopping" },
    { id: "siddu", label: "🥟 Plate of siddu", min: 40, max: 90, cat: "food" },
    { id: "chai", label: "☕ Chai", min: 10, max: 25, cat: "food" },
  ];
  // Jammu & Kashmir: the official Dal Lake shikara rate is ₹770 for the first hour per boat (J&K tourism department, as reported in 2025-26;
  // boatmen at Dal Gate often ask for more); autos are an agreed fare, matadors a few rupees a seat. The other ranges are estimates.
  // Sources: docs/CONTENT_REVIEW.md.
  const JK_PRICES = [
    { id: "auto", label: "🛺 Auto ride (~5 km, agreed fare)", min: 100, max: 200, cat: "transport" },
    { id: "shikara", label: "🛶 Shikara on the Dal (one hour, per boat)", min: 700, max: 800, cat: "transport", fixed: true,
      high: "🚩 Too high. The official rate is about ₹770 for the first hour per boat: ask to see the rate board at the ghat." },
    { id: "matador", label: "🚐 Matador seat in Jammu (~5 km)", min: 10, max: 20, cat: "transport" },
    { id: "pashmina", label: "🧣 Pashmina shawl (real, plain)", min: 3500, max: 7000, cat: "shopping" },
    { id: "kahwa", label: "🍵 Cup of kahwa", min: 30, max: 80, cat: "food" },
    { id: "kalari", label: "🧀 Kalari kulcha (Jammu)", min: 40, max: 80, cat: "food" },
  ];
  const cityPrices = () => ({ mumbai: MUMBAI_PRICES, bengaluru: BENGALURU_PRICES, chennai: CHENNAI_PRICES, puducherry: PUDUCHERRY_PRICES, jaipur: JAIPUR_PRICES, lucknow: LUCKNOW_PRICES, kolkata: KOLKATA_PRICES, hyderabad: HYDERABAD_PRICES, bhopal: BHOPAL_PRICES, jk: JK_PRICES, shimla: SHIMLA_PRICES }[S().city] || DELHI_PRICES);
  const ALL_PRICES = [...DELHI_PRICES, ...MUMBAI_PRICES, ...BENGALURU_PRICES, ...CHENNAI_PRICES, ...PUDUCHERRY_PRICES, ...JAIPUR_PRICES, ...LUCKNOW_PRICES, ...KOLKATA_PRICES, ...HYDERABAD_PRICES, ...BHOPAL_PRICES, ...JK_PRICES, ...SHIMLA_PRICES];
  function priceWidget(want) {
    const PRICES = cityPrices();                              // the asked-for item, else the same kind of item in this city (chhole → vada pav)
    const pick = (PRICES.find((p) => p.id === want) || PRICES.find((p) => p.cat === (ALL_PRICES.find((x) => x.id === want) || {}).cat) || PRICES[0]).id;
    return `<div class="card price-card"><div class="row between"><div><div class="eyebrow" style="margin:0">💰 Fair price check</div><h3>Getting a fair deal?</h3></div><span class="chip">${esc(E.cityName())} · approx.</span></div>
      <div class="row" style="margin-top:12px">
        <select id="pc-item" class="pc-in">${PRICES.map((p) => `<option value="${p.id}" ${p.id === pick ? "selected" : ""}>${p.label}</option>`).join("")}</select>
        <input id="pc-quote" class="pc-in" type="number" min="1" inputmode="numeric" aria-label="Price they quoted, in rupees" placeholder="They said ₹…" style="width:130px" onkeydown="if(event.key==='Enter')A.priceCheck()" />
        <button class="btn btn-primary btn-sm" onclick="A.priceCheck()">Check</button>
      </div><div id="pc-out"></div></div>`;
  }
  A.priceCheck = () => {
    const item = cityPrices().find((p) => p.id === $("#pc-item").value); const q = parseInt($("#pc-quote").value, 10);
    if (!q || q < 1) return toast("💰 Type the price they quoted, e.g. 150");
    const mid = Math.round((item.min + item.max) / 2 / 10) * 10 || item.min;
    // what to say, in the learner's language: the city's own (LOCAL_CONTENT priceSay, Kannada in Bengaluru), Marathi for a Marathi learner
    // in Mumbai, Hindi otherwise
    const own = E.local().priceSay;
    const say = own ? own(item.max, mid) : E.language() === "mr" ? {
      ticket: { roman: "Churchgatecha ek tikit dya.", hi: "चर्चगेटचं एक तिकीट द्या.", en: "One ticket to Churchgate, please." },
      meter: { roman: "Dada, meterne chala.", hi: "दादा, मीटरने चला.", en: "Please go by the meter." },
      fair: { roman: "Theek aahe, chala.", hi: "ठीक आहे, चला.", en: "Okay, let's go / deal." },
      counter: { roman: `Dada, ${item.max}la dyal ka?`, hi: `दादा, ${item.max}ला द्याल का?`, en: `Will you do it for ₹${item.max}?` },
      high: { roman: `Khup mahaag aahe, dada. ${mid}la dyal ka?`, hi: `खूप महाग आहे, दादा. ${mid}ला द्याल का?`, en: `That's too expensive. Will you do ₹${mid}?` },
    } : {
      ticket: { roman: "Churchgate ka ek ticket dena.", hi: "चर्चगेट का एक टिकट देना।", en: "One ticket to Churchgate, please." },
      meter: { roman: "Bhaiya, meter se chalo.", hi: "भैया, मीटर से चलो।", en: "Please go by the meter." },
      fair: { roman: "Theek hai, chaliye.", hi: "ठीक है, चलिए।", en: "Okay, let's go / deal." },
      counter: { roman: `Bhaiya, ${item.max} mein doge?`, hi: `भैया, ${item.max} में दोगे?`, en: `Will you do it for ₹${item.max}?` },
      high: { roman: `Bahut mehenga hai, bhaiya. ${mid} mein doge?`, hi: `बहुत महंगा है, भैया। ${mid} में दोगे?`, en: `That's too expensive. Will you do ₹${mid}?` },
    };
    let v, cls, phrase;
    if (item.fixed) { v = q <= item.max ? "✅ That's the normal fare." : item.high || "🚩 Train fares are fixed: buy at the counter or in the UTS app."; cls = q <= item.max ? "ok" : "heart"; phrase = say.ticket; }
    else if (item.meter) { v = q <= item.max ? "✅ About what the meter shows." : item.high || "🚩 Too high. In Mumbai autos and taxis go by the meter: ask for it."; cls = q <= item.max ? "ok" : "heart"; phrase = say.meter; }
    else if (q <= item.max) { v = "✅ Fair price. Go for it!"; cls = "ok"; phrase = say.fair; }
    else if (q <= item.max * 1.35) { v = "🤏 A little high. Counter politely:"; cls = "warn"; phrase = say.counter; }
    else { v = "🚩 Too high. Bargain or walk away:"; cls = "heart"; phrase = say.high; }
    const i = reg(phrase);
    $("#pc-out").innerHTML = `<div class="feedback"><div class="row between"><b>${v}</b><span class="chip ${cls}">Typical ₹${item.min}–${item.max}</span></div>
      <div style="margin-top:8px;font-size:18px;font-weight:700">“${esc(phrase.roman)}”</div>${phrase.hi !== phrase.roman ? `<div class="deva muted">${esc(phrase.hi)}</div>` : ""}<div class="muted" style="font-size:13px">${esc(phrase.en)}</div>
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
  // The phone "More" menu: a dialog over the page. Opening moves focus into it, Tab stays inside it, Escape / the backdrop / ✕ close it and
  // focus goes back to the More button; choosing a page closes it (hashchange above).
  document.body.insertAdjacentHTML("beforeend", `
    <div class="more-sheet" id="more-sheet" role="dialog" aria-modal="true" aria-labelledby="more-title" hidden>
      <div class="more-backdrop" onclick="A.moreMenu(false)"></div>
      <div class="more-panel">
        <div class="row between"><b id="more-title">More pages</b><button type="button" class="btn btn-ghost btn-sm" onclick="A.moreMenu(false)" aria-label="Close menu">✕</button></div>
        <nav class="more-links" aria-label="More pages"></nav>
      </div>
    </div>`);
  A.moreMenu = (want, quiet) => {
    const sheet = document.getElementById("more-sheet");
    if (!sheet) return;
    const show = want === undefined ? sheet.hidden : !!want;
    if (show === !sheet.hidden) return;
    sheet.hidden = !show;
    const btn = document.querySelector(".bn-more");
    if (btn) btn.setAttribute("aria-expanded", String(show));
    if (show) { const first = sheet.querySelector(".more-links a"); if (first) first.focus(); }
    else if (btn && !quiet) btn.focus();
  };
  document.addEventListener("keydown", (e) => {
    const sheet = document.getElementById("more-sheet");
    if (!sheet || sheet.hidden) return;
    if (e.key === "Escape") { A.moreMenu(false); return; }
    if (e.key !== "Tab") return;
    const items = [...sheet.querySelectorAll(".more-panel a, .more-panel button")];
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  // ---------- Connection status ----------
  // Offline: a calm notice that nothing can be loaded or saved until the connection is back. Nothing is queued, nothing pretends to be saved.
  document.body.insertAdjacentHTML("beforeend", `
    <div class="net-banner" id="net-banner" role="status" aria-live="polite" hidden>
      <span>📡 <b>You're offline.</b> Nothing can be loaded or saved until you reconnect.</span>
      <button type="button" class="btn btn-ghost btn-sm" onclick="location.reload()">Retry</button>
    </div>`);
  function netStatus() { const b = document.getElementById("net-banner"), nav = window.navigator; if (b) b.hidden = !(nav && nav.onLine === false); }
  window.addEventListener("online", netStatus);
  window.addEventListener("offline", netStatus);
  netStatus();
  A.sos = () => $("#sos-panel").classList.toggle("open");
  A.sosSay = (i) => { const p = SOS[i]; if (!E.speak(p, { slow: true, locale: "hi-IN", onerror: () => toast(`Show them: “${p.hi}”`) })) toast(`Show them: “${p.hi}”`); };

  E.hydrate().finally(render);
  if (window.AgeMode) window.AgeMode.refresh().finally(render);   // the learner's mode (child / teen) shapes the navigation and home
  render();
})();
