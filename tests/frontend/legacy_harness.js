// Drives the real legacy prototype (frontend/content.js, engine.js, profile.js, app.js) in JavaScriptCore (osascript) against a live test
// server. The scripts run in the global scope, as in a browser; the DOM, localStorage and timers are stubs, HTTP is real (curl).
// Each scenario prints one line "## {json}" with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, EMAIL + PASSWORD (an account
// the test made), PAYLOAD (the markup an attacker would plant), FAKE_AI (1: /api/health reports a model and /api/ai is captured, not sent).
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO'), PAYLOAD = E('PAYLOAD');
var JAR = WORKDIR + '/cookies.txt';
var G = (function () { return this; })();

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function curl(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}

// ---- HTTP: real, through one cookie jar (one browser) ----
var sent = [], aiBodies = [];
function http(method, url, body, headers) {
  var args = ['-s', '-i', '-b', JAR, '-c', JAR, '-X', method];
  for (var k in (headers || {})) { args.push('-H'); args.push(k + ': ' + headers[k]); }
  if (body) { args.push('--data-binary'); args.push(body); }
  args.push(BASE + url);
  var raw = curl(args), split = raw.indexOf('\r\n\r\n');
  var head = raw.slice(0, split), text = raw.slice(split + 4);
  return { status: parseInt(/HTTP\/[\d.]+ (\d+)/.exec(head)[1], 10), text: text };
}
function response(status, text) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status: status, json: function () { return Promise.resolve(JSON.parse(text)); } });
}
G.fetch = function (url, opts) {
  opts = opts || {};
  var method = opts.method || 'GET';
  sent.push({ method: method, url: url, body: opts.body || null, headers: opts.headers || {} });
  if (E('FAKE_AI') === '1' && url === '/api/health') return response(200, '{"ok": true, "ai": true}');                  // public health is coarse since Phase 14E
  if (E('FAKE_AI') === '1' && url === '/api/ai') { aiBodies.push(JSON.parse(opts.body)); return response(200, '{"ok": false, "reason": "offline"}'); }
  var r = http(method, url, opts.body, opts.headers);
  return response(r.status, r.text);
};
function serverGet(url) { var r = http('GET', url); return { status: r.status, data: r.status === 200 ? JSON.parse(r.text) : null }; }
var WRITE = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };   // what the frontend sends on writes
function serverPost(url, obj) { return http('POST', url, JSON.stringify(obj), WRITE).status; }

// ---- timers: queued, run by settle() ----
var timers = [];
G.setTimeout = function (f) { timers.push(f); return timers.length; };
G.clearTimeout = function () {};
G.setInterval = function () { return 0; };
G.clearInterval = function () {};
G.requestAnimationFrame = function (f) { timers.push(f); return timers.length; };
async function settle() {
  for (var round = 0; round < 50; round++) {
    for (var i = 0; i < 100; i++) await null;
    if (!timers.length) break;
    var due = timers.splice(0, timers.length);
    for (var j = 0; j < due.length; j++) { try { due[j](); } catch (e) {} }
  }
}

// ---- storage ----
var store = {};
G.localStorage = { getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
                   setItem: function (k, v) { store[k] = String(v); }, removeItem: function (k) { delete store[k]; } };

// ---- DOM ----
function element(id) {
  var kids = {};
  return { id: id, innerHTML: '', textContent: '', value: '', style: {}, dataset: {}, scrollTop: 0, scrollHeight: 0, offsetWidth: 0,
           classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } },
           setAttribute: function () {}, getAttribute: function () { return null; }, appendChild: function () {}, remove: function () {},
           insertAdjacentHTML: function () {}, addEventListener: function () {}, closest: function () { return null; },
           querySelector: function (s) { return kids[s] || (kids[s] = element(s)); }, querySelectorAll: function () { return []; }, kids: kids };
}
var page = { app: element('app'), nav: element('nav'), 'bottom-nav': element('bottom-nav'), 'side-card': element('side-card'), toast: element('toast') };
var profileRoot = null;
var handlers = {};
G.document = {
  querySelector: function (s) { return s.charAt(0) === '#' ? (page[s.slice(1)] || null) : null; },
  querySelectorAll: function () { return []; },
  getElementById: function (id) { if (id === 'profile-root') return profileRoot; return page[id] || null; },
  createElement: function () { return element(''); }, createDocumentFragment: function () { return element(''); }, createTextNode: function () { return element(''); },
  addEventListener: function (t, f) { (handlers[t] = handlers[t] || []).push(f); },
  body: { insertAdjacentHTML: function () {}, appendChild: function () {}, contains: function () { return true; },
          classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } } },
};
G.location = { hash: '', replace: function (h) { G.location.hash = h; } };
G.window = G;
G.addEventListener = function (t, f) { (handlers[t] = handlers[t] || []).push(f); };
G.dispatchEvent = function (ev) { (handlers[ev.type] || []).forEach(function (f) { f(ev); }); };
G.Event = function (type) { this.type = type; };
G.scrollTo = function () {};
G.console = G.console || { log: function () {}, error: function () {} };
G.AbortController = function () { this.signal = {}; this.abort = function () {}; };
G.Bits = { enhance: function () {} };                        // bits.js is visual effects only (canvas, pointer tracking)
G.VoiceView = { page: function () { return ''; } };          // newer views the router names directly; not part of the legacy surface
G.PlanView = { page: function () { return ''; } };

function load(p) { (0, eval)(read(p)); }
load('frontend/content.js'); load('frontend/engine.js'); load('frontend/profile.js'); load('frontend/app.js');

// ---- helpers ----
function has(s, sub) { return s.indexOf(sub) >= 0; }
async function go(route) { G.location.hash = '#/' + route; G.dispatchEvent(new G.Event('hashchange')); await settle(); return page.app.innerHTML + page['side-card'].innerHTML; }
var ROUTES = ['', 'pack', 'lesson/1', 'roleplay/auto', 'tutor', 'learn', 'progress', 'confidence', 'speaking'];
async function renderAll() { var out = ''; for (var i = 0; i < ROUTES.length; i++) out += '\n' + (await go(ROUTES[i])); return out; }
function stateRequests() { return sent.filter(function (s) { return has(s.url, '/api/state'); }); }
// Phase 14B: every write the frontend makes carries the browser-request signal the server requires (backend/security/csrf.py)
function writesAreSignalled(list) { var w = list.filter(function (s) { return s.method !== 'GET'; });
  return w.length > 0 && w.every(function (s) { return s.headers['X-Requested-With'] === 'XMLHttpRequest' && s.headers['Content-Type'] === 'application/json'; }); }
async function signIn() { serverPost('/api/auth/login', { email: E('EMAIL'), password: E('PASSWORD') }); await G.Engine.hydrate(); await settle(); }
function handle() { return serverGet('/api/auth/me').data.user.handle; }
function onclicks(html) { var out = [], re = /onclick="([^"]*)"/g, m; while ((m = re.exec(html))) out.push(m[1]); return out; }

var scenarios = {
  async anonymous_is_local_only() {
    await settle();                                          // app.js has run E.hydrate() at start-up
    var html = await renderAll();
    var before = stateRequests().length;
    G.Engine.bump('food', 5); await settle();
    var saved = JSON.parse(store['llb-state-v1'] || 'null');
    return { never_asked_the_server_for_state: before === 0, never_wrote_state_to_the_server: stateRequests().length === 0,
             did_not_load_the_planted_demo_state: G.Engine.state.level === 'A1' && !has(html, PAYLOAD) && !has(html, '<img'),
             kept_the_change_in_this_browser: !!saved && saved.confidence.food === 75, only_the_anonymous_key: Object.keys(store).join(',') === 'llb-state-v1' };
  },
  async signed_in_uses_own_identity() {
    await settle();
    sent.length = 0;
    await signIn();
    var me = handle(), url = '/api/state/' + me;
    var reads = stateRequests().filter(function (s) { return s.method === 'GET'; }).map(function (s) { return s.url; });
    var food = G.Engine.state.confidence.food;                 // a new account starts from its own (empty) progress since Phase 15A, not the demo's
    G.Engine.bump('food', 5); await settle();
    var writes = stateRequests().filter(function (s) { return s.method === 'PUT'; }).map(function (s) { return s.url; });
    var server = serverGet(url).data.state;
    return { read_own_state: reads.length === 1 && reads[0] === url, wrote_own_state: writes.length >= 1 && writes.every(function (u) { return u === url; }),
             state_writes_are_signalled: writesAreSignalled(stateRequests()),
             no_shared_identity_anywhere: sent.every(function (s) { return !has(s.url, 'demo-alex'); }), the_server_has_the_change: !!server && server.confidence.food === food + 5,
             kept_per_account_in_this_browser: !!store['llb-state-v1:' + me] && !store['llb-state-v1'] };
  },
  async malicious_state_renders_as_text() {
    await settle();
    await signIn();                                          // this account's stored state was planted by the test (as a pre-14A row could be)
    var loaded = G.Engine.state.level === PAYLOAD;
    var s = G.Engine.state, roman = G.PACKS.delhi[0].phrases[0].roman;
    s.streak = '<b id=pwn>4</b>'; s.xp = PAYLOAD; s.confidence.food = PAYLOAD; s.confidence.greetings = '50" onmouseover="alert(1)';
    s.skills.pronunciation = PAYLOAD; s.skills.speaking = '1;background:url(//evil)'; s.practiced[roman] = PAYLOAD; s.completedDays = { length: PAYLOAD, includes: function () { return false; } };
    var html = await renderAll();
    var tutor = await go('tutor');
    var handlersOk = onclicks(tutor).every(function (h) { return /^A\.[A-Za-z]+\([^"<>]*\)$/.test(h) && !has(h, 'alert'); });
    var practice = onclicks(tutor).filter(function (h) { return has(h, 'A.practice('); });
    return { the_planted_state_was_loaded: loaded, no_markup_from_state: !has(html, '<img') && !has(html, '<b id=pwn>') && !has(html, 'onmouseover="alert'),
             level_shown_as_text: has(html, '&lt;img src=x onerror=alert(1)&gt;'), numbers_stay_numbers: !has(html, 'url(//evil)') && has(html, '0%'),
             tutor_handlers_are_clean: handlersOk && practice.length >= 1 && practice.every(function (h) { return /, 'smalltalk'\)$/.test(h); }),
             planted_topic_never_in_markup: !has(tutor, "alert(1);//") && !has(tutor, 'onerror=alert(2)') };
  },
  async the_account_copy_wins_over_this_browsers() {
    await settle();
    serverPost('/api/auth/login', { email: E('EMAIL'), password: E('PASSWORD') });
    var me = handle(), local = JSON.parse(JSON.stringify(G.Engine.state));
    local.confidence.food = 88; store['llb-state-v1:' + me] = JSON.stringify(local);   // an older copy this browser kept for the account
    sent.length = 0;
    await G.Engine.hydrate(); await settle();
    var server = serverGet('/api/state/' + me).data.state;
    return { the_server_copy_is_shown: G.Engine.state.confidence.food === 33, the_server_copy_is_not_overwritten: !!server && server.confidence.food === 33,
             nothing_was_uploaded: stateRequests().every(function (s) { return s.method === 'GET'; }),
             this_browser_now_matches_the_account: JSON.parse(store['llb-state-v1:' + me]).confidence.food === 33 };
  },
  async legacy_ui_still_works() {
    await settle();
    var marks = { '': 'class="hero"', pack: 'Your First Week in Delhi', 'lesson/1': 'Day 1', 'roleplay/auto': 'Raju bhaiya', tutor: 'Namaste Test User', learn: 'Build your foundations',
                  progress: 'Your journey so far', confidence: 'Your Local Confidence', speaking: 'Say it like a local' };
    var out = {}, gated = true;
    for (var r in marks) { var html = await go(r); gated = gated && has(html, 'id="gate-root"') && !has(html, marks[r]); }   // Phase 15A: nothing before signing in
    out.signed_out_visitors_only_get_the_sign_in_screen = gated;
    await signIn();
    for (var r2 in marks) out['page_' + (r2 || 'home').replace('/', '_')] = has(await go(r2), marks[r2]);
    var side = page['side-card'].innerHTML;
    out.side_card_shows_the_accounts_own_level_and_streak = has(side, '>A1<') && has(side, '0-day streak');   // its own progress, not the demo's 4 days
    return out;
  },
  async ai_requests_carry_only_the_allowed_fields() {
    await settle();
    var long = new Array(800).join('x'), history = [];
    for (var i = 0; i < 20; i++) history.push({ role: i % 2 ? 'ai' : 'me', text: i === 19 ? long : 'm' + i, en: 'extra', tip: 'extra', fresh: true });
    await G.Engine.askAI({ mode: 'roleplay', scenario: 'auto', history: history });
    await G.Engine.askAI({ mode: 'tutor', history: [{ role: 'me', text: 'hi' }] });
    var rp = aiBodies[0], tu = aiBodies[1], aiSignalled = writesAreSignalled(sent.filter(function (s) { return s.url === '/api/ai'; }));
    var real = http('POST', '/api/ai', JSON.stringify(rp), WRITE);
    var realTutor = http('POST', '/api/ai', JSON.stringify(tu), WRITE);
    return { roleplay_fields: Object.keys(rp).sort().join(',') === 'city,history,language,level,mode,scenario', scene_by_id: rp.scenario === 'auto',
             history_bounded: rp.history.length === 12 && rp.history.every(function (m) { return Object.keys(m).sort().join(',') === 'role,text' && m.text.length <= 500; }),
             latest_messages_kept: rp.history[11].text.length === 500 && rp.history[0].text === 'm8',
             tutor_has_no_scene: !('scenario' in tu) && tu.mode === 'tutor', ai_requests_are_signalled: aiSignalled,
             the_server_accepts_them: real.status === 200 && realTutor.status === 200 && JSON.parse(real.text).reason === 'offline' };
  },
  async mumbai_pack_works() {
    await settle();
    await signIn();
    G.Engine.state.city = 'mumbai'; G.Engine.save(); await settle();
    var pack = await go('pack'), lessons = [];
    for (var d = 1; d <= 7; d++) lessons.push(await go('lesson/' + d));
    var rp = await go('roleplay/mum_taxi');
    var trip = G.Engine.roleplayReply('mum_taxi', 'Bhaiya, Churchgate chaloge?', []);
    var meter = G.Engine.roleplayReply('mum_taxi', 'Bhaiya, meter se chaloge?', []);
    var home = await go(''), conf = await go('confidence');
    var delhiPlaces = /Connaught|Sarojini|Kamla Nagar|Laxmi Nagar|Delhi University|Kashmere/;
    var mumbai = {
      first_week_is_mumbai: has(pack, 'Your First Week in Mumbai') && has(pack, 'Take the local train') && has(pack, 'Bargain politely'),
      every_day_renders: lessons.every(function (html, i) { return has(html, 'Day ' + (i + 1)); }) && has(lessons[2], 'वड़ा पाव') && has(lessons[1], 'Churchgate'),
      no_delhi_places_in_the_pack: ![pack].concat(lessons).some(function (html) { return delhiPlaces.test(html); }),
      transport_prices_are_mumbai: has(lessons[1], 'Mumbai · approx.') && has(lessons[1], 'Kaali-peeli taxi'),
      food_price_picks_vada_pav: /value="vadapav" selected/.test(lessons[2]),
      roleplay_is_mumbai: has(rp, 'Sharma ji') && has(rp, 'kidhar jaana hai') && !delhiPlaces.test(rp),
      offline_replies_use_mumbai_places: has(trip.text, 'Churchgate') && !has(trip.text, 'Connaught'),
      offline_replies_follow_the_meter: has(meter.text, 'meter se hi chalega'),
      home_counts_this_citys_locals: /data-count="7">0<\/b><span>AI locals/.test(home) && has(home, 'Right now in Mumbai'),
      practice_links_go_to_mumbai_roleplays: /href="#\/roleplay\/mum_/.test(conf) && !/href="#\/roleplay\/(auto|food|shopping|directions|college|smalltalk|greetings)"/.test(conf),
    };
    G.Engine.state.city = 'delhi'; G.Engine.save(); await settle();
    var delhi = await go('pack'), delhiRide = G.Engine.roleplayReply('auto', 'Connaught Place jaana hai.', []);
    var delhiRp = await go('roleplay/auto');
    mumbai.delhi_is_unchanged = has(delhi, 'Your First Week in Delhi') && has(delhiRide.text, 'Connaught Place') && has(delhiRp, 'Raju bhaiya') && !has(delhiRp, 'roleplay/mum_');
    mumbai.mumbai_side_panel_lists_only_mumbai = has(rp, 'href="#/roleplay/mum_food"') && !/href="#\/roleplay\/(auto|food|shopping)"/.test(rp);
    return mumbai;
  },
  async mumbai_in_marathi_works() {
    await settle();
    await signIn();
    G.Engine.state.city = 'mumbai'; G.Engine.state.language = 'mr'; G.Engine.save(); await settle();
    var pack = await go('pack'), lessons = [];
    for (var d = 1; d <= 7; d++) lessons.push(await go('lesson/' + d));
    var rp = await go('roleplay/mum_mr_taxi');
    var trip = G.Engine.roleplayReply('mum_mr_taxi', 'Dada, Churchgatela yenar ka?', []);
    var home = await go(''), conf = await go('confidence'), tutor = await go('tutor');
    await G.Engine.askAI({ mode: 'roleplay', scenario: 'mum_mr_taxi', history: [{ role: 'me', text: 'Namaskar' }] });
    await G.Engine.askAI({ mode: 'tutor', history: [{ role: 'me', text: 'hi' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[0]), WRITE);
    var hindiPhrases = /मीटर से चलोगे|कितना हुआ|स्टेशन किधर है|आख़िरी दाम/;
    var out = {
      first_week_is_mumbai: has(pack, 'Your First Week in Mumbai'),
      every_day_renders_in_marathi: lessons.every(function (html, i) { return has(html, 'Day ' + (i + 1)); }) && has(lessons[0], 'नमस्कार, कसे आहात?') &&
        has(lessons[1], 'मीटरने येणार का?') && has(lessons[4], 'स्टेशन कुठे आहे?') && has(lessons[6], 'चल, भेटू नंतर!'),
      no_hindi_pack_phrases: ![pack].concat(lessons).some(function (html) { return hindiPhrases.test(html); }),
      mumbai_prices: has(lessons[1], 'Mumbai · approx.') && has(lessons[1], 'Kaali-peeli taxi'),
      roleplay_is_marathi: has(rp, 'Shinde kaka') && has(rp, 'kuthe jaaycha aahe') && has(rp, 'Type in Marathi'),
      side_panel_lists_only_marathi_roleplays: has(rp, 'href="#/roleplay/mum_mr_food"') && !/href="#\/roleplay\/(mum_food|food|auto)"/.test(rp),
      offline_replies_use_mumbai_places: has(trip.text, 'Churchgate') && has(trip.text, 'Meterne'),
      home_links_to_marathi_roleplays: has(home, 'Right now in Mumbai') && /href="#\/roleplay\/mum_mr_/.test(home) && /data-count="7">0<\/b><span>AI locals/.test(home),
      practice_links_go_to_marathi_roleplays: /href="#\/roleplay\/mum_mr_/.test(conf) && !/href="#\/roleplay\/mum_(?!mr_)/.test(conf),
      tutor_is_marathi: has(tutor, 'Namaskar') && has(tutor, 'exact Marathi words') && has(tutor, 'What does &#39;bara&#39; mean?'),
      offline_tutor_answers_in_marathi: has(G.Engine.tutorReply('I need a taxi to Dadar', []).phrases[0].roman, 'Dadarla yenar ka') &&
        G.Engine.tutorReply('How do I order food?', []).phrases[0].hi === 'एक वडापाव द्या.' && has(G.Engine.tutorReply("What does 'bara' mean?", []).intro, 'Okay') &&
        G.Engine.tutorReply('blah', []).phrases[0].roman === 'Namaskar, kase aahat?' && !G.Engine.tutorReply("What does 'kitne' mean?", []).intro.includes('How many'),
      speech_is_marathi: G.Engine.speechLang() === 'mr-IN' && G.Engine.allCards()[0].hi === 'नमस्कार, कसे आहात?' && G.Engine.allCards().length === 35,
      ai_roleplay_and_tutor_ask_for_marathi: aiBodies[0].language === 'Marathi' && aiBodies[0].scenario === 'mum_mr_taxi' && aiBodies[1].language === 'Marathi',
      the_server_accepts_it: real.status === 200 && JSON.parse(real.text).reason === 'offline',
    };
    G.Engine.state.language = 'hi'; G.Engine.save(); await settle();
    var hindi = await go('lesson/2'), hindiTutor = await go('tutor');
    out.hindi_is_unchanged = has(hindi, 'मीटर से चलोगे?') && !has(hindi, 'मीटरने') && G.Engine.speechLang() === 'hi-IN' && !has(hindiTutor, 'exact Marathi words') &&
      has(G.Engine.tutorReply('I need a taxi to Dadar', []).phrases[0].roman, 'Bhaiya, Dadar chaloge');
    return out;
  },
  async bengaluru_in_kannada_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    E.state.city = 'bengaluru'; E.state.language = 'kn'; E.save(); await settle();
    var pack = await go('pack'), lessons = [];
    for (var d = 1; d <= 7; d++) lessons.push(await go('lesson/' + d));
    var rp = await go('roleplay/blr_auto');
    var trip = E.roleplayReply('blr_auto', 'Indiranagarakke bartira?', []), meter = E.roleplayReply('blr_auto', 'Meter haaki.', []);
    var english = E.roleplayReply('blr_auto', 'I want to go please', []);
    var home = await go(''), conf = await go('confidence'), tutor = await go('tutor');
    await E.askAI({ mode: 'roleplay', scenario: 'blr_auto', history: [{ role: 'me', text: 'Namaskara' }] });
    await E.askAI({ mode: 'tutor', history: [{ role: 'me', text: 'hi' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[0]), WRITE);
    var devanagari = /[ऀ-ॿ]/, delhiOrMumbai = /Connaught|Sarojini|Churchgate|Dadar|Colaba|vada pav|Kaali-peeli/;
    var out = {
      first_week_is_bengaluru: has(pack, 'Your First Week in Bengaluru') && has(pack, 'AI-assisted editorial review only, not yet checked by a native Kannada speaker'),
      every_day_renders_in_kannada: lessons.every(function (html, i) { return has(html, 'Day ' + (i + 1)); }) && has(lessons[0], 'ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?') &&
        has(lessons[0], 'ನಾನು ಇಲ್ಲಿ ಹೊಸಬಳು.') && has(lessons[1], 'ಮೀಟರ್ ಹಾಕಿ.') && has(lessons[6], 'ಸಖತ್! ಮತ್ತೆ ಸಿಗೋಣ.'),
      no_devanagari_and_no_other_city: ![pack].concat(lessons).some(function (html) { return devanagari.test(html.replace(/कृपया पढ़िए/g, '')) || delhiOrMumbai.test(html); }),
      bengaluru_prices: has(lessons[1], 'Bengaluru · approx.') && has(lessons[1], 'Namma Metro ticket') && /value="dosa" selected/.test(lessons[2]) && /value="kurta" selected/.test(lessons[3]),
      roleplay_is_kannada: has(rp, 'Manju') && has(rp, 'Ellige hogbeku?') && has(rp, 'Type in Kannada'),
      side_panel_lists_only_bengaluru_roleplays: has(rp, 'href="#/roleplay/blr_food"') && !/href="#\/roleplay\/(mum_|food|auto)/.test(rp),
      offline_replies_follow_the_conversation: trip.text === 'Indiranagar? Sari, kootkolli.' && has(meter.text, 'twenty rupees mele'),
      an_english_reply_is_coached_in_kannada: english.matched === false && has(english.tip, 'suggested Kannada replies'),
      home_links_to_bengaluru_roleplays: has(home, 'Right now in Bengaluru') && /href="#\/roleplay\/blr_/.test(home) && /data-count="7">0<\/b><span>AI locals/.test(home),
      practice_links_go_to_bengaluru_roleplays: /href="#\/roleplay\/blr_/.test(conf) && !/href="#\/roleplay\/(mum_|auto")/.test(conf),
      tutor_is_kannada: has(tutor, 'Namaskara') && has(tutor, 'exact Kannada words') && has(tutor, 'What does &#39;swalpa&#39; mean?'),
      offline_tutor_answers_in_kannada: E.tutorReply('I need a ride to Indiranagar.', []).phrases[0].roman === 'Indiranagarakke bartira? Meter haaki.' &&
        E.tutorReply('Which metro line goes to Whitefield?', []).phrases[0].hi === 'ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ ಯಾವ ಲೈನ್?' && has(E.tutorReply("What does 'swalpa' mean?", []).intro, 'A little') &&
        E.tutorReply('blah', []).phrases[0].roman === 'Namaskara, hegiddira?' && !E.tutorReply("What does 'jugaad' mean?", []).intro.includes('improvised'),
      speech_is_kannada: E.speechLang() === 'kn-IN' && E.packLanguage() === 'kn' && E.allCards()[0].hi === 'ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?' && E.allCards().length === 36,
      the_review_status_is_kannadas: E.reviewStatus().native_review_status === 'pending' && has(E.reviewStatus().note, 'Kannada'),
      ai_roleplay_and_tutor_ask_for_kannada: aiBodies[0].language === 'Kannada' && aiBodies[0].scenario === 'blr_auto' && aiBodies[0].city === 'Bengaluru' && aiBodies[1].language === 'Kannada',
      the_server_accepts_it: real.status === 200 && JSON.parse(real.text).reason === 'offline',
    };
    // the English view shows the same Kannada pack, English first, and its content is still Bengaluru's Kannada
    E.state.language = 'en'; E.save(); await settle();
    var en = await go('lesson/2');
    out.english_view_teaches_kannada = has(en, 'Please use the meter.') && has(en, 'ಮೀಟರ್ ಹಾಕಿ.') && E.packLanguage() === 'kn' && E.speechLang() === 'kn-IN' &&
      E.local().tutor.language === 'Kannada' && E.packKey() === 'bengaluru';
    // a language Bengaluru does not offer (an old or edited state) falls back to Kannada, never Hindi or Marathi
    E.state.language = 'mr'; E.save(); await settle();
    out.an_unoffered_language_falls_back_to_kannada = E.language() === 'kn' && E.speechLang() === 'kn-IN' && has(await go('lesson/1'), 'ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?');
    E.state.city = 'mumbai'; E.state.language = 'mr'; E.save(); await settle();
    out.mumbai_marathi_is_unchanged = E.speechLang() === 'mr-IN' && has(await go('lesson/2'), 'मीटरने येणार का?') && E.local().tutor.language === 'Marathi';
    E.state.city = 'delhi'; E.state.language = 'hi'; E.save(); await settle();
    out.delhi_is_unchanged = E.speechLang() === 'hi-IN' && E.packLanguage() === 'hi' && has(await go('lesson/2'), 'भैया, कनॉट प्लेस चलोगे?') && JSON.stringify(E.local()) === '{}';
    return out;
  },
  async puducherry_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    // Tamil, the city's own pack
    E.state.city = 'puducherry'; E.state.language = 'ta'; E.save(); await settle();
    var taPack = await go('pack'), taLesson = await go('lesson/2'), taRp = await go('roleplay/pdy_scooter');
    var scooter = E.roleplayReply('pdy_scooter', 'Oru naalaikku evvalavu?', []);
    var taHome = await go('');
    var out = {
      tamil_pack_is_puducherrys: has(taPack, 'Your First Week in Puducherry') && has(taLesson, 'ஸ்கூட்டர் வாடகைக்கு கிடைக்குமா?') && has(taLesson, 'Puducherry · approx.') && has(taLesson, 'Scooter rental'),
      tamil_roleplay: has(taRp, 'Velu') && has(taRp, 'Type in Tamil') && has(scooter.text, 'naanooru rupaai'),
      tamil_home: has(taHome, 'Right now in Puducherry') && /href="#\/roleplay\/pdy_(?!fr_)/.test(taHome),
      tamil_speech: E.speechLang() === 'ta-IN' && E.packKey() === 'puducherry' && E.local().tutor.language === 'Tamil' && E.reviewStatus().note.indexOf('Puducherry Tamil') === 0,
      tamil_tutor: E.tutorReply('I need a ride to Auroville.', []).phrases[0].roman === 'Auroville pogumaa? Evvalavu?' && has(E.tutorReply('How do I rent a scooter?', []).phrases[0].roman, 'Scooter vaadagaikku'),
    };
    // French, its second pack
    E.state.language = 'fr'; E.save(); await settle();
    var frPack = await go('pack'), frLesson = await go('lesson/1'), frRp = await go('roleplay/pdy_fr_bike'), frTutor = await go('tutor');
    var bike = E.roleplayReply('pdy_fr_bike', 'Je voudrais louer un velo.', []), accented = E.roleplayReply('pdy_fr_bike', 'Je voudrais louer un vélo.', []);
    await E.askAI({ mode: 'roleplay', scenario: 'pdy_fr_bike', history: [{ role: 'me', text: 'Bonjour' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[aiBodies.length - 1]), WRITE);
    out.french_pack = has(frPack, 'Your First Week in Puducherry') && has(frPack, 'not yet checked by a native French speaker') && E.pack() === G.LANGUAGE_PACKS.puducherry.fr;
    out.french_lesson_shows_french_and_a_pronunciation_guide = has(frLesson, 'Bonjour, comment allez-vous ?') && has(frLesson, 'bon-ZHOOR') && has(frLesson, 'Je suis nouvelle ici.');
    out.french_roleplay_ignores_accents = has(frRp, 'Monsieur Pierre') && has(frRp, 'Type in French') && bike.text === accented.text && has(bike.text, 'Bien sûr');
    out.french_tutor = has(frTutor, 'Bonjour') && has(frTutor, 'exact French words') && E.tutorReply('How do I rent a bicycle?', []).phrases[0].roman === 'Je voudrais louer un vélo.';
    out.french_speech_and_ai = E.speechLang() === 'fr-FR' && E.packKey() === 'puducherry:fr' && aiBodies[aiBodies.length - 1].language === 'French' && real.status === 200;
    out.french_practice_never_scores = E.packLanguage() === 'fr';
    // each pack keeps its own progress
    E.daysDone().push(1); E.save(); await settle();
    E.state.language = 'ta'; E.save(); await settle();
    out.each_language_keeps_its_own_days = JSON.stringify(E.daysDone()) === '[]' && JSON.stringify(E.state.packDays['puducherry:fr']) === '[1]';
    // Chennai is not given French
    E.state.city = 'chennai'; E.state.language = 'fr'; E.save(); await settle();
    out.chennai_falls_back_to_tamil = E.language() === 'ta' && E.speechLang() === 'ta-IN';
    return out;
  },
  async jammu_kashmir_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    var out = {};
    var cases = [['ks', 'jk', 'jk_food', 'Noon chai chha?', 'Aa, garam noon chai!', 'ks-IN', 'Kashmiri'],
                 ['doi', 'jk:doi', 'jk_doi_auto', 'Matador kutthen thammdi ai?', 'Matador baahar stand', 'doi-IN', 'Dogri'],
                 ['ur', 'jk:ur', 'jk_ur_auto', 'Shikaara kahan milega?', 'Shikaara Dal Gate ke ghaat par', 'ur-IN', 'Urdu']];
    for (var i = 0; i < cases.length; i++) {
      var c = cases[i];
      E.state.city = 'jk'; E.state.language = c[0]; E.save(); await settle();
      var pack = await go('pack'), rp = await go('roleplay/' + c[2]);
      out[c[0] + '_pack'] = has(pack, 'Your First Week in Jammu') && E.packKey() === c[1] && E.speechLang() === c[5] && E.local().tutor.language === c[6];
      out[c[0] + '_roleplay'] = has(rp, 'Type in ' + c[6]) && E.roleplayReply(c[2], c[3], []).text.indexOf(c[4]) === 0;
    }
    E.state.language = 'ks'; E.save(); await settle();
    out.kashmiri_says_it_is_a_draft = E.reviewStatus().note.indexOf('Kashmiri: an AI-assisted first draft') === 0;
    out.kashmiri_tutor = E.tutorReply('I need an auto to Dal Gate.', []).phrases[0].roman === 'Dal Gate gatshiv? Kotah poonsa?';
    await E.askAI({ mode: 'roleplay', scenario: 'jk_auto', history: [{ role: 'me', text: 'Assalaam alaikum' }] });
    out.kashmiri_ai = aiBodies[aiBodies.length - 1].language === 'Kashmiri' && http('POST', '/api/ai', JSON.stringify(aiBodies[aiBodies.length - 1]), WRITE).status === 200;
    // Hyderabad keeps its own Urdu, and Delhi is never given Kashmiri
    E.state.city = 'hyderabad'; E.state.language = 'ur'; E.save(); await settle();
    out.hyderabad_urdu_unchanged = E.packKey() === 'hyderabad:ur' && E.pack() === G.LANGUAGE_PACKS.hyderabad.ur;
    E.state.city = 'delhi'; E.state.language = 'ks'; E.save(); await settle();
    out.delhi_falls_back_to_hindi = E.language() === 'hi' && E.speechLang() === 'hi-IN';
    return out;
  },
  async hyderabad_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    // Telugu, the city's own pack
    E.state.city = 'hyderabad'; E.state.language = 'te'; E.save(); await settle();
    var tePack = await go('pack'), teLesson = await go('lesson/2'), teRp = await go('roleplay/hyd_auto'), teHome = await go('');
    var auto = E.roleplayReply('hyd_auto', 'Entha sepu padutundi?', []);
    var out = {
      telugu_pack: has(tePack, 'Your First Week in Hyderabad') && has(teLesson, 'మీటర్ వేయండి.') && has(teLesson, 'Hyderabad · approx.'),
      telugu_roleplay: has(teRp, 'Srinu') && has(teRp, 'Type in Telugu') && auto.text.indexOf('Traffic unte') === 0,
      telugu_home: has(teHome, 'Right now in Hyderabad') && /href="#\/roleplay\/hyd_(?!ur_)/.test(teHome),
      telugu_speech: E.speechLang() === 'te-IN' && E.packKey() === 'hyderabad' && E.local().tutor.language === 'Telugu' && E.reviewStatus().note.indexOf('Hyderabad Telugu') === 0,
      telugu_tutor: E.tutorReply('I need a ride to Charminar.', []).phrases[0].roman === 'Charminar ki vastaaraa? Meter veyandi.',
    };
    // Urdu, its second pack
    E.state.language = 'ur'; E.save(); await settle();
    var urPack = await go('pack'), urLesson = await go('lesson/1'), urRp = await go('roleplay/hyd_ur_auto');
    var metro = E.roleplayReply('hyd_ur_auto', 'Metro station kidhar hai?', []);
    await E.askAI({ mode: 'roleplay', scenario: 'hyd_ur_auto', history: [{ role: 'me', text: 'Assalaam alaikum' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[aiBodies.length - 1]), WRITE);
    out.urdu_pack = has(urPack, 'not yet checked by a native Urdu speaker') && E.pack() === G.LANGUAGE_PACKS.hyderabad.ur && has(urLesson, 'السلام علیکم! آپ کیسے ہیں؟') && has(urLesson, 'Main yahan nayi hoon.');
    out.urdu_roleplay = has(urRp, 'Salim bhai') && has(urRp, 'Type in Urdu') && metro.text.indexOf('Metro chahiye toh') === 0;
    out.urdu_speech_and_ai = E.speechLang() === 'ur-IN' && E.packKey() === 'hyderabad:ur' && aiBodies[aiBodies.length - 1].language === 'Urdu' && real.status === 200;
    out.urdu_tutor = E.local().tutor.language === 'Urdu' && E.tutorReply('I need an auto to Golconda.', []).phrases[0].roman === 'Golconda chaloge? Meter se.';
    // each pack keeps its own progress, and Lucknow is never given Urdu
    E.daysDone().push(1); E.save(); await settle();
    E.state.language = 'te'; E.save(); await settle();
    out.each_language_keeps_its_own_days = JSON.stringify(E.daysDone()) === '[]' && JSON.stringify(E.state.packDays['hyderabad:ur']) === '[1]';
    E.state.city = 'lucknow'; E.state.language = 'ur'; E.save(); await settle();
    out.lucknow_falls_back_to_hindi = E.language() === 'hi' && E.speechLang() === 'hi-IN';
    return out;
  },
  async kolkata_in_bengali_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    E.state.city = 'kolkata'; E.state.language = 'bn'; E.save(); await settle();
    var pack = await go('pack'), lesson = await go('lesson/2'), rp = await go('roleplay/kol_taxi'), home = await go('');
    var taxi = E.roleplayReply('kol_taxi', 'Kotokkhon lagbe?', []), place = E.roleplayReply('kol_taxi', 'Park Street jaben?', []);
    await E.askAI({ mode: 'roleplay', scenario: 'kol_taxi', history: [{ role: 'me', text: 'Nomoshkar' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[aiBodies.length - 1]), WRITE);
    var out = {
      bengali_pack: has(pack, 'Your First Week in Kolkata') && has(pack, 'not yet checked by a native Bengali speaker') && has(lesson, 'মিটারে যাবেন তো?') && has(lesson, 'Kolkata · approx.'),
      bengali_roleplay: has(rp, 'Bapi da') && has(rp, 'Type in Bengali') && taxi.text.indexOf('Jaam thakle') === 0 && place.text.indexOf('Park Street? Hyan, cholun.') === 0,
      bengali_home: has(home, 'Right now in Kolkata') && /href="#\/roleplay\/kol_/.test(home),
      bengali_speech_and_ai: E.speechLang() === 'bn-IN' && E.packKey() === 'kolkata' && aiBodies[aiBodies.length - 1].language === 'Bengali' && real.status === 200,
      bengali_tutor: E.local().tutor.language === 'Bengali' && E.tutorReply('I need a taxi to Esplanade.', []).phrases[0].roman === 'Esplanade jaben? Meter-e.',
    };
    // the English view shows the same Bengali pack, English first
    E.state.language = 'en'; E.save(); await settle();
    out.english_view_teaches_bengali = has(await go('lesson/2'), 'মিটারে যাবেন তো?') && E.packLanguage() === 'bn' && E.speechLang() === 'bn-IN';
    // a language Kolkata does not offer (an old or edited state) falls back to Bengali, never Hindi
    E.state.language = 'hi'; E.save(); await settle();
    out.an_unoffered_language_falls_back_to_bengali = E.language() === 'bn' && E.speechLang() === 'bn-IN';
    E.state.city = 'delhi'; E.state.language = 'hi'; E.save(); await settle();
    out.delhi_is_unchanged = E.speechLang() === 'hi-IN' && has(await go('lesson/2'), 'भैया, कनॉट प्लेस चलोगे?') && JSON.stringify(E.local()) === '{}';
    return out;
  },
  async jaipur_and_lucknow_work() {
    await settle();
    await signIn();
    var E = G.Engine;
    var out = {};
    // each city in Hindi, with its own pack, roleplays, tutor, prices and review note
    var cases = [['jaipur', 'Jaipur', 'jpr_auto', 'Hawa Mahal chaloge?', 'Hawa Mahal? Haan, chalo.', 'Ramesh', 'Khamma ghani', 'Jaipur Hindi'],
                 ['lucknow', 'Lucknow', 'lko_auto', 'Hazratganj chalenge?', 'Hazratganj? Ji, baithiye.', 'Rafiq', 'Aadaab', 'Lucknow Hindi'],
                 ['bhopal', 'Bhopal', 'bpl_auto', 'New Market chaloge?', 'New Market? Haan, baitho.', 'Rafiq bhai', 'Namaste', 'Bhopal Hindi']];
    for (var i = 0; i < cases.length; i++) {
      var c = cases[i], id = c[0], name = c[1];
      E.state.city = id; E.state.language = 'hi'; E.save(); await settle();
      var pack = await go('pack'), lesson = await go('lesson/2'), rp = await go('roleplay/' + c[2]), home = await go('');
      var reply = E.roleplayReply(c[2], c[3], []);
      out[id + '_pack'] = has(pack, 'Your First Week in ' + name) && has(lesson, name + ' · approx.');
      out[id + '_roleplay'] = has(rp, c[5]) && reply.text.indexOf(c[4]) === 0 && E.speechLang() === 'hi-IN' && E.packKey() === id;
      out[id + '_home'] = has(home, 'Right now in ' + name) && new RegExp('href="#/roleplay/' + c[2].slice(0, 4)).test(home);
      out[id + '_tutor'] = E.local().tutor.greet === c[6] && E.reviewStatus().note.indexOf(c[7]) === 0 && E.packLanguage() === 'hi';
      // the English view shows the same Hindi pack, and Hindi is the only language the city offers besides English
      E.state.language = 'hi'; E.save(); await settle();
      E.state.language = 'mr'; E.save(); await settle();
      out[id + '_falls_back_to_hindi'] = E.language() === 'hi' && E.speechLang() === 'hi-IN';
    }
    // the neighbours are unchanged
    E.state.city = 'delhi'; E.state.language = 'hi'; E.save(); await settle();
    out.delhi_is_unchanged = E.packLanguage() === 'hi' && has(await go('lesson/2'), 'भैया, कनॉट प्लेस चलोगे?') && JSON.stringify(E.local()) === '{}';
    E.state.city = 'mumbai'; E.state.language = 'hi'; E.save(); await settle();
    out.mumbai_is_unchanged = E.packKey() === 'mumbai' && E.local().tutor.greet === 'Namaskar';
    return out;
  },
  async chennai_in_tamil_works() {
    await settle();
    await signIn();
    var E = G.Engine;
    E.state.city = 'chennai'; E.state.language = 'ta'; E.save(); await settle();
    var pack = await go('pack'), lessons = [];
    for (var d = 1; d <= 7; d++) lessons.push(await go('lesson/' + d));
    var rp = await go('roleplay/chn_auto');
    var trip = E.roleplayReply('chn_auto', 'T. Nagar pogumaa?', []), meter = E.roleplayReply('chn_auto', 'Meter podunga.', []);
    var english = E.roleplayReply('chn_auto', 'I want to go please', []);
    var home = await go(''), conf = await go('confidence'), tutor = await go('tutor');
    await E.askAI({ mode: 'roleplay', scenario: 'chn_auto', history: [{ role: 'me', text: 'Vanakkam' }] });
    await E.askAI({ mode: 'tutor', history: [{ role: 'me', text: 'hi' }] });
    var real = http('POST', '/api/ai', JSON.stringify(aiBodies[0]), WRITE);
    var devanagari = /[ऀ-ॿಀ-೿]/, delhiOrMumbai = /Connaught|Sarojini|Churchgate|Dadar|Colaba|vada pav|Kaali-peeli|Indiranagar|darshini/;
    var out = {
      first_week_is_chennai: has(pack, 'Your First Week in Chennai') && has(pack, 'AI-assisted editorial review only, not yet checked by a native Tamil speaker'),
      every_day_renders_in_tamil: lessons.every(function (html, i) { return has(html, 'Day ' + (i + 1)); }) && has(lessons[0], 'வணக்கம், எப்படி இருக்கீங்க?') &&
        has(lessons[1], 'மீட்டர் போடுங்க.') && has(lessons[6], 'சூப்பர்! அப்புறம் பாக்கலாம்.'),
      no_devanagari_and_no_other_city: ![pack].concat(lessons).some(function (html) { return devanagari.test(html.replace(/कृपया पढ़िए/g, '')) || delhiOrMumbai.test(html); }),
      chennai_prices: has(lessons[1], 'Chennai · approx.') && has(lessons[1], 'Chennai Metro token') && /value="idli" selected/.test(lessons[2]) && /value="kurta" selected/.test(lessons[3]),
      roleplay_is_tamil: has(rp, 'Murugan') && has(rp, 'Enga poganum?') && has(rp, 'Type in Tamil'),
      side_panel_lists_only_chennai_roleplays: has(rp, 'href="#/roleplay/chn_food"') && !/href="#\/roleplay\/(mum_|blr_|food|auto)/.test(rp),
      offline_replies_follow_the_conversation: trip.text === 'T. Nagar? Sari, ukkaarunga.' && has(meter.text, 'fifty rupees kudunga'),
      an_english_reply_is_coached_in_tamil: english.matched === false && has(english.tip, 'suggested Tamil replies'),
      home_links_to_chennai_roleplays: has(home, 'Right now in Chennai') && /href="#\/roleplay\/chn_/.test(home) && /data-count="7">0<\/b><span>AI locals/.test(home),
      practice_links_go_to_chennai_roleplays: /href="#\/roleplay\/chn_/.test(conf) && !/href="#\/roleplay\/(mum_|blr_|auto")/.test(conf),
      tutor_is_tamil: has(tutor, 'Vanakkam') && has(tutor, 'exact Tamil words') && has(tutor, 'What does &#39;konjam&#39; mean?'),
      offline_tutor_answers_in_tamil: E.tutorReply('I need a ride to Adyar.', []).phrases[0].roman === 'Adyar pogumaa? Meter podunga.' &&
        E.tutorReply('Which metro line goes to Guindy?', []).phrases[0].hi === 'ஏர்போர்ட்டுக்கு எந்த லைன்?' && has(E.tutorReply("What does 'konjam' mean?", []).intro, 'A little') &&
        E.tutorReply('blah', []).phrases[0].roman === 'Vanakkam, eppadi irukeenga?' && !E.tutorReply("What does 'jugaad' mean?", []).intro.includes('improvised'),
      speech_is_tamil: E.speechLang() === 'ta-IN' && E.packLanguage() === 'ta' && E.allCards()[0].hi === 'வணக்கம், எப்படி இருக்கீங்க?' && E.allCards().length === 36,
      the_review_status_is_tamils: E.reviewStatus().native_review_status === 'pending' && has(E.reviewStatus().note, 'Tamil'),
      ai_roleplay_and_tutor_ask_for_tamil: aiBodies[0].language === 'Tamil' && aiBodies[0].scenario === 'chn_auto' && aiBodies[0].city === 'Chennai' && aiBodies[1].language === 'Tamil',
      the_server_accepts_it: real.status === 200 && JSON.parse(real.text).reason === 'offline',
    };
    // the English view shows the same Tamil pack, English first, and its content is still Chennai's Tamil
    E.state.language = 'en'; E.save(); await settle();
    var en = await go('lesson/2');
    out.english_view_teaches_tamil = has(en, 'Please use the meter.') && has(en, 'மீட்டர் போடுங்க.') && E.packLanguage() === 'ta' && E.speechLang() === 'ta-IN' &&
      E.local().tutor.language === 'Tamil' && E.packKey() === 'chennai';
    // a language Chennai does not offer (an old or edited state) falls back to Tamil, never Hindi or Kannada
    E.state.language = 'kn'; E.save(); await settle();
    out.an_unoffered_language_falls_back_to_tamil = E.language() === 'ta' && E.speechLang() === 'ta-IN' && has(await go('lesson/1'), 'வணக்கம், எப்படி இருக்கீங்க?');
    E.state.city = 'bengaluru'; E.state.language = 'kn'; E.save(); await settle();
    out.bengaluru_kannada_is_unchanged = E.speechLang() === 'kn-IN' && has(await go('lesson/2'), 'ಮೀಟರ್ ಹಾಕಿ.') && E.local().tutor.language === 'Kannada';
    E.state.city = 'delhi'; E.state.language = 'hi'; E.save(); await settle();
    out.delhi_is_unchanged = E.speechLang() === 'hi-IN' && E.packLanguage() === 'hi' && has(await go('lesson/2'), 'भैया, कनॉट प्लेस चलोगे?') && JSON.stringify(E.local()) === '{}';
    return out;
  },
  async an_old_invalid_city_language_pair_is_repaired() {
    // the account's stored state says Delhi "in Marathi" (planted by the test, as an older version of the app could have saved it)
    await settle();
    await signIn();
    var lesson = await go('lesson/2'), rp = await go('roleplay/auto');
    var before = serverGet('/api/state/' + handle()).data.state;
    sent.length = 0;
    G.Engine.bump('food', 1); await settle();                // any change saves the state
    var puts = stateRequests().filter(function (r) { return r.method === 'PUT'; });
    var after = serverGet('/api/state/' + handle()).data.state;
    return {
      the_stored_pair_was_invalid: before.city === 'delhi' && before.language === 'mr',
      delhi_is_shown_in_its_own_language: G.Engine.language() === 'hi' && G.Engine.speechLang() === 'hi-IN' && G.Engine.pack() === G.PACKS.delhi,
      no_marathi_reaches_delhi: !has(lesson, 'मीटरने') && !has(rp, 'Type in Marathi') && has(rp, 'Type in Hinglish'),
      the_next_save_repairs_it: puts.length === 1 && JSON.parse(puts[0].body).language === 'hi' && after.city === 'delhi' && after.language === 'hi',
      progress_is_kept: after.confidence.food === before.confidence.food + 1 && after.xp === before.xp + 5 &&          // bump: +1 food, +5 XP
        ['greetings', 'transport', 'shopping', 'directions', 'college', 'smalltalk'].every(function (k) { return after.confidence[k] === before.confidence[k]; }),
    };
  },
  async each_pack_keeps_its_own_progress() {
    await settle();
    await signIn();
    var E = G.Engine, st = E.state;
    function use(city, lang) { st.city = city; st.language = lang; E.save(); }
    use('delhi', 'hi'); G.A.completeDay(3); await settle();
    var delhiCards = E.allCards().map(function (c) { return c.id; }); E.review(delhiCards[0], true);
    use('mumbai', 'hi'); var mumbaiPack = await go('pack'), mumbaiDone = E.daysDone().slice();
    G.A.completeDay(1); await settle();
    var mumbaiCards = E.allCards().map(function (c) { return c.id; }); E.review(mumbaiCards[0], true);
    use('mumbai', 'en'); var englishKey = E.packKey(), englishDone = E.daysDone().slice();
    use('mumbai', 'mr'); var marathiPack = await go('pack'), marathiDone = E.daysDone().slice(), marathiCards = E.allCards().map(function (c) { return c.id; });
    var marathiDue = E.dueCards().length;
    use('delhi', 'hi'); var delhiPack = await go('pack');
    await settle();
    var server = serverGet('/api/state/' + handle()).data.state;
    return {
      delhi_keeps_its_keys: E.packKey() === '' && delhiCards[0] === 'd1-0' && JSON.stringify(st.completedDays) === '[3]' && has(delhiPack, '>1</span> / 7 days complete'),
      mumbai_starts_on_its_own: mumbaiDone.length === 0 && has(mumbaiPack, '>0</span> / 7 days complete'),
      mumbai_has_its_own_cards: mumbaiCards[0] === 'mumbai:d1-0' && mumbaiCards.length === 35,
      english_view_shares_the_hindi_pack: englishKey === 'mumbai' && JSON.stringify(englishDone) === '[1]',
      marathi_has_its_own_days_and_cards: JSON.stringify(marathiDone) === '[]' && has(marathiPack, '>0</span> / 7 days complete') && marathiCards[0] === 'mumbai:mr:d1-0' && marathiDue === 35,
      nothing_is_lost_on_the_way_back: !!st.srs['d1-0'] && !!st.srs['mumbai:d1-0'] && JSON.stringify(st.packDays) === '{"mumbai":[1],"mumbai:mr":[]}',
      the_server_keeps_it: JSON.stringify(server.completedDays) === '[3]' && JSON.stringify(server.packDays) === '{"mumbai":[1],"mumbai:mr":[]}' && !!server.srs['mumbai:d1-0'],
    };
  },
  async learn_tools_follow_the_city_and_language() {
    await settle();
    await signIn();
    var E = G.Engine, st = E.state, out = {};
    async function tab(t) { G.A.learnTab(t); await settle(); return await go('learn'); }
    async function look(city, lang) {
      st.city = city; st.language = lang; E.save(); await settle();
      return { read: await tab('reading'), place: await tab('placement'), progress: await go('progress'), tutor: await go('tutor'),
               ride: E.tutorReply('I need a taxi to the airport', []), train: E.tutorReply('Which metro or local train do I take?', []),
               food: E.tutorReply('How do I order food?', []), word: E.tutorReply("What does 'jugaad' mean?", []), other: E.tutorReply('blah', []) };
    }
    var delhi = await look('delhi', 'hi'), mumbai = await look('mumbai', 'hi'), english = await look('mumbai', 'en'), marathi = await look('mumbai', 'mr');
    var delhiAgain = await look('delhi', 'hi');
    var delhiOnly = /Sarojini|Connaught|Rajiv Chowk|Huda City|Chandni Chowk|chhole|Dilli|India Gate|very Delhi/;
    out.delhi_is_unchanged = has(delhi.read, 'Ravi in Delhi') && has(delhi.place, 'Seedhe jaiye') && has(delhi.progress, 'Dilli foodie') && has(delhi.progress, 'Sarojini bargainer') &&
      has(delhi.tutor, 'Namaste Test User') && has(delhi.tutor, 'bargain at Sarojini') && has(delhi.ride.phrases[0].roman, 'Bhaiya, airport chaloge?') &&
      has(delhi.train.phrases[0].roman, 'Rajiv Chowk') && has(delhi.food.phrases[0].roman, 'chhole bhature') && has(delhi.word.intro, 'very Delhi') && has(delhi.other.note, 'India Gate') &&
      JSON.stringify(delhi) === JSON.stringify(delhiAgain);
    out.mumbai_hindi_is_mumbai = has(mumbai.read, 'Asha in Mumbai') && has(mumbai.place, 'Bridge se us paar jao') && has(mumbai.progress, 'Mumbai foodie') &&
      has(mumbai.progress, 'Colaba bargainer') && has(mumbai.progress, 'Meter pro') && has(mumbai.tutor, 'Namaskar Test User') && has(mumbai.tutor, 'Colaba Causeway') &&
      has(mumbai.ride.phrases[0].roman, 'Bhaiya, airport chaloge? Meter se.') && has(mumbai.train.phrases[0].roman, 'kaun si local') && has(mumbai.food.phrases[0].roman, 'vada pav') &&
      has(mumbai.word.intro, 'Mumbai runs on it') && has(mumbai.other.note, 'Churchgate');
    out.english_view_uses_mumbai_hindi = english.read === mumbai.read && has(english.progress, 'Mumbai foodie') && english.ride.phrases[0].roman === mumbai.ride.phrases[0].roman;
    out.marathi_is_marathi = has(marathi.read, 'आशा मुंबईत नवीन आहे.') && has(marathi.place, 'Pulavarun palikade ja') && has(marathi.progress, 'Said your first Marathi phrase') &&
      has(marathi.progress, 'Dadar bargainer') && has(marathi.ride.phrases[0].roman, 'Dada, airportla yenar ka? Meterne.') && has(marathi.train.phrases[0].roman, 'jaanari local konti') &&
      marathi.food.phrases[0].hi === 'एक वडापाव द्या.' && !has(marathi.word.intro, 'jugaad') && has(marathi.other.phrases[0].roman, 'kase aahat');
    out.no_delhi_in_mumbai = [mumbai, english, marathi].every(function (v) { return !delhiOnly.test(v.read + v.place + v.progress + v.tutor + JSON.stringify([v.ride, v.train, v.food, v.other])); });
    return out;
  },
  async sign_in_and_out_switch_identity() {
    await settle();
    G.Engine.bump('food', 29); await settle();               // the anonymous visitor's own progress: food 99
    profileRoot = element('profile-root');
    G.ProfileView.page(); await settle();                    // the real profile page: the sign-in card
    profileRoot.kids['#pf-email'] = { value: E('EMAIL') }; profileRoot.kids['#pf-pass'] = { value: E('PASSWORD') };
    sent.length = 0;
    await profileRoot.kids['#pf-login'].onclick(); await settle();
    var loginSignalled = writesAreSignalled(sent.filter(function (s) { return s.url === '/api/auth/login'; }));
    var me = handle();
    var signedIn = { reads_own_state: stateRequests().some(function (s) { return s.method === 'GET' && s.url === '/api/state/' + me; }),
                     anonymous_progress_not_carried_over: G.Engine.state.confidence.food !== 99,
                     anonymous_progress_never_uploaded: stateRequests().every(function (s) { return s.method !== 'PUT' || JSON.parse(s.body).confidence.food !== 99; }) };
    sent.length = 0;
    await profileRoot.kids['#pf-logout'].onclick(); await settle();
    var logoutSignalled = writesAreSignalled(sent.filter(function (s) { return s.url === '/api/auth/logout'; }));
    sent.length = 0;
    var back = G.Engine.state.confidence.food === 99;
    G.Engine.bump('food', 1); await settle();
    var server = serverGet('/api/state/' + me);
    return { signed_in_reads_own_state: signedIn.reads_own_state, anonymous_progress_not_carried_over: signedIn.anonymous_progress_not_carried_over,
             anonymous_progress_never_uploaded: signedIn.anonymous_progress_never_uploaded, signed_out_is_anonymous_again: back,
             signed_out_writes_nothing_to_the_server: stateRequests().length === 0, really_signed_out: server.status === 401,
             login_is_signalled: loginSignalled, logout_is_signalled: logoutSignalled };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
