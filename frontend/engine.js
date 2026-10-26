// Core engine: state/persistence, speech, pronunciation scoring, offline AI, spaced repetition.
(function () {
  // Whose state this is. Anonymous visitors keep theirs in this browser only; a signed-in user's is synced to their OWN server-side state
  // (/api/state/<their handle>). There is no shared account: each identity has its own localStorage key, so nothing leaks between them.
  const KEY = "llb-state-v1";
  let who = null;                                        // the signed-in user's handle, or null when anonymous
  const keyFor = (handle) => (handle ? `${KEY}:${handle}` : KEY);
  const AI_HISTORY = 12, AI_TEXT = 500;                  // what /api/ai accepts (backend/settings.py LEGACY_AI_*)
  const WRITE_HEADERS = { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" };   // required on every write (backend/security/csrf.py)

  const DEMO = () => ({
    v: 1, name: "Alex", city: "delhi", language: "hi", level: "A1",
    confidence: { greetings: 90, transport: 100, food: 70, shopping: 50, directions: 80, college: 65, smalltalk: 40 },
    completedDays: [1, 2, 3], practiced: {}, xp: 340, streak: 4, lastActive: new Date().toDateString(),
    skills: { speaking: 70, listening: 80, vocabulary: 60, pronunciation: 72 },
    srs: {}, placement: null, tutor: [], roleplays: 0, achievements: ["first-words", "auto-pro", "foodie"],
  });

  // A signed-in account starts from its OWN empty progress and name (Phase 15A); the "Alex" demo is only for visitors who are not signed in.
  const FRESH = (name) => ({
    ...DEMO(), name: name || "there", confidence: { greetings: 0, transport: 0, food: 0, shopping: 0, directions: 0, college: 0, smalltalk: 0 },
    completedDays: [], xp: 0, streak: 0, skills: { speaking: 0, listening: 0, vocabulary: 0, pronunciation: 0 }, achievements: [],
  });
  let account = null;                                    // { name } of the signed-in user, or null
  let ready = false;                                     // true once the first check of who is signed in has finished
  const base = () => (who ? FRESH(account && account.name) : DEMO());
  let state = load(null);
  function load(handle) {
    const start = handle ? FRESH(account && account.name) : DEMO();
    try { const s = JSON.parse(localStorage.getItem(keyFor(handle))); if (s && s.v === 1) return { ...start, ...s }; } catch (e) {}
    return start;
  }
  function keep() { try { localStorage.setItem(keyFor(who), JSON.stringify(state)); } catch (e) {} }
  let syncTimer;
  function save() {
    state.language = language();                         // only a language this city offers is kept (the server refuses any other)
    keep();
    clearTimeout(syncTimer);
    if (!who) return;                                    // anonymous: this browser only, never the server
    const target = who, body = JSON.stringify(state);   // captured now, so a later sign-in or sign-out cannot redirect it
    syncTimer = setTimeout(() => fetch(`/api/state/${encodeURIComponent(target)}`, { method: "PUT", headers: WRITE_HEADERS, body }).catch(() => {}), 400);
  }
  // Works out who is signed in and loads that identity's state. Called at start-up and again after signing in or out.
  async function hydrate() {
    let handle = null, user = null;
    try { const r = await fetch("/api/auth/me"); if (r.ok) { user = (await r.json()).user; handle = user.handle || null; } } catch (e) {}
    account = handle ? { name: user.display_name } : null;
    ready = true;
    clearTimeout(syncTimer);
    who = handle; state = load(handle);
    if (!handle) return;
    let hasLocal = false;
    try { hasLocal = !!localStorage.getItem(keyFor(handle)); } catch (e) {}
    try {
      const r = await fetch(`/api/state/${encodeURIComponent(handle)}`); const j = r.ok ? await r.json() : null;
      if (j && j.state && j.state.v === 1) { state = { ...base(), ...j.state }; keep(); return; }   // the server copy wins: it follows the account
    } catch (e) {}
    if (hasLocal) save();                                // nothing on the server yet: upload what this browser has for this account
  }
  function reset() { state = base(); save(); }

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
  // The language the learner is taught in: the one they chose if their city offers it, else the city's first. A saved combination the city
  // does not offer (a city switched after picking a language, an old or edited state) never brings one city's language into another.
  const language = () => { const c = CITIES.find((x) => x.id === state.city) || CITIES[0]; return c.langs.includes(state.language) ? state.language : c.langs[0]; };
  // The learner's First Week pack: their city's pack in that language (LANGUAGE_PACKS, e.g. Mumbai in Marathi), else the city's own.
  const pack = () => ((window.LANGUAGE_PACKS || {})[state.city] || {})[language()] || PACKS[state.city] || PACKS.delhi;
  // The language the pack's phrases are in: the learner's, or for the English and Hinglish views the city's own (Hindi in Delhi and Mumbai,
  // Kannada in Bengaluru, Tamil in Chennai, Bengali in Kolkata, Telugu in Hyderabad). Hindi keeps its old voice fallbacks and practice score; every other language needs a voice of its own and gets
  // only an honest word check (app.js).
  const packLanguage = () => {
    const l = language(); if (l !== "en" && l !== "hinglish") return l;
    const c = CITIES.find((x) => x.id === state.city) || CITIES[0];
    return c.langs.find((x) => x !== "en" && x !== "hinglish") || "hi";
  };
  const LOCALES = { hi: "hi-IN", mr: "mr-IN", kn: "kn-IN", ta: "ta-IN", fr: "fr-FR", bn: "bn-IN", te: "te-IN", ur: "ur-IN", ks: "ks-IN", doi: "doi-IN" };
  const AI_LANGUAGE = { mr: "Marathi", kn: "Kannada", ta: "Tamil", fr: "French", bn: "Bengali", te: "Telugu", ur: "Urdu", ks: "Kashmiri", doi: "Dogri" };                  // the language label /api/ai accepts; Hindi's is "Hindi (Hinglish)"
  const speechLang = () => LOCALES[packLanguage()] || "hi-IN";           // what the learner speaks into the mic
  // Each pack keeps its own progress. Its key: "" for Delhi's pack (the original one, so progress saved before keeps its meaning), the city for
  // a city's own pack ("mumbai", which the English view also uses) and city:language for a pack in another language ("mumbai:mr").
  const packKey = () => {
    const p = pack(); if (p === PACKS.delhi) return "";
    return ((window.LANGUAGE_PACKS || {})[state.city] || {})[language()] === p ? `${state.city}:${language()}` : state.city;
  };
  // The days completed in the learner's pack: Delhi's in completedDays as before, every other pack's in packDays[key]. Never shared, so
  // finishing a day in one pack does not mark it done in another. A stored value that is not a list counts as none.
  function daysDone() {
    const k = packKey();
    if (!k) { if (!Array.isArray(state.completedDays)) state.completedDays = []; return state.completedDays; }
    if (!state.packDays || typeof state.packDays !== "object" || Array.isArray(state.packDays)) state.packDays = {};
    if (!Array.isArray(state.packDays[k])) state.packDays[k] = [];
    return state.packDays[k];
  }
  // The review status of the learner's pack (content.js CONTENT_REVIEW; the English view shows the Hindi pack), or null where none is recorded.
  const reviewStatus = () => ((window.CONTENT_REVIEW || {})[state.city] || {})[packLanguage()] || null;
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
  // Which voice reads the learner's phrases: the pack language's own ("hi", "mr", "kn"), "en" (an Indian-English voice reading romanised
  // Hindi) or "none". Only Hindi has the English fallback; a Marathi or Kannada phrase without its own voice is not played (app.js A.say).
  function voiceKind() {
    if (!("speechSynthesis" in window)) return "none";
    if (!voices.length) loadVoices();
    const has = (code) => voices.some((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(code));
    const own = packLanguage();
    if (own !== "hi") return has(own) ? own : "none";                       // a Marathi or Kannada phrase is read by its own voice or not at all
    return has("hi") ? "hi" : voices.length ? "en" : "none";
  }
  const codeOf = (locale) => String(locale || "").split(/[-_]/)[0].toLowerCase();
  // Is there a voice that really speaks this language? Only then is text in it read aloud as that language. Hindi keeps its old fallbacks
  // (an Indian-English voice reading the romanised form); any other language without a voice of its own is not read at all, so a Hindi voice
  // is never passed off as Marathi. Voices load asynchronously: ask at the moment of playing, not when a page is drawn.
  function hasVoice(locale) {
    if (!("speechSynthesis" in window)) return false;
    if (!voices.length) loadVoices();
    const code = codeOf(locale);
    return code === "hi" ? voices.length > 0 : voices.some((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(code));
  }
  function speak(phrase, opts = {}) {
    if (!("speechSynthesis" in window)) return false;
    if (!voices.length) loadVoices();
    const voiceFor = (code) => voices.find((v) => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(code));
    // the phrase's language: the page's (a listening activity's locale) or the learner's; anything but Hindi needs a voice of its own
    const code = opts.locale ? codeOf(opts.locale) : packLanguage();
    if (code !== "hi" && !voiceFor(code)) return false;
    const hiVoice = code !== "hi" ? voiceFor(code) : voiceFor("hi");
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
  function listen(lang = speechLang()) {
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
  // Latin accents are ignored (French "café" and "cafe" are one word); other scripts' vowel signs are kept
  const noAccents = (s) => (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").normalize("NFC");
  const norm = (s) => noAccents(s).toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
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
      const native = /[^\p{Script=Latin}\P{L}]/u.test(alt);              // heard in a script of its own (Devanagari, Kannada), not Roman letters
      const target = norm(native ? phrase.hi : phrase.roman).split(" ");
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
  const MR_WORDS = /\b(aahe|aahet|aahat|kay|kuthe|kiti|mala|tumhi|tumhala|dada|kaka|ho|nako|chala|dya|sanga|zhale|ithe|khup|majet|kasa|bhetu)\b/gi;
  const KN_WORDS = /\b(namaskara|ide|ideya|ellide|eshtu|beku|beda|kodi|maadi|haaki|heli|hogi|swalpa|tumba|haudu|illa|sari|nanna|nimma|naanu|neevu|ille|sigona|aaytu|bartira|dhanyavaadagalu)\b/gi;
  const TA_WORDS = /\b(vanakkam|irukku|irukkaa|enga|evvalavu|venum|venaam|kudunga|podunga|sollunga|pannunga|konjam|romba|aamaa|illa|sari|en|unga|naan|neenga|inga|nandri|aachu|pogumaa)\b/gi;
  const BN_WORDS = /\b(nomoshkar|achhe|achhen|kothay|koto|holo|lagbe|din|deben|korun|bolun|thamun|jaben|hyan|thik|ektu|khub|beshi|kom|amar|apnar|ami|apni|tumi|dhonnobad|darun|aschhi)\b/gi;
  const TE_WORDS = /\b(namaskaram|entha|ekkada|undi|undaa|ivvandi|cheyandi|cheppandi|aapandi|veyandi|vastaaraa|avunu|ledu|sare|chaala|konchem|ekkuva|takkuva|dhanyavaadaalu|kaavaali|vaddu|nenu|meeru|naaku|malli|kaluddaam)\b/gi;
  const KS_WORDS = /\b(vaaray|chhivaa|chhu|chhe|chha|kotah|kati|diyiv|kariv|vaniv|rukiv|gatshiv|vaariyah|shukriya|myon|naav|tuhi|aa|zaroor|mulaqaat)\b/gi;
  const DOI_WORDS = /\b(kiyaan|ai|aan|kutthen|kitne|deo|karo|dasso|ghatt|dhannvaad|itthen|tus|naan|phi|milchai|chaah|laggan|chalge)\b/gi;
  const FR_WORDS = /\b(bonjour|merci|je|vous|tu|est|une?|le|la|les|pour|combien|s'il|plait|plaît|oui|non|c'est|velo|vélo|cafe|café|ou|où)\b/gi;
  function looksEnglish(t) { return (t.match(EN_WORDS) || []).length >= 2 && [HI_WORDS, MR_WORDS, KN_WORDS, TA_WORDS, BN_WORDS, TE_WORDS, KS_WORDS, DOI_WORDS, FR_WORDS].every((re) => (t.match(re) || []).length === 0); }
  const PLACES = ["Connaught Place", "Airport", "Rajiv Chowk", "India Gate", "Hauz Khas", "Chandni Chowk", "Karol Bagh", "Railway Station", "North Campus"];
  const PRAISE = ["Nice — that sounded natural! 👌", "Great word choice.", "Perfect, very local!", "Well said — clear and polite."];

  function roleplayReply(sid, text, used) {
    const sc = SCENARIOS[sid]; const t = " " + noAccents(text.toLowerCase()) + " ";   // a rule's words are written without accents
    const matches = sc.rules.map((r, i) => ({ r, i })).filter(({ r }) => r.m.some((k) => t.includes(k)));
    const pick = matches.find(({ i }) => !used.includes(i)) || matches[0];
    let out, tip = "";
    if (pick) {
      used.push(pick.i);
      const places = sc.places || PLACES;                  // a city's scenario may name its own places (Mumbai); Delhi's use the list above
      const place = places.find((p) => t.includes(p.toLowerCase().split(" ")[0])) || places[0];
      out = { text: pick.r.text.replace("{place}", place), en: pick.r.en.replace("{place}", place), s: pick.r.s, end: pick.r.end };
      if (looksEnglish(text) && pick.r.hint) tip = `💡 Say it like a local: “${pick.r.hint.replace("{place}", place)}”`;
      else if (!looksEnglish(text)) tip = PRAISE[hash(text) % PRAISE.length];
    } else {
      out = { ...sc.fallback };
      tip = looksEnglish(text) ? `💡 Try one of the suggested ${AI_LANGUAGE[packLanguage()] || "Hinglish"} replies below — ${sc.partner} will follow along.` : "";
    }
    return { ...out, tip, matched: !!pick };
  }

  // ---------- Offline tutor engine ----------
  function titleCase(s) { return s.replace(/\b\w/g, (c) => c.toUpperCase()); }
  // Content for the learner's city in their language (content.js LOCAL_CONTENT; the English view uses the Hindi entry), or {} for the shared one.
  const local = () => ((window.LOCAL_CONTENT || {})[state.city] || {})[packLanguage()] || {};
  const readings = () => local().readings || READINGS;
  const placement = () => local().placement || PLACEMENT;
  function tutorReply(text, history) {
    const t = text.toLowerCase(), tu = local().tutor || {};
    const glossary = tu.glossaryOnly ? tu.glossary : { ...GLOSSARY, ...(tu.glossary || {}) };
    const places = tu.places || PLACES, fallbackPlace = tu.defaultPlace || "Connaught Place";
    const mean = t.match(/(?:what does|meaning of|what is|what's)\s+["“']?([a-z ]+?)["”']?\s*(?:mean|\?|$)/);
    if (mean) {
      const w = mean[1].trim(); const g = glossary[w] || glossary[w.split(" ").pop()];
      if (g) return { intro: `“${titleCase(w)}” — ${g}`, phrases: [], topic: "greetings" };
    }
    if (/polite|formal|another|more|again|different/.test(t) && history.length) {
      const last = [...history].reverse().find((m) => m.role === "ai" && m.phrases && m.phrases.length);
      const pol = tu.polite;
      const soften = pol ? (r) => pol.rules.reduce((out, [re, to]) => out.replace(new RegExp(re, "i"), to), r) : politer;
      if (last) return { intro: pol ? pol.intro : "To sound more polite, use “-iye” verb endings and add “ji”:", topic: last.topic, phrases: last.phrases.slice(0, 2).map((p) => ({ ...p, roman: soften(p.roman), hi: p.hi, en: "Polite: " + p.en.replace(/^.*?: /, ""), label: "Polite" })), note: pol ? pol.note : "e.g. “dena” → “dijiye”, “chaloge” → “chalenge”, “bhaiya” → “bhaiya ji”." };
    }
    for (const it of tu.intents || TUTOR_INTENTS) {
      if (it.m.some((k) => t.includes(k))) {
        if (it.build) {
          const dm = t.match(/\b(?:to|till|for|reach)\s+(?:the\s+)?([a-z][a-z ]{1,28}?)(?:[.?!,]|$|\s+from|\s+please|\s+by)/);
          let dest = dm ? titleCase(dm[1].trim()) : (places.find((p) => t.includes(p.toLowerCase())) || fallbackPlace);
          if (/^(ask|go|get|an?|auto|driver|take)\b/i.test(dest)) dest = places.find((p) => t.includes(p.toLowerCase())) || fallbackPlace;
          return { ...it.build(dest), topic: it.topic };
        }
        return { intro: it.intro, phrases: it.phrases, note: it.note, topic: it.topic };
      }
    }
    if (tu.generic) return { generic: true, topic: "greetings", ...tu.generic };
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
  fetch("/api/health").then((r) => r.json()).then((j) => { aiProvider = j.ai === true; }).catch(() => {});   // a yes/no since Phase 14E
  // payload: { mode: "tutor" | "roleplay", scenario: <SCENARIOS id, roleplay only>, history: [{ role, text }] }. Only what /api/ai accepts is
  // sent: the scene by id (its text lives on the server), the last AI_HISTORY messages, each cut to AI_TEXT characters of our own text.
  async function askAI(payload) {
    if (!aiProvider) return null;
    // a Marathi or Kannada learner's roleplays and tutor are asked for in that language
    const body = { mode: payload.mode, city: cityName(), language: AI_LANGUAGE[packLanguage()] || "Hindi (Hinglish)", level: state.level,
      history: (payload.history || []).slice(-AI_HISTORY).map((m) => ({ role: m.role === "me" ? "me" : "ai", text: String(m.text || "").slice(0, AI_TEXT) })) };
    if (payload.mode === "roleplay") body.scenario = payload.scenario;
    try {
      const ctrl = new AbortController(); const to = setTimeout(() => ctrl.abort(), 12000);
      const r = await fetch("/api/ai", { method: "POST", headers: WRITE_HEADERS, body: JSON.stringify(body), signal: ctrl.signal });
      clearTimeout(to); const j = await r.json(); return j.ok && j.reply ? j : null;
    } catch (e) { return null; }
  }

  // ---------- Spaced repetition (SM-2 lite) ----------
  function allCards() {
    const k = packKey();                                 // a pack's own review history: Delhi's cards keep their ids (d1-0), others are prefixed
    return pack().flatMap((d) => d.phrases.map((p, i) => ({ id: `${k ? k + ":" : ""}d${d.day}-${i}`, ...p, category: d.title, key: d.key })));
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
    get state() { return state; }, get account() { return account; }, get ready() { return ready; }, save, hydrate, reset, bump, overall, readiness, insight, sortedCats, cityName, language, packLanguage, pack, packKey, daysDone, speechLang, reviewStatus, local, readings, placement,
    speak, voiceKind, hasVoice, listen, canListen: !!SR, canSpeak: "speechSynthesis" in window, score,
    roleplayReply, tutorReply, askAI, get aiProvider() { return aiProvider; }, looksEnglish, allCards, dueCards, review, clamp,
  };
})();
