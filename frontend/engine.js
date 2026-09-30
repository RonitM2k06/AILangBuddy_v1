// Core engine: state/persistence, speech, pronunciation scoring, offline AI, spaced repetition.
(function () {
  const USER = "demo-alex";
  const KEY = "llb-state-v1";

  const DEMO = () => ({
    v: 1, name: "Alex", city: "delhi", language: "hi", level: "A1",
    confidence: { greetings: 90, transport: 100, food: 70, shopping: 50, directions: 80, college: 65, smalltalk: 40 },
    completedDays: [1, 2, 3], practiced: {}, xp: 340, streak: 4, lastActive: new Date().toDateString(),
    skills: { speaking: 70, listening: 80, vocabulary: 60, pronunciation: 72 },
    srs: {}, placement: null, tutor: [], roleplays: 0, achievements: ["first-words", "auto-pro", "foodie"],
  });

  let state = load();
  function load() {
    try { const s = JSON.parse(localStorage.getItem(KEY)); if (s && s.v === 1) return { ...DEMO(), ...s }; } catch (e) {}
    return DEMO();
  }
  let syncTimer;
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => fetch(`/api/state/${USER}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state) }).catch(() => {}), 400);
  }
  async function hydrate() {
    let hasLocal = false;
    try { hasLocal = !!localStorage.getItem(KEY); } catch (e) {}
    if (hasLocal) return save();
    try {
      const r = await fetch(`/api/state/${USER}`); const j = await r.json();
      if (j.state && j.state.v === 1) { state = { ...DEMO(), ...j.state }; save(); }
    } catch (e) {}
  }
  function reset() { state = DEMO(); save(); }

  const clamp = (n) => Math.max(0, Math.min(100, Math.round(n)));
  function bump(cat, amt) {
    if (!(cat in state.confidence)) return 0;
    const before = state.confidence[cat];
    state.confidence[cat] = clamp(before + amt);
    state.xp += Math.max(5, Math.round(amt * 5));
    save();
    return state.confidence[cat] - before;
  }
  function overall() {
    let t = 0, w = 0;
    for (const c of CATEGORIES) { t += state.confidence[c.key] * c.weight; w += c.weight; }
    return Math.round(t / w);
  }
  function readiness(p) {
    if (p >= 85) return "LIVING LIKE A LOCAL";
    if (p >= 70) return "READY TO EXPLORE " + cityName().toUpperCase();
    if (p >= 50) return "FINDING YOUR FEET";
    return "JUST ARRIVED";
  }
  const cityName = () => (CITIES.find((c) => c.id === state.city) || CITIES[0]).name;
  function sortedCats() { return CATEGORIES.map((c) => ({ ...c, v: state.confidence[c.key] })).sort((a, b) => b.v - a.v); }
  function insight() {
    const s = sortedCats(); const top = s.filter((c) => c.v >= 80).slice(0, 2); const low = s[s.length - 1];
    const names = (arr) => arr.map((c) => c.label.toLowerCase()).join(" and ");
    const strong = top.length ? `You're comfortable with ${names(top)}.` : `You're building a solid base across situations.`;
    const tips = { smalltalk: "feel more natural in everyday conversations", shopping: "get fair prices at markets", food: "order exactly what you want", greetings: "make great first impressions", directions: "never feel lost", college: "settle in on campus", transport: "move around freely" };
    return { text: `${strong} A little more practice with ${low.label.toLowerCase()} will help you ${tips[low.key]}.`, low };
  }

  // ---------- Speech ----------
  let voices = [];
  function loadVoices() { try { voices = speechSynthesis.getVoices(); } catch (e) {} }
  if ("speechSynthesis" in window) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
  let currentUtterance = null; // keep a reference: Chrome garbage-collects utterances mid-speech otherwise
  function speak(phrase, opts = {}) {
    if (!("speechSynthesis" in window)) return false;
    if (!voices.length) loadVoices();
    const hiVoice = voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith("hi"));
    const hasDeva = (t) => /[\u0900-\u097F]/.test(t || "");
    let text = typeof phrase === "string" ? phrase : (hiVoice && phrase.hi) || phrase.roman || phrase.hi;
    if (!hiVoice && hasDeva(text) && phrase.roman) text = phrase.roman; // non-Hindi voices can't read Devanagari
    const u = new SpeechSynthesisUtterance(text);
    const inVoice = hiVoice || voices.find((v) => v.lang === "en-IN" || v.lang === "en_IN");
    if (inVoice) { u.voice = inVoice; u.lang = inVoice.lang.replace("_", "-"); } else u.lang = "en-US";
    u.rate = opts.slow ? 0.7 : 0.92;
    u.onstart = () => opts.onstart && opts.onstart();
    u.onend = () => opts.onend && opts.onend();
    u.onerror = (e) => { if (e.error !== "interrupted" && e.error !== "canceled" && opts.onerror) opts.onerror(e.error); if (opts.onend) opts.onend(); };
    currentUtterance = u;
    try { speechSynthesis.cancel(); speechSynthesis.resume(); } catch (e) {}
    // Chrome drops speak() calls made in the same tick as cancel(); defer slightly.
    setTimeout(() => { try { speechSynthesis.speak(u); } catch (e) { opts.onerror && opts.onerror("failed"); } }, 60);
    return true;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let activeRec = null;
  function listen(lang = "hi-IN") {
    Engine.micError = null;
    return new Promise((resolve) => {
      if (!SR) { Engine.micError = "unsupported"; return resolve(null); }
      try { if (activeRec) activeRec.abort(); } catch (e) {}
      try {
        const r = new SR(); activeRec = r; r.lang = lang; r.interimResults = false; r.maxAlternatives = 3;
        let done = false; const finish = (v) => { if (!done) { done = true; activeRec = null; resolve(v); } };
        r.onresult = (e) => finish(Array.from(e.results[0]).map((a) => a.transcript).join(" | "));
        r.onerror = (e) => { Engine.micError = e.error; finish(null); }; r.onend = () => finish(null);
        r.start(); setTimeout(() => { try { r.stop(); } catch (e) {} }, 7000); setTimeout(() => finish(null), 8500);
      } catch (e) { resolve(null); }
    });
  }

  // ---------- Pronunciation scoring ----------
  const norm = (s) => (s || "").toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  function lev(a, b) {
    const m = a.length, n = b.length; if (!m) return n; if (!n) return m;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[n];
  }
  const sim = (a, b) => 1 - lev(a, b) / Math.max(a.length, b.length, 1);
  function hash(s) { let h = 7; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; }
  function score(phrase, transcript) {
    const romanWords = norm(phrase.roman).split(" ");
    if (!transcript) {
      // No speech recognition available: deterministic estimate so the flow still demos.
      const h = hash(phrase.roman + Date.now().toString().slice(0, -4));
      const bad = romanWords.filter((w, i) => w.length > 3 && (h >> i) % 4 === 0).slice(0, 2);
      const good = romanWords.filter((w) => !bad.includes(w));
      return { pct: clamp(95 - bad.length * 7 - (h % 8)), good, bad, estimated: true };
    }
    const alts = transcript.split(" | ").map(norm);
    let best = null;
    for (const alt of alts) {
      const deva = /[ऀ-ॿ]/.test(alt);
      const target = norm(deva ? phrase.hi : phrase.roman).split(" ");
      const said = alt.split(" ");
      const per = target.map((w) => Math.max(0, ...said.map((s) => sim(w, s))));
      const pct = clamp((per.reduce((a, b) => a + b, 0) / per.length) * 100);
      const labels = romanWords.length === target.length ? romanWords : target;
      const res = { pct, good: labels.filter((_, i) => per[i] >= 0.7), bad: labels.filter((_, i) => per[i] < 0.7), heard: alt };
      if (!best || res.pct > best.pct) best = res;
    }
    best.pct = Math.max(best.pct, 35);
    return best;
  }

  // ---------- Offline roleplay engine ----------
  const EN_WORDS = /\b(the|want|go|please|how|what|where|is|are|can|you|i|to|my|much|stop|thanks|thank|yes|okay|need|would|like)\b/gi;
  const HI_WORDS = /\b(hai|hain|kya|kahan|mera|aap|bhaiya|jaana|chaloge|theek|kitne|paise|nahi|haan|dijiye|kijiye|hoon|main|se|ka|ki|ke|na|ji|shukriya|dhanyavaad|accha|achha|chaliye|mein)\b/gi;
  function looksEnglish(t) { return (t.match(EN_WORDS) || []).length >= 2 && (t.match(HI_WORDS) || []).length === 0; }
  const PLACES = ["Connaught Place", "Airport", "Rajiv Chowk", "India Gate", "Hauz Khas", "Chandni Chowk", "Karol Bagh", "Railway Station", "North Campus"];
  const PRAISE = ["Nice — that sounded natural! 👌", "Great word choice.", "Perfect, very local!", "Well said — clear and polite."];

  function roleplayReply(sid, text, used) {
    const sc = SCENARIOS[sid]; const t = " " + text.toLowerCase() + " ";
    const matches = sc.rules.map((r, i) => ({ r, i })).filter(({ r }) => r.m.some((k) => t.includes(k)));
    const pick = matches.find(({ i }) => !used.includes(i)) || matches[0];
    let out, tip = "";
    if (pick) {
      used.push(pick.i);
      const place = PLACES.find((p) => t.includes(p.toLowerCase().split(" ")[0])) || "Connaught Place";
      out = { text: pick.r.text.replace("{place}", place), en: pick.r.en.replace("{place}", place), s: pick.r.s, end: pick.r.end };
      if (looksEnglish(text) && pick.r.hint) tip = `💡 Say it like a local: “${pick.r.hint.replace("{place}", place)}”`;
      else if (!looksEnglish(text)) tip = PRAISE[hash(text) % PRAISE.length];
    } else {
      out = { ...sc.fallback };
      tip = looksEnglish(text) ? `💡 Try one of the suggested Hinglish replies below — ${sc.partner} will follow along.` : "";
    }
    return { ...out, tip, matched: !!pick };
  }

  // ---------- Offline tutor engine ----------
  function titleCase(s) { return s.replace(/\b\w/g, (c) => c.toUpperCase()); }
  function tutorReply(text, history) {
    const t = text.toLowerCase();
    const mean = t.match(/(?:what does|meaning of|what is|what's)\s+["“']?([a-z ]+?)["”']?\s*(?:mean|\?|$)/);
    if (mean) {
      const w = mean[1].trim(); const g = GLOSSARY[w] || GLOSSARY[w.split(" ").pop()];
      if (g) return { intro: `“${titleCase(w)}” — ${g}`, phrases: [], topic: "greetings" };
    }
    if (/polite|formal|another|more|again|different/.test(t) && history.length) {
      const last = [...history].reverse().find((m) => m.role === "ai" && m.phrases && m.phrases.length);
      if (last) return { intro: "To sound more polite, use “-iye” verb endings and add “ji”:", topic: last.topic, phrases: last.phrases.slice(0, 2).map((p) => ({ ...p, roman: politer(p.roman), hi: p.hi, en: "Polite: " + p.en.replace(/^.*?: /, ""), label: "Polite" })), note: "e.g. “dena” → “dijiye”, “chaloge” → “chalenge”, “bhaiya” → “bhaiya ji”." };
    }
    for (const it of TUTOR_INTENTS) {
      if (it.m.some((k) => t.includes(k))) {
        if (it.build) {
          const dm = t.match(/(?:to|till|for|reach)\s+(?:the\s+)?([a-z][a-z ]{1,28}?)(?:[.?!,]|$|\s+from|\s+please|\s+by)/);
          let dest = dm ? titleCase(dm[1].trim()) : (PLACES.find((p) => t.includes(p.toLowerCase())) || "Connaught Place");
          if (/^(ask|go|get|an?|auto|driver|take)\b/i.test(dest)) dest = PLACES.find((p) => t.includes(p.toLowerCase())) || "Connaught Place";
          return { ...it.build(dest), topic: it.topic };
        }
        return { intro: it.intro, phrases: it.phrases, note: it.note, topic: it.topic };
      }
    }
    return { generic: true, intro: "Here are three phrases that'll get you through almost anything in your first week:", topic: "greetings", phrases: [
      { roman: "Namaste, aap kaise hain?", hi: "नमस्ते, आप कैसे हैं?", en: "Hello, how are you?" },
      { roman: "Kitne paise honge?", hi: "कितने पैसे होंगे?", en: "How much will it cost?" },
      { roman: "Kya aap meri madad kar sakte hain?", hi: "क्या आप मेरी मदद कर सकते हैं?", en: "Could you help me?" },
    ], note: "Tell me a situation — like “I want to order food” or “ask for directions to India Gate” — and I'll give you the exact words." };
  }
  function politer(r) {
    return r.replace(/chaloge/i, "chalenge").replace(/\bdena\b/i, "dijiye").replace(/Bhaiya,/i, "Bhaiya ji,").replace(/\bdo\b/i, "dijiye");
  }

  // ---------- LLM (optional, via backend) ----------
  let aiProvider = null;
  fetch("/api/health").then((r) => r.json()).then((j) => { aiProvider = j.ai; }).catch(() => {});
  async function askAI(payload) {
    if (!aiProvider) return null;
    try {
      const ctrl = new AbortController(); const to = setTimeout(() => ctrl.abort(), 12000);
      const r = await fetch("/api/ai", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ city: cityName(), language: "Hindi (Hinglish)", level: state.level, ...payload }), signal: ctrl.signal });
      clearTimeout(to); const j = await r.json(); return j.ok && j.reply ? j : null;
    } catch (e) { return null; }
  }

  // ---------- Spaced repetition (SM-2 lite) ----------
  function allCards() {
    return (PACKS[state.city] || PACKS.delhi).flatMap((d) => d.phrases.map((p, i) => ({ id: `d${d.day}-${i}`, ...p, category: d.title, key: d.key })));
  }
  function dueCards() {
    const now = Date.now();
    return allCards().filter((c) => !state.srs[c.id] || state.srs[c.id].due <= now)
      .sort((a, b) => ((state.srs[a.id] || {}).due || 0) - ((state.srs[b.id] || {}).due || 0));
  }
  function review(id, knew) {
    const c = state.srs[id] || { ease: 2.5, interval: 0, reps: 0, due: 0 };
    if (knew) { c.reps++; c.interval = c.reps === 1 ? 1 : c.reps === 2 ? 3 : Math.round(c.interval * c.ease); c.ease = Math.min(3, c.ease + 0.1); c.due = Date.now() + c.interval * 864e5; }
    else { c.reps = 0; c.interval = 0; c.ease = Math.max(1.3, c.ease - 0.2); c.due = Date.now() + 60e3; }
    state.srs[id] = c;
    state.skills.vocabulary = clamp(state.skills.vocabulary + (knew ? 1 : 0));
    state.xp += knew ? 10 : 3; save();
  }

  window.Engine = {
    get state() { return state; }, save, hydrate, reset, bump, overall, readiness, insight, sortedCats, cityName,
    speak, listen, canListen: !!SR, canSpeak: "speechSynthesis" in window, score,
    roleplayReply, tutorReply, askAI, get aiProvider() { return aiProvider; }, looksEnglish, allCards, dueCards, review, clamp,
  };
})();
