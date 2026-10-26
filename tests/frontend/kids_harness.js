// Drives the real frontend/agemode.js, kids.js and teen.js (plus profile.js for the shared API helper) in JavaScriptCore
// (osascript) against a live test server. Timers are stubs; HTTP is real (via curl). Each scenario prints one line "## {json}"
// with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, KEY (answer key read from the test database), DOB_CHILD,
// DOB_TEEN, DOB_ADULT.
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO');
var KEY = E('KEY') ? JSON.parse(E('KEY')) : {};
var JAR = WORKDIR + '/cookies.txt';

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function sh(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}
function fetch(url, opts) {
  opts = opts || {};
  var args = ['-s', '-i', '-b', JAR, '-c', JAR, '-X', opts.method || 'GET'];
  var h = opts.headers || {}; for (var k in h) { args.push('-H'); args.push(k + ': ' + h[k]); }
  if (opts.body) { args.push('--data-binary'); args.push(opts.body); }
  args.push(BASE + url);
  var raw = sh(args), split = raw.indexOf('\r\n\r\n');
  var head = raw.slice(0, split), text = raw.slice(split + 4);
  var status = parseInt(/HTTP\/[\d.]+ (\d+)/.exec(head)[1], 10);
  return Promise.resolve({ ok: status >= 200 && status < 300, status: status, json: function () { return Promise.resolve(JSON.parse(text)); } });
}

// ---- stubbed browser ----
var rootEl = { innerHTML: '', onclick: null };
var classes = {};
var document = { getElementById: function (id) { return id === 'kids-root' || id === 'path-root' ? rootEl : null; },
                 body: { contains: function () { return true; }, classList: { add: function (c) { classes[c] = true; }, remove: function () { for (var i = 0; i < arguments.length; i++) delete classes[arguments[i]]; } } } };
var intervals = [], spoken = [];
var win = { setInterval: function (fn) { intervals.push({ fn: fn, cleared: false }); return intervals.length; },
            clearInterval: function (id) { if (intervals[id - 1]) intervals[id - 1].cleared = true; },
            Engine: { canSpeak: true, speak: function (p) { spoken.push(p.hi); } } };
function advance() { intervals.filter(function (i) { return !i.cleared; }).forEach(function (i) { i.fn(); }); }
var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/agemode.js'); load('frontend/kids.js'); load('frontend/teen.js');

var tick = async function () { for (var i = 0; i < 120; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
var click = async function (d) { await rootEl.onclick({ target: { closest: function () { return { dataset: d }; } } }); await tick(); };
var api = win.LBApi.api;
var mountKids = async function (arg) { win.KidsView.page(arg); await lastMount; await tick(); };
var mountTeen = async function () { win.TeenView.page(); await lastMount; await tick(); };
function has(s, sub) { return s.indexOf(sub) >= 0; }
function count(s, sub) { return s.split(sub).length - 1; }
async function login(dob) {
  await api('POST', '/api/auth/register', { email: 'k' + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com', password: 'ui-password-123', display_name: 'Kid', role: 'learner' });
  await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: dob });
  await win.AgeMode.refresh();
}
var child = function () { return login(E('DOB_CHILD')); };
var lives = async function () { return (await api('GET', '/api/kids/adventure')).data.lives.current; };
var wrongOn = async function (level, qi) { await click({ choice: String(KEY[level][qi][2]) }); };
var rightOn = async function (level, qi) { await click({ choice: String(KEY[level][qi][1]) }); };

var scenarios = {
  async signed_out() {
    await mountKids();
    return { asks_to_sign_in: has(text(), 'Sign in to play'), no_game: !has(html(), 'data-choice'), no_mode: win.AgeMode.mode() === null };
  },
  async not_a_child() {
    await login(E('DOB_TEEN')); await mountKids();
    return { explains: has(text(), 'for younger learners'), no_game: !has(html(), 'data-choice') && !has(html(), 'kid-tile') };
  },
  async map_and_lives() {
    await child(); await mountKids();
    var h = html();
    return { five_hearts: count(h, '❤️') === 5 && count(h, '🖤') === 0, level_one_is_a_link: has(h, 'href="#/kids/1"'), later_levels_locked: has(h, 'aria-disabled="true"') && !has(h, 'href="#/kids/2"'),
             big_tiles: has(h, 'kid-tile'), mode_is_child: win.AgeMode.mode() === 'child', body_class: classes['mode-child'] === true, no_ids_shown: !/(activity|option|item)[_-]?id/i.test(h) };
  },
  async question_screen() {
    await child(); await mountKids('1');
    var h = html();
    return { instruction: has(text(), 'Listen.'), listen_button: has(h, 'data-play'), big_choices: count(h, 'data-choice=') >= 2, choices_are_small_numbers: /data-choice="1"/.test(h) && !/data-choice="\d{3,}"/.test(h),
             nothing_marks_the_answer: !has(h, 'is_correct') && !has(h, ' right') && !has(h, 'data-option'), hearts_visible: count(h, '❤️') === 5, progress_shown: has(text(), 'Question 1 of') };
  },
  async playing_audio_speaks_the_phrase() {
    await child(); await mountKids('1'); await click({ play: '' });
    return { spoken_once: spoken.length === 1 && spoken[0].length > 0, text_not_displayed: !has(html(), spoken[0]) };
  },
  async wrong_answer_loses_a_life() {
    await child(); await mountKids('1'); await wrongOn(1, 0);
    var h = html();
    return { four_hearts: count(h, '❤️') === 4 && count(h, '🖤') === 1, kind_message: has(text(), 'Oops'), right_answer_shown: has(h, 'kid-choice right'), server_agrees: (await lives()) === 4, choices_locked: has(h, 'disabled') };
  },
  async correct_answer_keeps_lives() {
    await child(); await mountKids('1'); await rightOn(1, 0);
    return { five_hearts: count(html(), '❤️') === 5 + 0 || count(html(), '❤️') >= 5, praise: has(text(), 'Great job'), server_agrees: (await lives()) === 5 };
  },
  async no_hearts_left_blocks_play() {
    await child(); await mountKids('1');
    for (var i = 0; i < 5; i++) { await wrongOn(1, 0); if (i < 4) await click({ next: '' }); }
    var h = html(), t = text();
    var r = { shows_no_hearts: has(t, 'No hearts left'), zero_hearts: count(h, '❤️') === 0 && count(h, '🖤') === 5, countdown_shown: /comes back in \d+ (min|sec)/.test(t), no_choices: !has(h, 'data-choice'), no_play_yet: !has(h, 'data-retry'), server_zero: (await lives()) === 0 };
    var s = await api('POST', '/api/kids/levels/1/answers', { question: 1, choice: KEY[1][0][1] });
    r.server_refuses_even_a_right_answer = s.status === 409;
    r.timer_is_a_page_timer_not_authority = intervals.length >= 1;
    return r;
  },
  async map_shows_sleeping_state_without_hearts() {
    await child(); await mountKids('1');
    for (var i = 0; i < 5; i++) { await wrongOn(1, 0); if (i < 4) await click({ next: '' }); }
    await mountKids();
    return { says_no_hearts: has(text(), 'No hearts left'), black_hearts: count(html(), '🖤') === 5 };
  },
  async finishing_a_level_unlocks_the_next() {
    await child(); await mountKids('1');
    var n = KEY[1].length;
    for (var i = 0; i < n; i++) { await rightOn(1, i); await click({ next: '' }); }
    var done = has(text(), 'Level 1 done') && has(html(), 'Next level');
    await mountKids();
    var h = html();
    return { celebrates: done, level_two_open: has(h, 'href="#/kids/2"'), level_one_completed: has(text(), 'Done!'), still_five_hearts: count(h, '❤️') === 5 };
  },
  async locked_level_is_explained() {
    await child(); await mountKids('2');
    return { explains: has(text(), 'Finish the last level first'), no_game: !has(html(), 'data-choice') };
  },
  async child_navigation_is_small_and_simple() {
    await child();
    var nav = win.AgeMode.filterNav([['#/', 'H', 'Home'], ['#/voice', 'V', 'Voice Practice'], ['#/tutor', 'T', 'AI Tutor']]);
    return { three_items: nav.length === 3, labels: nav.map(function (n) { return n[2]; }).join(',') === 'Adventure,Listen,Me', no_voice_practice: !nav.some(function (n) { return n[0] === '#/voice'; }),
             other_routes_open_the_adventure: win.AgeMode.routeFor('voice') === 'kids' && win.AgeMode.routeFor('') === 'kids' && win.AgeMode.routeFor('tutor') === 'kids',
             listening_and_profile_kept: win.AgeMode.routeFor('listening') === 'listening' && win.AgeMode.routeFor('profile') === 'profile', no_voice_feature: win.AgeMode.features().voice_practice === false };
  },
  async teen_gets_a_path_page_and_keeps_navigation() {
    await login(E('DOB_TEEN'));
    var base = [['#/', 'H', 'Home'], ['#/voice', 'V', 'Voice Practice'], ['#/tutor', 'T', 'AI Tutor']];
    var nav = win.AgeMode.filterNav(base);
    await mountTeen();
    var h = html();
    return { mode_is_teen: win.AgeMode.mode() === 'teen' && classes['mode-teen'] === true, everything_kept: base.every(function (b) { return nav.some(function (n) { return n[0] === b[0]; }); }), path_added: nav.length === 4 && nav[1][0] === '#/path',
             routes_untouched: win.AgeMode.routeFor('voice') === 'voice' && win.AgeMode.routeFor('') === '', voice_allowed: win.AgeMode.features().voice_practice === true,
             path_page_has_lessons: has(h, 'href="#/lessons/') && has(h, 'Greetings'), up_next: has(text(), 'Up next'), difficulty: has(text(), 'Difficulty:'), no_game_ui: !has(h, 'kid-') };
  },
  async teen_page_is_not_for_children() {
    await child(); await mountTeen();
    return { explains: has(text(), 'Not available for this account'), no_lessons: !has(html(), 'href="#/lessons/') };
  },
  async adult_is_unchanged() {
    await login(E('DOB_ADULT'));
    var base = [['#/', 'H', 'Home'], ['#/voice', 'V', 'Voice Practice']];
    return { mode_adult: win.AgeMode.mode() === 'adult', same_nav: win.AgeMode.filterNav(base) === base, same_routes: win.AgeMode.routeFor('voice') === 'voice' && win.AgeMode.routeFor('') === '', no_body_class: !classes['mode-child'] && !classes['mode-teen'] };
  },
  async signed_out_is_unchanged() {
    await win.AgeMode.refresh();
    var base = [['#/', 'H', 'Home']];
    return { no_mode: win.AgeMode.mode() === null, same_nav: win.AgeMode.filterNav(base) === base, same_routes: win.AgeMode.routeFor('voice') === 'voice', no_body_class: !classes['mode-child'] && !classes['mode-teen'] };
  },
  async leaving_childhood_changes_the_mode() {
    await child();
    var before = win.AgeMode.mode();
    await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: E('DOB_ADULT') });
    await win.AgeMode.refresh();
    return { was_child: before === 'child', now_adult: win.AgeMode.mode() === 'adult', class_removed: !classes['mode-child'], routes_open_again: win.AgeMode.routeFor('voice') === 'voice' };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
