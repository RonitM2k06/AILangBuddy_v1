// Drives the real frontend/agemode.js and gamify.js (plus profile.js for the shared API helper) in JavaScriptCore
// (osascript) against a live test server. Timers are stubs; HTTP is real (via curl). Each scenario prints one line "## {json}"
// with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, KEY (answer key read from the test database), DOB_CHILD,
// DOB_TEEN, DOB_ADULT. Two browsers (cookie jars) are used: one per learner (A and B).
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO');
var KEY = E('KEY') ? JSON.parse(E('KEY')) : {};
var JAR = WORKDIR + '/cookies.txt', A_JAR = WORKDIR + '/a.txt', B_JAR = WORKDIR + '/b.txt';

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function sh(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}
var sent = [];
function fetch(url, opts) {
  opts = opts || {};
  sent.push({ method: opts.method || 'GET', url: url, body: opts.body || null });
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
var cache = {};
var rootEl = { innerHTML: '', onclick: null, onchange: null, querySelector: function (s) { return cache[s] || (cache[s] = { value: '', textContent: '' }); } };
var classes = {};
var document = { getElementById: function (id) { return id === 'rewards-root' || id === 'friends-root' ? rootEl : null; },
                 body: { contains: function () { return true; }, classList: { add: function (c) { classes[c] = true; }, remove: function () { for (var i = 0; i < arguments.length; i++) delete classes[arguments[i]]; } } } };
var tz = 'Asia/Kolkata';
var win = { setInterval: function () { return 1; }, clearInterval: function () {}, location: { hash: '' }, confirm: function () { return true; },
            Intl: { DateTimeFormat: function () { return { resolvedOptions: function () { return { timeZone: tz }; } }; } } };
var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/agemode.js'); load('frontend/gamify.js');

var tick = async function () { for (var i = 0; i < 200; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
var click = async function (d) { await rootEl.onclick({ target: { closest: function () { return { dataset: d }; } } }); await tick(); };
var api = win.LBApi.api;
var mountRewards = async function () { win.RewardsView.page(); await lastMount; await tick(); };
var mountFriends = async function () { win.FriendsView.page(); await lastMount; await tick(); };
function has(s, sub) { return s.indexOf(sub) >= 0; }
function count(s, sub) { return s.split(sub).length - 1; }
function as(jar) { JAR = jar; }
async function learner(jar, name, dob) {
  as(jar);
  await api('POST', '/api/auth/register', { email: 'g' + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com', password: 'ui-password-123', display_name: name, role: 'learner' });
  await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: dob });
  await win.AgeMode.refresh();
}
// answers n listening activities correctly by trying the options (wrong tries earn nothing)
async function solve(n) {
  var list = (await api('GET', '/api/listening')).data.activities, done = 0;
  for (var i = 0; i < list.length && done < n; i++) {
    var a = (await api('GET', '/api/listening/' + list[i].id)).data.activity;
    for (var j = 0; j < a.options.length; j++) {
      var r = await api('POST', '/api/listening/' + a.id + '/attempts', { option_id: a.options[j].id });
      if (r.data.correct) { done++; break; }
    }
  }
}
async function codeOf(jar) { as(jar); var r = await api('GET', '/api/social/friends'); return r.data.my_friend_code; }
async function befriend(requesterJar, otherJar) {
  var code = await codeOf(otherJar); as(requesterJar);
  await api('POST', '/api/social/friends/requests', { code: code });
  as(otherJar); var inc = (await api('GET', '/api/social/friends')).data.incoming[0].id;
  await api('POST', '/api/social/friends/requests/' + inc + '/accept');
  as(requesterJar);
}

var scenarios = {
  async rewards_signed_out() {
    await mountRewards();
    return { asks_to_sign_in: has(text(), 'Sign in to see rewards'), nothing_else: !has(html(), 'Level') };
  },
  async rewards_new_learner() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountRewards();
    var t = text();
    return { level_and_rank: has(t, '1 · Explorer'), zero_xp: has(t, '0 XP · 100 to level 2'), streak_zero: has(t, '🔥 0 days'), freezes: has(t, '❄️ 0 / 2'), explains_freezes: has(t, 'One is earned every 7 days'),
             confidence_note: has(t, 'Local Confidence still shows how ready you feel'), challenges_listed: has(t, 'Get 3 listening activities right') && !has(html(), 'data-claim'),
             achievements_locked: has(t, 'First lesson') && has(t, '🔒'), empty_history: has(t, 'to earn your first XP') };
  },
  async rewards_after_activity() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await solve(3); await mountRewards();
    var t = text(), h = html();
    return { xp: has(t, '15 XP'), streak_one_day: has(t, '🔥 1 day') && has(t, 'done for today'), claim_offered: has(h, 'data-claim='), listening_challenge_done: has(t, '3 / 3 · +15 XP'), recent_xp: has(t, '+5 · Listening activity') };
  },
  async claiming_a_challenge() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await solve(3); await mountRewards();
    var id = /data-claim="(\d+)"/.exec(html())[1];
    await click({ claim: id });
    var t = text();
    var again = await api('POST', '/api/gamification/challenges/' + id + '/claim');
    return { says_claimed: has(t, 'Reward claimed'), xp_now_30: has(t, '30 XP'), no_claim_button: !has(html(), 'data-claim='), shows_claimed_chip: has(t, 'Claimed ✓'), achievement_unlocked: has(t, '🏅'),
             a_replay_is_refused: again.status === 409 };
  },
  async the_page_never_sends_an_amount() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await solve(3); await mountRewards();
    var id = /data-claim="(\d+)"/.exec(html())[1];
    sent.length = 0;
    await click({ claim: id }); await click({ tz: '' });
    var posts = sent.filter(function (s) { return s.method !== 'GET'; });
    var bodies = posts.map(function (s) { return s.body || ''; }).join(' ');
    return { only_two_writes: posts.length === 2, claim_has_no_body: posts[0].body === null, no_xp_or_level_sent: !/xp|level|streak|freeze|score/i.test(bodies), timezone_only: posts[1].body === JSON.stringify({ timezone: 'Asia/Kolkata' }) };
  },
  async timezone_button() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountRewards(); await click({ tz: '' });
    return { saved: has(text(), 'Timezone saved'), shown: has(text(), 'timezone Asia/Kolkata') };
  },
  async a_child_gets_no_friends() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD')); await mountFriends();
    return { explains: has(text(), 'Not available for this account'), no_code: !has(html(), 'fr-mycode'), no_form: !has(html(), 'fr-code'),
             server_refuses: (await api('GET', '/api/social/friends')).status === 403 && (await api('POST', '/api/social/friends/requests', { code: 'ABCDEFGHJK' })).status === 403 };
  },
  async friends_signed_out() {
    await mountFriends();
    return { asks_to_sign_in: has(text(), 'Sign in to see friends') };
  },
  async friends_empty_page() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountFriends();
    var h = html();
    return { shows_my_code: /id="fr-mycode">[A-Z2-9]{10}</.test(h), no_friends: has(text(), 'No friends yet'), add_form: has(h, 'id="fr-code"') && has(h, 'data-add'), board_has_me: has(text(), '1. Aria (you)') };
  },
  async sending_a_request_and_accepting_it() {
    await learner(B_JAR, 'Bea', E('DOB_TEEN')); await learner(A_JAR, 'Aria', E('DOB_TEEN'));
    var code = await codeOf(B_JAR); as(A_JAR);
    await mountFriends(); cache['#fr-code'] = { value: code, textContent: '' };
    await click({ add: '' });
    var r = { sent_message: has(text(), 'Request sent'), waiting_list: has(text(), 'Waiting for an answer') && has(text(), 'Bea') };
    as(B_JAR); await mountFriends();
    r.addressee_sees_request = has(text(), 'Aria') && has(text(), 'wants to be friends');
    await click({ accept: /data-accept="(\d+)"/.exec(html())[1] });
    r.accepted = has(text(), 'You are now friends') && has(text(), 'My friends') && has(html(), 'data-remove=');
    as(A_JAR); await mountFriends();
    r.sender_sees_friend = has(text(), 'Bea') && has(html(), 'data-remove=');
    r.leaderboard_has_both = has(text(), 'Aria (you)') && has(text(), 'Bea');
    r.no_private_data = !has(html(), '@example.com') && !has(html(), 'date_of_birth');
    return r;
  },
  async rejecting_a_request() {
    await learner(B_JAR, 'Bea', E('DOB_TEEN')); await learner(A_JAR, 'Aria', E('DOB_TEEN'));
    var code = await codeOf(B_JAR); as(A_JAR); await api('POST', '/api/social/friends/requests', { code: code });
    as(B_JAR); await mountFriends();
    await click({ reject: /data-reject="(\d+)"/.exec(html())[1] });
    return { request_gone: !has(text(), 'wants to be friends'), no_friend: has(text(), 'No friends yet') };
  },
  async a_wrong_code_gets_a_calm_message() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountFriends(); cache['#fr-code'] = { value: 'WRONGCODE1', textContent: '' };
    await click({ add: '' });
    return { message: has(text(), 'did not work') };
  },
  async an_empty_code_is_not_sent() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountFriends(); cache['#fr-code'] = { value: ' ', textContent: '' };
    sent.length = 0; await click({ add: '' });
    return { asks_for_code: has(cache['#fr-msg'].textContent, "Type your friend's code"), nothing_sent: sent.length === 0 };
  },
  async removing_a_friend() {
    await learner(B_JAR, 'Bea', E('DOB_TEEN')); await learner(A_JAR, 'Aria', E('DOB_TEEN')); await befriend(A_JAR, B_JAR);
    await mountFriends();
    var had = has(html(), 'data-remove=');
    await click({ remove: /data-remove="(\d+)"/.exec(html())[1] });
    return { had_friend: had, now_none: has(text(), 'No friends yet') && !has(text(), 'Bea') };
  },
  async leaderboard_period_toggle() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await solve(2); await mountFriends();
    var week = has(html(), 'data-period="week"') && /btn-primary btn-sm" data-period="week"/.test(html());
    sent.length = 0; await click({ period: 'all' });
    return { starts_on_week: week, switches: /btn-primary btn-sm" data-period="all"/.test(html()), asked_server: sent.some(function (s) { return s.url.indexOf('period=all') >= 0; }), shows_xp: has(text(), '10 XP') };
  },
  async navigation_is_not_changed_for_children_or_parents() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD'));
    var base = [['#/', 'H', 'Home'], ['#/rewards', 'R', 'Rewards'], ['#/friends', 'F', 'Friends']];
    var child = win.AgeMode.filterNav(base);
    var r = { child_nav_is_still_three_items: child.length === 3 && child.map(function (n) { return n[2]; }).join(',') === 'Adventure,Listen,Me',
              child_routes_open_the_adventure: win.AgeMode.routeFor('rewards') === 'kids' && win.AgeMode.routeFor('friends') === 'kids' };
    as(B_JAR);
    await api('POST', '/api/auth/register', { email: 'par' + Date.now() + '@example.com', password: 'ui-password-123', display_name: 'Pat', role: 'parent' });
    await win.AgeMode.refresh();
    var parent = win.AgeMode.filterNav(base);
    r.parent_does_not_get_learner_pages = !parent.some(function (n) { return n[0] === '#/rewards' || n[0] === '#/friends'; }) && parent.some(function (n) { return n[0] === '#/parent'; });
    return r;
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
