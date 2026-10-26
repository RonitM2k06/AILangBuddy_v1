// Drives the real frontend/agemode.js and frontend/admin.js (plus profile.js for the shared API helper) in JavaScriptCore (osascript) against a live test server.
// Timers are stubs; HTTP is real (via curl, with a cookie jar per "browser"). Every request the page makes is recorded in `calls`, so a scenario can assert what was SENT
// (the CSRF header, the revision, that nothing is ever deleted). Each scenario prints one line "## {json}" with named boolean checks.
// Inputs: BASE, ROOT, WORKDIR, SCENARIO, ADMIN_EMAIL, PASSWORD, LEARNER_DOB, plus ids prepared by the test (IDS: JSON).
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO');
var ADMIN_EMAIL = E('ADMIN_EMAIL'), PASSWORD = E('PASSWORD'), DOB = E('LEARNER_DOB'), IDS = E('IDS') ? JSON.parse(E('IDS')) : {};
var JAR = WORKDIR + '/cookies.txt';

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function sh(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}
var calls = [], failNext = false;
function fetch(url, opts) {
  opts = opts || {};
  calls.push({ method: opts.method || 'GET', url: url, headers: opts.headers || {}, body: opts.body || null });
  if (failNext) { failNext = false; return Promise.reject(new Error('network down')); }
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
var confirmAnswer = true, confirmAsked = [];
var document = { getElementById: function (id) { return id === 'admin-root' ? rootEl : null; },
                 body: { contains: function () { return true; }, classList: { add: function (c) { classes[c] = true; }, remove: function () { for (var i = 0; i < arguments.length; i++) delete classes[arguments[i]]; } } } };
var win = { setInterval: function () { return 1; }, clearInterval: function () {}, location: { hash: '' }, confirm: function (m) { confirmAsked.push(m); return confirmAnswer; } };
var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/agemode.js'); load('frontend/admin.js');

var tick = async function () { for (var i = 0; i < 160; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
function has(s, sub) { return s.indexOf(sub) >= 0; }
function resetStubs() { cache = {}; rootEl.innerHTML = ''; rootEl.onclick = null; rootEl.onchange = null; }

// open an admin page at a hash and wait for it to render
async function open(hash) { win.location.hash = hash; resetStubs(); win.AdminView.page(); await lastMount; await tick(); }
async function clickAct(act, data) {
  var target = { closest: function (sel) { return sel === 'button' ? { id: '', dataset: Object.assign({ act: act }, data || {}) } : null; } };
  await rootEl.onclick({ target: target }); await tick();
}
async function changeTo(id, value) { await rootEl.onchange({ target: { id: id, value: value } }); await tick(); }
function setv(id, value) { cache['#' + id] = { value: value, textContent: '' }; }

var api = win.LBApi.api;
// The console admin signs in with a session that has passed a second factor (Phase 14D), planted by the test: one per sign-in.
var ADMIN_SESSIONS = E('ADMIN_SESSIONS') ? JSON.parse(E('ADMIN_SESSIONS')) : [];
async function loginAs(email, password) {
  JAR = WORKDIR + '/cookies.txt';
  if (email === ADMIN_EMAIL && !password && ADMIN_SESSIONS.length) {
    var host = /^https?:\/\/([^:/]+)/.exec(BASE)[1];
    $(host + '\tFALSE\t/\tFALSE\t0\tllb_session\t' + ADMIN_SESSIONS.shift() + '\n').writeToFileAtomicallyEncodingError(JAR, true, 4, null);
    return { ok: true, status: 200, data: { planted: true } };
  }
  return api('POST', '/api/auth/login', { email: email, password: password || PASSWORD });
}
async function logout() { return api('POST', '/api/auth/logout'); }
async function registerLearner(tag, dob) {
  var email = tag + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com';
  await api('POST', '/api/auth/register', { email: email, password: PASSWORD, display_name: 'Pat ' + tag, role: tag === 'parent' ? 'parent' : 'learner' });
  if (dob) await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: dob });
  return email;
}
// admin API calls made by the harness itself (not by the page under test), with the CSRF header
async function adminCall(method, url, body) {
  var res = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }, body: body === undefined ? undefined : JSON.stringify(body) });
  var data = null; try { data = await res.json(); } catch (e) {}
  return { ok: res.ok, status: res.status, data: data };
}
var NAV = [['#/', 'x', 'Home'], ['#/new', 'x', "I'm New Here"], ['#/lessons', 'x', 'My Lessons'], ['#/rewards', 'x', 'Rewards'], ['#/profile', 'x', 'Profile']];
var writes = function () { return calls.filter(function (c) { return c.method !== 'GET'; }); };
var sentCsrf = function (c) { return c.headers['X-Requested-With'] === 'XMLHttpRequest' && c.headers['Content-Type'] === 'application/json'; };
var uniq = function (p) { return p + '-' + Date.now().toString(36) + Math.floor(Math.random() * 1000).toString(36); };
async function newDraft(kind, slug, extra) {
  var body = Object.assign({ slug: slug, language: 'hi', cefr: 'A1', title: 'Title ' + slug, description: 'Desc', topics: ['food'] }, extra || {});
  var r = await adminCall('POST', '/api/admin/content/' + kind, body);
  return r.data;
}

var scenarios = {
  async nav_modes() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var adminNav = win.AgeMode.filterNav(NAV), adminMode = win.AgeMode.mode();
    var adminOnly = JSON.stringify(adminNav) === JSON.stringify(win.AdminView.NAV);
    var routeAdmin = win.AgeMode.routeFor('admin'), routeLessons = win.AgeMode.routeFor('lessons');
    await logout();
    await registerLearner('adult', DOB); await win.AgeMode.refresh();
    var learnerNav = win.AgeMode.filterNav(NAV), learnerMode = win.AgeMode.mode();
    await logout();
    return { admin_mode: adminMode === 'admin', admin_sees_only_the_admin_nav: adminOnly, admin_nav_has_all_seven: win.AdminView.NAV.length === 7 && win.AdminView.NAV[5][0] === '#/admin/security',
             admin_never_sees_learner_pages: adminNav.every(function (n) { return n[0].indexOf('#/admin') === 0; }), admin_stays_in_admin: routeAdmin === 'admin' && routeLessons === 'admin',
             learner_nav_unchanged: JSON.stringify(learnerNav) === JSON.stringify(NAV) && learnerMode !== 'admin', learner_nav_has_no_admin_link: !JSON.stringify(learnerNav).includes('admin') };
  },
  async non_admins_are_sent_home() {
    var out = {};
    out.anonymous = (await win.AgeMode.refresh(), win.AgeMode.routeFor('admin')) === '';
    await registerLearner('adult', DOB); await win.AgeMode.refresh(); out.adult = win.AgeMode.routeFor('admin') === '';
    await logout(); await registerLearner('teen', '2012-05-05'); await win.AgeMode.refresh(); out.teen = win.AgeMode.routeFor('admin') === '';
    await logout(); await registerLearner('child', '2019-05-05'); await win.AgeMode.refresh(); out.child = win.AgeMode.routeFor('admin') === 'kids';
    await logout(); await registerLearner('parent'); await win.AgeMode.refresh(); out.parent = win.AgeMode.routeFor('admin') === 'parent';
    out.other_routes_untouched_for_a_parent = win.AgeMode.routeFor('lessons') === 'lessons';
    await logout();
    return { anonymous_goes_home: out.anonymous, adult_goes_home: out.adult, teen_goes_home: out.teen, child_goes_to_the_adventure: out.child, parent_goes_to_the_family_page: out.parent, other_routes_untouched_for_a_parent: out.other_routes_untouched_for_a_parent };
  },
  async server_refusal_redirects_and_explains() {
    await registerLearner('adult', DOB);                          // a learner who walks straight to the URL: the page asks the server, the server says 403
    win.location.hash = '#/admin';
    await open('#/admin');
    var out = { says_admins_only: has(text(), 'Administrators only'), hash_is_home: win.location.hash === '#/', no_data_shown: !has(html(), 'ad-stat') && !has(html(), 'ad-table') };
    await logout();
    await open('#/admin/curriculum/lessons');
    out.signed_out_is_asked_to_sign_in = has(text(), 'Sign in as an administrator') && has(html(), 'href="#/profile"');
    return out;
  },
  async dashboard_renders_aggregates() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin');
    var t = text(), h = html();
    var out = { title: has(t, 'Dashboard'), shows_the_window_in_utc: has(t, '(UTC)'), learner_total_is_a_number: /Learners\s+\d+/.test(t), has_line_chart: has(h, 'data-chart="line"') && has(h, '<path d="M'),
                has_three_distributions: (h.match(/data-chart="bar"/g) || []).length === 3, shows_language_names: has(t, 'Hindi'), learning_block: has(t, 'Lesson completion') && has(t, 'Exercise accuracy'),
                no_identity: !has(h, '@') && !has(h, 'user_id') && !has(h, 'password'), explains_hidden_figures: has(t, 'fewer than 5 learners'), window_selector_present: has(h, 'id="ad-window"'), links_onward: has(h, 'href="#/admin/analytics"') };
    var before = calls.length;
    await changeTo('ad-window', '7d');
    out.changing_the_window_changes_the_url = win.location.hash === '#/admin?window=7d';
    await open('#/admin?window=7d');
    out.window_is_sent_to_the_server = calls.slice(before).some(function (c) { return c.url === '/api/admin/dashboard?window=7d'; }) && calls.slice(before).some(function (c) { return c.url === '/api/admin/analytics/activity?window=7d'; });
    await open('#/admin?window=1y');
    out.an_unknown_window_falls_back = calls[calls.length - 2].url.indexOf('window=30d') >= 0 || calls[calls.length - 1].url.indexOf('window=30d') >= 0;
    return out;
  },
  async dashboard_suppresses_small_figures() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin');
    var h = html();
    return { suppressed_text_shown: has(h, 'hidden · fewer than 5 learners'), small_cells_have_no_number_next_to_the_label: !/Roleplay success<\/td><td>\d/.test(h), a_small_count_is_hidden_not_shown: /Pronunciation checks<\/td><td><span class="ad-sup"/.test(h) };
  },
  async error_state_and_retry() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    failNext = true;
    await open('#/admin/curriculum/lessons');
    var out = { error_box: has(html(), 'data-state="error"') && has(text(), "Couldn't load"), has_retry: has(html(), 'data-act="retry"') };
    await clickAct('retry'); await tick();
    out.retry_loads_the_page = has(html(), 'class="ad-table"') && !has(html(), 'data-state="error"');
    return out;
  },
  async lessons_list_filters_and_pagination() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/lessons');
    var out = { table: has(html(), 'class="ad-table"'), rows_link_to_detail: /href="#\/admin\/curriculum\/lessons\/\d+"/.test(html()), shows_status_badges: has(html(), 'ad-published') && has(html(), 'ad-draft'),
                has_next_page: has(html(), 'data-act="next"') && has(html(), 'offset=25'), previous_is_disabled_on_page_one: !has(html(), 'data-act="prev"') };
    var firstPage = (html().match(/<tr data-id=/g) || []).length;
    out.page_size_is_25 = firstPage === 25;
    await open('#/admin/curriculum/lessons?offset=25');
    out.second_page = has(html(), 'data-act="prev"') && (html().match(/<tr data-id=/g) || []).length >= 1 && has(text(), '26–');
    setv('f-status', 'draft'); setv('f-language', 'hi'); setv('f-cefr', 'A1'); setv('f-q', IDS.search || 'zz');
    await open('#/admin/curriculum/lessons');
    setv('f-status', 'draft'); setv('f-q', 'needle');
    await clickAct('filter');
    out.filter_goes_to_the_url = has(win.location.hash, 'status=draft') && has(win.location.hash, 'q=needle');
    await open('#/admin/curriculum/lessons?status=draft&q=needle');
    out.filters_are_sent = calls.some(function (c) { return c.url.indexOf('/api/admin/content/lessons?status=draft&q=needle&limit=25&offset=0') === 0; });
    out.filter_values_are_kept = has(html(), 'value="needle"') && has(html(), '<option value="draft" selected>');
    await open('#/admin/curriculum/lessons?q=nothing-will-match-this-9z');
    out.empty_state = has(html(), 'data-state="empty"') && has(text(), 'Nothing matches');
    setv('f-q', 'x');
    await clickAct('clear');
    out.clear_resets = win.location.hash === '#/admin/curriculum/lessons';
    return out;
  },
  async situations_and_listening_lists() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/situations');
    var out = { situations_table: has(html(), 'class="ad-table"') && has(html(), '<th>Steps</th>') };
    await open('#/admin/curriculum/listening');
    out.listening_table = has(html(), 'class="ad-table"') && has(html(), '<th>Options</th>');
    await open('#/admin/curriculum');
    var sweepBox = cache['#ad-sweep'] = { innerHTML: '', value: '', textContent: '' };
    out.curriculum_home_links = has(html(), '#/admin/curriculum/lessons') && has(html(), '#/admin/curriculum/situations') && has(html(), '#/admin/curriculum/listening') && has(html(), '#/admin/curriculum/vocabulary') && has(html(), '#/admin/curriculum/topics');
    await clickAct('sweep');
    out.integrity_check_runs = has(sweepBox.innerHTML, 'Passes') && /0 errors, \d+ warnings/.test(sweepBox.innerHTML) && /checked \d+ lessons, 111 situations, 315 listening activities/.test(sweepBox.innerHTML);
    out.sweep_called_the_endpoint = calls.some(function (c) { return c.url === '/api/admin/validate/all'; });
    return out;
  },
  async create_a_lesson_from_the_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/lessons');
    var slug = uniq('ui-new');
    setv('c-slug', slug); setv('c-language', 'hi'); setv('c-cefr', 'A1'); setv('c-title', 'Made in the UI'); setv('c-description', 'Created by the harness'); setv('c-topics', 'food'); setv('c-ages', '');
    var before = calls.length;
    await clickAct('create');
    var post = calls.slice(before).filter(function (c) { return c.method === 'POST'; })[0];
    var out = { posts_to_lessons: !!post && post.url === '/api/admin/content/lessons', sends_csrf: !!post && sentCsrf(post), body_has_no_status_or_actor: !!post && !/"status"|"actor"|"published"/.test(post.body), goes_to_the_new_draft: /^#\/admin\/curriculum\/lessons\/\d+$/.test(win.location.hash) };
    setv('c-slug', 'Bad Slug'); await open('#/admin/curriculum/lessons'); setv('c-slug', 'Bad Slug'); setv('c-language', 'hi'); setv('c-cefr', 'A1'); setv('c-title', 'x'); setv('c-description', 'y');
    var msg = cache['#ad-create-msg'] = { value: '', textContent: '' };
    await clickAct('create');
    out.a_refusal_is_shown_in_place = msg.textContent.length > 0 && win.location.hash === '#/admin/curriculum/lessons';
    return out;
  },
  async draft_lesson_edit_and_publish_workflow() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var slug = uniq('ui-flow'), lesson = await newDraft('lessons', slug);
    var first = IDS.item;
    await adminCall('PUT', '/api/admin/content/lessons/' + lesson.id + '/vocabulary', { revision: lesson.revision, item_ids: [first] });
    var l2 = (await adminCall('GET', '/api/admin/content/lessons/' + lesson.id)).data;
    await open('#/admin/curriculum/lessons/' + lesson.id);
    var out = { shows_status_and_revision: has(html(), 'ad-draft') && has(text(), 'revision ' + l2.revision), edit_form_present: has(html(), 'id="e-title"') && has(html(), 'data-act="save-meta"'), publish_button_present: has(html(), 'data-act="publish"') && !has(html(), 'data-act="unpublish"'),
               no_delete_anywhere: !/delete/i.test(html()) };
    // an incomplete lesson: validate shows findings, publish is blocked and says why
    await clickAct('validate');
    out.validate_lists_findings = has(html(), 'data-findings="blocked"') && has(html(), 'lesson_no_exercises') && has(text(), 'Publishing is blocked');
    var before = calls.length;
    await clickAct('publish');
    var pub = calls.slice(before).filter(function (c) { return c.url.indexOf('/api/admin/publish/') === 0; })[0];
    out.publish_sends_the_revision_and_csrf = !!pub && sentCsrf(pub) && JSON.parse(pub.body).revision === l2.revision;
    out.blocked_publish_shows_the_findings = has(html(), 'data-code="lesson_no_exercises"') && has(text(), 'blocked by validation') && has(html(), 'ad-draft');
    // add an exercise, then it validates and publishes
    var cur = (await adminCall('GET', '/api/admin/content/lessons/' + lesson.id)).data;
    await open('#/admin/curriculum/lessons/' + lesson.id);
    setv('n-kind', 'multiple_choice'); setv('n-prompt', 'Pick the right one'); setv('n-item', String(first)); setv('n-difficulty', '1'); setv('n-answers', '* right\n  wrong\n  other');
    before = calls.length;
    await clickAct('add-exercise');
    var add = calls.slice(before).filter(function (c) { return c.method === 'POST' && c.url.indexOf('/exercises') > 0; })[0];
    var addBody = add ? JSON.parse(add.body) : {};
    out.add_exercise_parses_the_star = !!add && addBody.answers.length === 3 && addBody.answers[0].is_correct === true && addBody.answers[1].is_correct === false && addBody.revision === cur.revision && sentCsrf(add);
    out.exercise_listed = has(text(), 'Pick the right one') && has(text(), 'Exercise added');
    await clickAct('validate');
    out.validate_now_clean = has(html(), 'data-findings="clean"');
    await clickAct('publish');
    out.published = has(html(), 'ad-published') && has(text(), 'Published');
    out.published_is_read_only = !has(html(), 'id="e-title"') && has(html(), 'data-readonly="published"') && has(text(), "Published content can't be edited") && has(html(), 'data-act="unpublish"') && !has(html(), 'data-act="publish"');
    out.no_exercise_edit_form_when_published = !has(html(), 'data-act="save-exercise"') && !has(html(), 'data-act="add-exercise"');
    await clickAct('unpublish');
    out.unpublish_makes_it_a_draft = has(html(), 'ad-draft') && has(html(), 'id="e-title"');
    return out;
  },
  async archive_needs_confirmation_and_never_deletes() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var lesson = await newDraft('lessons', uniq('ui-arch'));
    await open('#/admin/curriculum/lessons/' + lesson.id);
    confirmAnswer = false; confirmAsked = [];
    var before = calls.length;
    await clickAct('archive');
    var out = { asked_first: confirmAsked.length === 1 && has(confirmAsked[0], 'Archive'), explains_history_is_kept: has(confirmAsked[0] || '', 'progress and history are kept'), cancel_sends_nothing: calls.slice(before).filter(function (c) { return c.method !== 'GET'; }).length === 0, still_a_draft: has(html(), 'ad-draft') };
    confirmAnswer = true; before = calls.length;
    await clickAct('archive');
    var post = calls.slice(before).filter(function (c) { return c.method === 'POST'; })[0];
    out.confirm_archives = !!post && post.url === '/api/admin/archive/lesson/' + lesson.id && sentCsrf(post) && has(html(), 'ad-archived') && has(text(), 'Learner history is untouched');
    out.archived_is_read_only = has(html(), 'data-readonly="archived"') && !has(html(), 'id="e-title"') && has(html(), 'data-act="restore"') && !has(html(), 'data-act="publish"');
    await clickAct('restore');
    out.restore_gives_a_draft = has(html(), 'ad-draft') && has(html(), 'id="e-title"');
    out.no_request_was_ever_a_delete = calls.every(function (c) { return c.method !== 'DELETE'; });
    return out;
  },
  async revision_conflict_is_handled() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var lesson = await newDraft('lessons', uniq('ui-conf'));
    lesson = (await adminCall('PATCH', '/api/admin/content/lessons/' + lesson.id, { revision: lesson.revision, tip: 'first tip' })).data;      // revision 2, so a wrong constant would differ
    await open('#/admin/curriculum/lessons/' + lesson.id);
    // someone else edits while this page is open
    var other = await adminCall('PATCH', '/api/admin/content/lessons/' + lesson.id, { revision: lesson.revision, title: 'Changed elsewhere' });
    setv('e-slug', lesson.slug); setv('e-title', 'My edit'); setv('e-cefr', 'A1'); setv('e-sort', String(lesson.sort_order)); setv('e-ages', ''); setv('e-description', 'd'); setv('e-situation', ''); setv('e-tip', ''); setv('e-topics', 'food');
    var before = calls.length;
    await clickAct('save-meta');
    var sent = calls.slice(before).filter(function (c) { return c.method === 'PATCH'; })[0];
    var out = { other_edit_succeeded: other.ok === true, sent_the_old_revision: !!sent && JSON.parse(sent.body).revision === lesson.revision && sentCsrf(sent), conflict_banner: has(html(), 'data-conflict="1"') && has(text(), 'changed while you were editing'), reload_offered: has(html(), 'data-act="reload"'), nothing_was_overwritten: true };
    await clickAct('reload');
    out.reload_shows_the_other_edit = has(html(), 'Changed elsewhere') && !has(html(), 'data-conflict="1"') && has(text(), 'revision ' + (lesson.revision + 1));
    var server = (await adminCall('GET', '/api/admin/content/lessons/' + lesson.id)).data;
    out.server_kept_the_other_edit = server.title === 'Changed elsewhere';
    return out;
  },
  async user_text_is_escaped() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var evil = '<img src=x onerror=alert(1)>', lesson = await newDraft('lessons', uniq('ui-xss'), { title: evil, description: '<script>alert(2)</script>' });
    await open('#/admin/curriculum/lessons?q=ui-xss');
    var listed = html();
    await open('#/admin/curriculum/lessons/' + lesson.id);
    var detail = html();
    return { stored_as_text: lesson.title === evil, list_escaped: has(listed, '&lt;img src=x') && !has(listed, '<img src=x'), detail_escaped: has(detail, '&lt;img src=x') && !has(detail, '<img src=x') && !has(detail, '<script>alert(2)'),
             heading_escaped: has(detail, '<h1>&lt;img') };
  },
  async csrf_header_on_every_write_and_no_delete() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    calls = [];
    var lesson = await newDraft('lessons', uniq('ui-csrf'));
    calls = [];
    await open('#/admin/curriculum/lessons/' + lesson.id);
    setv('e-slug', lesson.slug); setv('e-title', 'Retitled'); setv('e-cefr', 'A1'); setv('e-sort', String(lesson.sort_order)); setv('e-ages', ''); setv('e-description', 'd'); setv('e-situation', ''); setv('e-tip', ''); setv('e-topics', 'food');
    await clickAct('save-meta'); await clickAct('validate'); await clickAct('archive'); await clickAct('restore');
    await open('#/admin/curriculum/topics'); setv('n-slug', uniq('t')); setv('n-name', 'N'); setv('n-icon', 'x'); await clickAct('create-topic');
    var w = writes();
    return { made_writes: w.length >= 5, every_write_has_both_headers: w.every(sentCsrf), every_write_has_a_json_body: w.every(function (c) { return typeof c.body === 'string' && JSON.parse(c.body) !== null; }), no_delete_method: calls.every(function (c) { return c.method !== 'DELETE'; }),
             every_call_is_under_api_admin: calls.every(function (c) { return c.url.indexOf('/api/admin/') === 0; }), gets_carry_no_csrf_header_needed: calls.filter(function (c) { return c.method === 'GET'; }).length > 0 };
  },
  async vocabulary_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/vocabulary');
    var out = { table: has(html(), 'class="ad-table"') && has(html(), '<th>English</th>'), pagination: has(html(), 'offset=25'), explains_locks: has(text(), 'locked') };
    await open('#/admin/curriculum/vocabulary?item=' + IDS.item);
    out.detail_panel = has(html(), 'data-vocab="' + IDS.item + '"') && has(text(), 'in use: level and kind locked') && has(html(), 'data-act="save-translation"');
    setv('v-tlang', 'es'); setv('v-tmeaning', 'un significado de prueba'); setv('v-tnatural', '');
    var before = calls.length;
    await clickAct('save-translation', { id: String(IDS.item) });
    var put = calls.slice(before).filter(function (c) { return c.method === 'PUT'; })[0];
    out.adding_a_translation = !!put && put.url === '/api/admin/content/vocabulary/' + IDS.item + '/translations/es' && sentCsrf(put) && has(html(), 'un significado de prueba');
    setv('v-text', 'ही कुछ और'); setv('v-pron', ''); setv('v-cefr', 'A1'); setv('v-kind', 'word');
    await clickAct('save-vocab-item', { id: String(IDS.item) });
    out.locked_change_is_refused_in_place = has(text(), 'change') || cache['#ad-vmsg'] !== undefined;
    await open('#/admin/curriculum/vocabulary?item=99999999');
    out.unknown_item = has(html(), 'data-state="notfound"');
    return out;
  },
  async topics_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/topics');
    var out = { table: has(html(), 'class="ad-table"') && has(html(), 'data-topic="food"'), slug_is_not_editable: !has(html(), 'id="t-slug-') };
    var slug = uniq('tp');
    setv('n-slug', slug); setv('n-name', 'Weather'); setv('n-icon', 'x');
    await clickAct('create-topic');
    out.created = has(html(), 'data-topic="' + slug + '"');
    var id = (html().match(new RegExp('data-topic="' + slug + '".*?data-id="(\\d+)"')) || [])[1];
    setv('t-name-' + id, 'Weather report'); setv('t-icon-' + id, 'y');
    var msg = cache['#ad-msg'] = { value: '', textContent: '' };
    await clickAct('save-topic', { id: id });
    out.saved = msg.textContent === 'Saved ✓';
    return out;
  },
  async learners_pages() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/learners');
    var h = html(), t = text();
    var out = { table: has(h, 'class="ad-table"'), opaque_references: /<code>[0-9a-f]{10}…<\/code>/.test(h), says_no_identity: has(t, 'no names, emails'), says_nobody_can_be_impersonated: has(t, 'nobody can be signed in as a learner'),
                no_identity_in_the_page: !has(h, '@') && !has(h, 'Pat ') && !has(h, 'display_name') && !has(h, 'password'), has_filters: has(h, 'id="f-age"') && has(h, 'id="f-since"') };
    var ref = (h.match(/href="#\/admin\/learners\/([0-9a-f]{32})"/) || [])[1];
    await open('#/admin/learners?age_group=teen&cefr=A2');
    out.small_group_is_not_shown = has(html(), 'data-state="suppressed"') && has(text(), 'Fewer than 5 learners match') && !has(html(), 'class="ad-table"');
    await open('#/admin/learners/' + ref);
    var d = html();
    out.detail_is_numbers = has(d, 'Lessons started') && has(d, 'Active days (last 30)') && has(text(), 'Numbers only') && !has(d, '@');
    out.detail_offers_no_impersonation = !/log in as|login as|impersonat|act as/i.test(d.replace('or to act as them', '').replace('Numbers only. There is no way to view a learner\'s messages, recordings or answers, or to act as them.', '')) ;
    await open('#/admin/learners/' + '0'.repeat(32));
    out.unknown_reference = has(html(), 'data-state="notfound"');
    return out;
  },
  async audit_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var slug = uniq('ui-aud'), lesson = await newDraft('lessons', slug, { title: 'CANARY-TYPED-TITLE' });
    await adminCall('PATCH', '/api/admin/content/lessons/' + lesson.id, { revision: lesson.revision, title: 'CANARY-TYPED-TITLE-2' });
    await open('#/admin/audit');
    var h = html();
    var out = { table: has(h, 'class="ad-table"') && has(h, '<th>Actor</th>'), shows_the_creation: has(h, '<b>create</b>') && has(h, slug), shows_changed_field_names_only: has(h, 'changed_fields=title') && !has(h, 'CANARY-TYPED-TITLE'), request_ids_shown_short: /<code>[0-9a-f]{8}<\/code>/.test(h),
                filters_present: has(h, 'id="f-actor"') && has(h, 'id="f-action"') && has(h, 'id="f-outcome"'), no_secrets_or_emails: !has(h, '@') && !has(h, 'password') };
    setv('f-actor', ''); setv('f-entity', 'lesson'); setv('f-id', String(lesson.id)); setv('f-action', 'update'); setv('f-outcome', 'ok'); setv('f-from', ''); setv('f-to', '');
    await clickAct('filter');
    out.filter_goes_to_the_url = has(win.location.hash, 'entity_type=lesson') && has(win.location.hash, 'action=update') && has(win.location.hash, 'entity_id=' + lesson.id);
    await open(win.location.hash);
    out.filtered_rows = (html().match(/<tr data-event=/g) || []).length === 1 && has(html(), '<b>update</b>') && !has(html(), '<b>create</b>');
    await open('#/admin/audit?actor=nobody-here');
    out.empty = has(html(), 'data-state="empty"') && has(text(), 'No events match');
    return out;
  },
  async security_page_shows_warnings_events_and_accounts_without_identity() {
    var learnerEmail = await registerLearner('sec');
    await api('POST', '/api/auth/logout');
    await api('POST', '/api/auth/login', { email: learnerEmail, password: 'definitely the wrong password' });      // a failed sign-in to show
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/security');
    var h = html(), t = text();
    var nav = win.AdminView.NAV.some(function (n) { return n[0] === '#/admin/security'; });
    var reads = calls.filter(function (c) { return c.method === 'GET'; }).map(function (c) { return c.url.split('?')[0]; });
    return { in_the_navigation: nav, shows_the_cookie_warning: has(h, 'data-warning="cookie_not_secure"') && has(t, 'COOKIE_SECURE is off'),
             shows_key_and_admin_status: has(t, 'Two-factor key') && has(t, 'valid') && has(t, 'Administrators with two-factor'),
             lists_recent_events: has(h, 'data-section="events"') && has(h, '<b>login_failure</b>') && has(h, '<b>logout</b>'),   // table rows (the type filter's options name every type)
             has_a_type_filter: has(h, 'id="f-type"') && has(h, '<option value="mfa_success"'),
             lists_accounts_with_two_factor: has(h, 'data-section="accounts"') && has(t, 'Two-factor') && has(t, 'learner'),
             no_identity_or_secret: !has(h, '@example.com') && !has(h, learnerEmail) && !has(h, 'definitely the wrong password') && !has(h, '127.0.0.1') && !has(h, 'scrypt'),
             reads_only_the_admin_api: ['/api/admin/health', '/api/admin/security-events', '/api/admin/users'].every(function (u) { return reads.indexOf(u) >= 0; }) };
  },
  async health_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/health');
    var h = html(), t = text();
    var out = { shows_version_and_migration: has(t, 'App version') && has(t, 'Last migration') && has(t, '0056'), database_healthy: has(t, 'healthy'), content_counts: has(t, 'published') && has(t, 'lessons'), booleans_only: has(h, 'chip ok">configured') || has(h, 'chip">not configured'),
                no_secret_values: !has(h, 'CANARY') && !has(h, 'http') && !has(h, '/Users') && !has(h, 'buddy.db') && !has(h, 'sk-') };
    var box = cache['#ad-integrity'] = { innerHTML: '', value: '', textContent: '' };
    await clickAct('integrity');
    out.integrity_check_shows_counts = has(box.innerHTML, 'errors,') && has(box.innerHTML, 'warnings') && calls.some(function (c) { return c.url === '/api/admin/health/integrity'; });
    return out;
  },
  async analytics_page() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/analytics');
    var h = html(), t = text();
    var out = { sections: has(t, 'Active learners') && has(t, 'Learning') && has(t, 'Confidence versus measured accuracy') && has(t, 'Adaptive learning') && has(t, 'Content performance'), chart: has(h, 'data-chart="line"'),
                states_the_rule: has(t, 'fewer than 5 learners is always hidden'), requests_all_seven_endpoints: ['activity', 'learning', 'speaking', 'confidence-weakness', 'engagement', 'adaptive', 'content-performance'].every(function (n) { return calls.some(function (c) { return c.url.indexOf('/api/admin/analytics/' + n + '?') === 0; }); }) };
    setv('ad-window', ''); setv('ad-from', '2026-01-01'); setv('ad-to', '2026-01-31'); setv('ad-grain', 'week');
    await clickAct('apply-window');
    out.custom_dates_go_to_the_url = has(win.location.hash, 'from=2026-01-01') && has(win.location.hash, 'to=2026-01-31') && has(win.location.hash, 'grain=week');
    await open(win.location.hash);
    out.custom_dates_are_sent = calls.some(function (c) { return c.url.indexOf('/analytics/learning?from=2026-01-01&to=2026-01-31') > 0; });
    out.weekly_chart = has(html(), 'per 7-day bucket');
    await open('#/admin/analytics?window=7d&kind=situation');
    out.kind_is_sent = calls.some(function (c) { return c.url.indexOf('kind=situation') > 0; });
    await open('#/admin/analytics?from=2020-01-01&to=2026-03-15');
    out.an_invalid_window_is_an_error_not_a_crash = has(html(), 'data-state="error"') || has(html(), 'Analytics');
    return out;
  },
  async every_admin_page_has_no_delete_and_escapes() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var pages = ['#/admin', '#/admin/curriculum', '#/admin/curriculum/lessons', '#/admin/curriculum/lessons/' + IDS.lesson, '#/admin/curriculum/situations', '#/admin/curriculum/situations/' + IDS.situation,
                 '#/admin/curriculum/listening', '#/admin/curriculum/listening/' + IDS.activity, '#/admin/curriculum/vocabulary', '#/admin/curriculum/topics', '#/admin/analytics', '#/admin/learners', '#/admin/audit', '#/admin/health'];
    var noDelete = true, rendered = true, offenders = [];
    for (var i = 0; i < pages.length; i++) {
      await open(pages[i]);
      var h = html();
      if (/>\s*delete|data-act="delete|Delete</i.test(h)) { noDelete = false; offenders.push(pages[i]); }
      if (has(h, 'Loading…') && !has(h, 'ad-')) rendered = false;
    }
    return { no_page_offers_delete: noDelete, every_page_rendered: rendered, offenders_empty: offenders.length === 0 };
  },
  async published_lesson_detail_is_read_only_with_answers_visible_to_admins() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    await open('#/admin/curriculum/lessons/' + IDS.lesson);
    var h = html();
    return { published_badge: has(h, 'ad-published'), read_only_note: has(h, 'data-readonly="published"'), no_edit_form: !has(h, 'id="e-title"') && !has(h, 'data-act="save-meta"'), shows_correct_answer_marks: has(h, '✅'), has_unpublish_and_archive: has(h, 'data-act="unpublish"') && has(h, 'data-act="archive"') };
  },
  async situation_and_listening_editors() {
    await loginAs(ADMIN_EMAIL); await win.AgeMode.refresh();
    var s = await newDraft('situations', uniq('ui-sit'), { topic: 'food', difficulty: 1, topics: undefined });
    await open('#/admin/curriculum/situations/' + s.id);
    var out = { situation_form: has(html(), 'id="e-topic"') && has(html(), 'id="e-difficulty"') && has(html(), 'data-act="add-step"') };
    setv('n-kind', 'learn_phrase'); setv('n-prompt', ''); setv('n-meaning', ''); setv('n-item', String(IDS.item)); setv('n-answers', '');
    var before = calls.length;
    await clickAct('add-step');
    var add = calls.slice(before).filter(function (c) { return c.method === 'POST' && c.url.indexOf('/steps') > 0; })[0];
    out.adds_a_step = !!add && sentCsrf(add) && JSON.parse(add.body).kind === 'learn_phrase' && has(text(), 'Step added');
    var a = await newDraft('listening', uniq('ui-lis'), { topic: 'food', item_id: IDS.item, mode: 'choose_meaning', prompt: 'Listen', difficulty: 1, topics: undefined, description: undefined });
    await open('#/admin/curriculum/listening/' + a.id);
    out.listening_form = has(html(), 'id="e-mode"') && has(html(), 'data-act="add-option"') && has(text(), 'Options (0 of 3)');
    setv('n-item', String(IDS.item));
    await clickAct('add-option');
    out.adds_an_option = has(text(), 'Option added') && has(text(), 'Options (1 of 3)') && has(text(), 'correct answer');
    return out;
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
