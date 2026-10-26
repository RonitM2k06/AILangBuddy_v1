// Drives the real frontend/agemode.js and parent.js (plus profile.js for the shared API helper) in JavaScriptCore
// (osascript) against a live test server. Timers are stubs; HTTP is real (via curl). Each scenario prints one line "## {json}"
// with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, KEY (answer key read from the test database), DOB_CHILD,
// DOB_TEEN, DOB_ADULT. Two browsers (cookie jars) are used: one for the child, one for the parent.
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO');
var KEY = E('KEY') ? JSON.parse(E('KEY')) : {};
var JAR = WORKDIR + '/cookies.txt', CHILD_JAR = WORKDIR + '/child.txt', PARENT_JAR = WORKDIR + '/parent.txt', PARENT2_JAR = WORKDIR + '/parent2.txt';

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
var cache = {};
var rootEl = { innerHTML: '', onclick: null, onchange: null, querySelector: function (s) { return cache[s] || (cache[s] = { value: '', textContent: '' }); } };
var classes = {};
var document = { getElementById: function (id) { return id === 'parent-root' ? rootEl : null; },
                 body: { contains: function () { return true; }, classList: { add: function (c) { classes[c] = true; }, remove: function () { for (var i = 0; i < arguments.length; i++) delete classes[arguments[i]]; } } } };
var win = { setInterval: function () { return 1; }, clearInterval: function () {}, location: { hash: '' }, confirm: function () { return true; } };
var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/agemode.js'); load('frontend/parent.js');

var tick = async function () { for (var i = 0; i < 120; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
var clickId = async function (id) { await rootEl.onclick({ target: { closest: function () { return { id: id }; } } }); await tick(); };
var api = win.LBApi.api;
var mountList = async function () { win.ParentView.page(); await lastMount; await tick(); };
var mountChild = async function (id) { win.ParentView.page(String(id)); await lastMount; await tick(); };
function has(s, sub) { return s.indexOf(sub) >= 0; }
function as(jar) { JAR = jar; }
async function register(role, jar, dob) {
  as(jar);
  var email = 'u' + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com';
  await api('POST', '/api/auth/register', { email: email, password: 'ui-password-123', display_name: role === 'parent' ? 'Pat Parent' : 'Kiki', role: role });
  if (dob) await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: dob });
  return email;
}
async function child(dob) { await register('learner', CHILD_JAR, dob); }
async function parent(jar) { await register('parent', jar || PARENT_JAR); await win.AgeMode.refresh(); }
async function codeFromChild() { as(CHILD_JAR); var r = await api('POST', '/api/profile/parent-link-code'); as(PARENT_JAR); return r.data.code; }
async function linkViaApi(jar) { var code = await codeFromChild(); as(jar || PARENT_JAR); var r = await api('POST', '/api/parent/children', { code: code }); return r.data.child.id; }
async function childPost(path, body) { as(CHILD_JAR); var r = await api('POST', path, body); as(PARENT_JAR); return r; }

var scenarios = {
  async signed_out() {
    await mountList();
    return { asks_to_sign_in: has(text(), 'Sign in as a parent'), no_add_form: !has(html(), 'pa-code') };
  },
  async a_learner_is_told_this_is_for_parents() {
    await child(E('DOB_TEEN')); as(CHILD_JAR); await mountList();
    return { explains: has(text(), 'Parent accounts only'), no_children: !has(html(), 'href="#/parent/') };
  },
  async empty_list_offers_to_add_a_child() {
    await parent(); await mountList();
    return { says_none: has(text(), 'No children linked yet'), add_form: has(html(), 'id="pa-code"') && has(html(), 'id="pa-add"'), explains_where_the_code_comes_from: has(text(), 'Make a code') };
  },
  async linking_with_the_childs_code() {
    await child(E('DOB_TEEN')); await parent(); var code = await codeFromChild();
    await mountList(); cache['#pa-code'] = { value: code, textContent: '' };
    await clickId('pa-add');
    var h = html();
    return { child_listed: has(text(), 'Kiki') && has(h, 'href="#/parent/'), age_group_and_level_shown: has(text(), '10–17 · hi') && has(text(), 'A1'), no_email_shown: !has(h, '@example.com') };
  },
  async a_wrong_code_gives_a_calm_message() {
    await parent(); await mountList(); cache['#pa-code'] = { value: 'WRONGCODE1', textContent: '' };
    await clickId('pa-add');
    return { message: has(cache['#pa-msg'].textContent, 'did not work'), still_empty: has(text(), 'No children linked yet') };
  },
  async an_empty_code_is_not_sent() {
    await parent(); await mountList(); cache['#pa-code'] = { value: '  ', textContent: '' };
    await clickId('pa-add');
    return { asks_for_code: has(cache['#pa-msg'].textContent, 'Type the code') };
  },
  async dashboard_shows_the_childs_activity() {
    await child(E('DOB_CHILD')); await parent(); var id = await linkViaApi();
    await childPost('/api/kids/levels/1/answers', { question: 1, choice: KEY[1][0][2] });          // one wrong answer
    await childPost('/api/kids/levels/1/answers', { question: 2, choice: KEY[1][1][1] });          // one right answer
    await mountChild(id);
    var h = html(), t = text();
    return { name_and_group: has(t, 'Kiki') && has(t, 'Under 10 · learning hi · level A1'), stats: has(t, 'Listening answers') && has(t, '2') && has(t, '50% right'), recent_wrong_and_right: has(t, '❌ listening') && has(t, '✅ listening'),
             sections: has(t, 'Areas to improve') && has(t, 'Confidence') && has(t, 'Recent activity') && has(t, 'Pronunciation'), nothing_to_improve_yet: has(t, 'Nothing needs extra practice'),
             no_private_data: !has(h, '@example.com') && !has(h, 'date_of_birth') && !has(t, 'transcript') };
  },
  async child_voice_cannot_be_turned_on() {
    await child(E('DOB_CHILD')); await parent(); var id = await linkViaApi(); await mountChild(id);
    return { explained: has(text(), "can't be turned on"), no_toggle: !has(html(), 'pa-voice') };
  },
  async parent_can_switch_a_teens_voice_off_and_on() {
    await child(E('DOB_TEEN')); await parent(); var id = await linkViaApi(); await mountChild(id);
    var r = { starts_unrestricted: has(html(), 'id="pa-voice"') && !has(html(), 'checked'), child_can_start_voice: (await childPost('/api/speaking/sessions', {})).status === 201 };
    await rootEl.onchange({ target: { id: 'pa-voice', checked: true } }); await tick();
    r.shows_off = has(html(), 'checked') && has(text(), 'currently off');
    r.server_blocks_the_child = (await childPost('/api/speaking/sessions', {})).status === 403;
    await rootEl.onchange({ target: { id: 'pa-voice', checked: false } }); await tick();
    r.back_on = !has(text(), 'currently off');
    r.child_allowed_again = (await childPost('/api/speaking/sessions', {})).status === 201;
    return r;
  },
  async a_failed_control_change_is_reported() {
    await child(E('DOB_TEEN')); await parent(); var id = await linkViaApi(); await mountChild(id);
    await api('DELETE', '/api/parent/children/' + id);                                              // the link vanishes under the page
    await rootEl.onchange({ target: { id: 'pa-voice', checked: true } }); await tick();
    return { reported: cache['#pa-ctl-msg'].textContent.length > 0 && cache['#pa-ctl-msg'].textContent !== 'Saved ✓' };
  },
  async unknown_child() {
    await parent(); await mountChild(99999);
    return { not_found: has(text(), 'Child not found'), nothing_shown: !has(html(), 'pa-voice') };
  },
  async another_parents_child_looks_like_an_unknown_child() {
    await child(E('DOB_TEEN')); await parent(); var id = await linkViaApi();
    await register('parent', PARENT2_JAR); as(PARENT2_JAR); await mountChild(id);
    return { not_found: has(text(), 'Child not found'), no_name: !has(text(), 'Kiki'), no_controls: !has(html(), 'pa-voice') };
  },
  async stop_following() {
    await child(E('DOB_TEEN')); await parent(); var id = await linkViaApi(); await mountChild(id);
    await clickId('pa-unlink');
    as(PARENT_JAR); var list = await api('GET', '/api/parent/children');
    return { link_removed: list.data.children.length === 0, back_to_the_list: win.location.hash === '#/parent' };
  },
  async parent_navigation() {
    await parent();
    var base = [['#/', 'H', 'Home'], ['#/tutor', 'T', 'AI Tutor']];
    var nav = win.AgeMode.filterNav(base);
    return { mode_parent: win.AgeMode.mode() === 'parent', family_page_added: nav.length === 3 && nav[1][0] === '#/parent', everything_kept: base.every(function (b) { return nav.some(function (n) { return n[0] === b[0]; }); }),
             no_child_or_teen_styling: !classes['mode-child'] && !classes['mode-teen'], routes_untouched: win.AgeMode.routeFor('voice') === 'voice' && win.AgeMode.routeFor('') === '' };
  },
  async learners_are_unaffected_by_the_parent_entry() {
    await child(E('DOB_TEEN')); await win.AgeMode.refresh();
    var base = [['#/', 'H', 'Home']];
    var nav = win.AgeMode.filterNav(base);
    return { teen_mode: win.AgeMode.mode() === 'teen', no_parent_item: !nav.some(function (n) { return n[0] === '#/parent'; }), path_item: nav.some(function (n) { return n[0] === '#/path'; }) };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
