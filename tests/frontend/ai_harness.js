// Drives the real frontend/agemode.js and ai.js (plus profile.js for the shared API helper) in JavaScriptCore
// (osascript) against a live test server. Timers are stubs; HTTP is real (via curl). Each scenario prints one line "## {json}"
// with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, KEY (answer key read from the test database), DOB_CHILD,
// DOB_TEEN, DOB_ADULT, KEY (roleplay answer key read from the test database). Two browsers (cookie jars) are used: one per learner (A and B).
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
var sent = [], failNext = false, fake = {};
function fetch(url, opts) {
  opts = opts || {};
  sent.push({ method: opts.method || 'GET', url: url, body: opts.body || null });
  if (fake[url]) return Promise.resolve({ ok: true, status: 200, json: function () { return Promise.resolve(fake[url]); } });
  if (failNext && (opts.method || 'GET') === 'POST' && /\/messages$/.test(url)) { failNext = false; return Promise.resolve({ ok: false, status: 502, json: function () { return Promise.resolve({ detail: "The tutor couldn't answer right now. Please try again." }); } }); }
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
var KEY = E('KEY') ? JSON.parse(E('KEY')) : {};
var cache = {};
var rootEl = { innerHTML: '', onclick: null, onchange: null, querySelector: function (s) { return cache[s] || (cache[s] = { value: '', textContent: '' }); } };
var classes = {};
var document = { getElementById: function (id) { return id === 'aitutor-root' || id === 'airoleplay-root' || id === 'adaptive-root' ? rootEl : null; },
                 body: { contains: function () { return true; }, classList: { add: function (c) { classes[c] = true; }, remove: function () { for (var i = 0; i < arguments.length; i++) delete classes[arguments[i]]; } } } };
var win = { setInterval: function () { return 1; }, clearInterval: function () {}, location: { hash: '' }, confirm: function () { return true; } };
var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/agemode.js'); load('frontend/ai.js'); load('frontend/adaptive.js');

var tick = async function () { for (var i = 0; i < 200; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
var click = async function (d) { await rootEl.onclick({ target: { closest: function () { return { dataset: d }; } } }); await tick(); };
var api = win.LBApi.api;
var mountTutor = async function (id) { win.AiTutorView.page(id === undefined ? undefined : String(id)); await lastMount; await tick(); };
var mountAdaptive = async function () { win.AdaptiveView.page(); await lastMount; await tick(); };
var mountRoleplay = async function (id) { win.AiRoleplayView.page(id === undefined ? undefined : String(id)); await lastMount; await tick(); };
function has(s, sub) { return s.indexOf(sub) >= 0; }
function count(s, sub) { return s.split(sub).length - 1; }
function as(jar) { JAR = jar; }
async function learner(jar, name, dob) {
  as(jar);
  await api('POST', '/api/auth/register', { email: 'a' + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com', password: 'ui-password-123', display_name: name, role: 'learner' });
  await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: dob });
  await win.AgeMode.refresh();
}
async function newConversation() { return (await api('POST', '/api/tutor/conversations', {})).data.conversation.id; }
async function situationId(title) { var l = (await api('GET', '/api/situations')).data.situations; for (var i = 0; i < l.length; i++) if (l[i].title === title) return l[i].id; }
async function startSession(title) { return (await api('POST', '/api/roleplay/sessions', { situation_id: await situationId(title) })).data.session.id; }
// wrong listening answers, repeated, so the existing weakness engine finds something (finding the right option costs one correct answer per activity)
async function makeWeak() {
  var list = (await api('GET', '/api/listening')).data.activities;
  for (var i = 0; i < list.length; i++) {
    if (list[i].topic.slug !== 'greetings') continue;
    var a = (await api('GET', '/api/listening/' + list[i].id)).data.activity, wrong = null;
    for (var j = 0; j < a.options.length; j++) { var r = await api('POST', '/api/listening/' + a.id + '/attempts', { option_id: a.options[j].id }); if (!r.data.correct) { wrong = a.options[j].id; break; } }
    for (var k = 0; k < 4; k++) await api('POST', '/api/listening/' + a.id + '/attempts', { option_id: wrong });
  }
}
var ALL_ANSWERS = function () { var out = []; KEY.transport.forEach(function (texts) { texts.forEach(function (t) { if (t) out.push(t); }); }); return out; };
async function solve(sid, n) { for (var i = 0; i < KEY.transport.length && (n === undefined || i < n); i++) await api('POST', '/api/roleplay/sessions/' + sid + '/turns', { text: KEY.transport[i][0] }); }

var scenarios = {
  async tutor_signed_out() {
    await mountTutor();
    return { asks_to_sign_in: has(text(), 'Sign in to use the tutor') };
  },
  async tutor_list_and_start() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountTutor();
    var empty = has(text(), 'No conversations yet');
    await click({ new: '' });
    return { empty_at_first: empty, goes_to_the_new_conversation: win.location.hash === '#/ai-tutor/1' || /^#\/ai-tutor\/\d+$/.test(win.location.hash) };
  },
  async tutor_conversation_and_reply() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var id = await newConversation(); await mountTutor(id);
    var t0 = text();
    cache['#at-input'] = { value: 'give me a hint please', textContent: '' };
    await click({ send: '' });
    var t = text(), h = html();
    return { invites_a_hello: has(t0, 'Say hello to your tutor'), shows_my_message: has(t, 'give me a hint please'), reply_is_labelled_generated: has(t, 'generated advice'), reply_separates_records_from_advice: has(t, 'From your records:') && has(t, 'Advice (generated, not a record):'),
             input_cleared: !has(h, 'value="give me a hint please"'), stored_once: (await api('GET', '/api/tutor/conversations/' + id)).data.conversation.message_count === 2 };
  },
  async tutor_shows_stored_facts_apart() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN'));
    await api('POST', '/api/confidence', { topic: 'food', score: 35 });
    var id = await newConversation(); await mountTutor(id);
    cache['#at-input'] = { value: 'how am I doing', textContent: '' };
    await click({ send: '' });
    var h = html();
    return { facts_box: has(text(), 'From your records (stored facts the tutor was given)'), shows_the_stored_fact: has(text(), 'Self-rated confidence in Food: 35%'), advice_stays_in_the_reply: has(h, 'generated advice') };
  },
  async tutor_failure_keeps_the_text_and_a_retry_is_safe() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var id = await newConversation(); await mountTutor(id);
    cache['#at-input'] = { value: 'please explain my mistake', textContent: '' };
    failNext = true; sent.length = 0;
    await click({ send: '' });
    var r = { error_shown: has(text(), "couldn't answer just now") && has(text(), 'press Send to try again'), text_kept: has(html(), 'value="please explain my mistake"'), nothing_stored: (await api('GET', '/api/tutor/conversations/' + id)).data.conversation.message_count === 0 };
    cache['#at-input'] = { value: 'please explain my mistake', textContent: '' };
    await click({ send: '' });
    var ids = sent.filter(function (s) { return s.method === 'POST' && /messages$/.test(s.url); }).map(function (s) { return JSON.parse(s.body).client_id; });
    r.retry_uses_the_same_id = ids.length === 2 && ids[0] === ids[1];
    r.retry_works_and_is_stored_once = has(text(), 'please explain my mistake') && !has(text(), "couldn't answer") && (await api('GET', '/api/tutor/conversations/' + id)).data.conversation.message_count === 2;
    return r;
  },
  async tutor_empty_message_is_not_sent() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var id = await newConversation(); await mountTutor(id);
    cache['#at-input'] = { value: '   ', textContent: '' }; sent.length = 0;
    await click({ send: '' });
    return { asks_for_text: has(text(), 'Type a message first'), nothing_sent: sent.filter(function (s) { return s.method === 'POST'; }).length === 0 };
  },
  async tutor_child_gets_only_helper_questions() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD')); var id = await newConversation(); await mountTutor(id);
    var h = html();
    var r = { no_free_text_box: !has(h, 'id="at-input"'), helper_buttons: count(h, 'data-quick=') === 3 && has(text(), 'Teach me a new phrase') };
    await click({ quick: 'teach_me_a_phrase' });
    r.child_gets_a_phrase = has(text(), 'Here is a new phrase') && !has(html(), 'From your records');
    r.server_refuses_free_text = (await api('POST', '/api/tutor/conversations/' + id + '/messages', { message: 'tell me a story' })).status === 422;
    return r;
  },
  async tutor_someone_elses_conversation_looks_missing() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var id = await newConversation();
    await api('POST', '/api/tutor/conversations/' + id + '/messages', { message: 'private words' });
    await learner(B_JAR, 'Bea', E('DOB_TEEN')); await mountTutor(id);
    return { not_found: has(text(), 'Conversation not found'), nothing_leaked: !has(html(), 'private words') && !has(html(), 'at-input') };
  },
  async roleplay_list_and_start() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountRoleplay();
    var t = text();
    var r = { situations_listed: has(t, 'Auto-rickshaw ride') && has(t, 'Get to Connaught Place for a fair price.') && count(html(), 'data-start=') >= 7 };
    await click({ start: String(await situationId('Auto-rickshaw ride')) });
    r.goes_to_the_session = /^#\/ai-roleplay\/\d+$/.test(win.location.hash);
    return r;
  },
  async roleplay_a_turn_with_hint_and_progress() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await mountRoleplay(sid);
    var t0 = text();
    var r = { shows_scene_and_objective: has(t0, 'Raju bhaiya') && has(t0, 'Say this in Hindi'), progress: has(text(), 'Step 1 of 7'), three_tries: has(t0, '3 tries left') };
    cache['#rp-input'] = { value: 'wrong words', textContent: '' };
    await click({ say: '' });
    var t = text();
    r.not_quite = has(t, 'Not quite') && has(t, 'wrong words'); r.hint_shown = has(t, 'Hint: The phrase is'); r.two_tries_left = has(t, '2 tries left');
    cache['#rp-input'] = { value: KEY.transport[0][0], textContent: '' };
    await click({ say: '' });
    r.correct_advances = has(text(), '✓ Correct') && has(text(), 'Step 2 of 7') && has(text(), 'Model answer:');
    return r;
  },
  async roleplay_never_shows_an_unresolved_answer() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await mountRoleplay(sid);
    cache['#rp-input'] = { value: 'no', textContent: '' }; await click({ say: '' });
    cache['#rp-input'] = { value: 'nope', textContent: '' }; await click({ say: '' });
    var h = html(), leaked = ALL_ANSWERS().filter(function (a) { return has(unescapeHtml(h), a); });
    return { two_wrong_tries_show_no_answer: leaked.length === 0, still_no_model_answer: !has(h, 'Model answer:') };
  },
  async roleplay_complete_and_feedback() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await solve(sid); await mountRoleplay(sid);
    var r = { offers_feedback: has(text(), 'All steps done') && has(html(), 'data-complete') && !has(html(), 'id="rp-input"') };
    await click({ complete: '' });
    var t = text();
    r.feedback = has(t, '7 of 7 steps correct (7 on the first try).') && has(t, 'Vocabulary:') && has(t, 'Grammar:') && has(t, 'Next:');
    r.xp_shown = has(t, '+25 XP');
    r.no_pronunciation_claim = has(text(), 'no pronunciation feedback') && !has(t, 'pronunciation score:');
    r.finished = has(text(), 'Finished') || has(html(), 'More roleplays');
    var again = await api('POST', '/api/roleplay/sessions/' + sid + '/complete');
    r.replay_pays_nothing = again.data.xp_awarded === 0 && again.data.replayed === true;
    return r;
  },
  async roleplay_reopening_a_finished_session_shows_its_feedback() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await solve(sid);
    await api('POST', '/api/roleplay/sessions/' + sid + '/complete'); await mountRoleplay(sid);
    return { feedback_shown: has(text(), 'Feedback') && has(text(), '7 of 7 steps correct'), no_input: !has(html(), 'id="rp-input"') };
  },
  async roleplay_empty_reply_is_not_sent_and_errors_are_shown() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD')); var sid = await startSession('Auto-rickshaw ride'); await mountRoleplay(sid);
    cache['#rp-input'] = { value: ' ', textContent: '' }; sent.length = 0; await click({ say: '' });
    var r = { asks_for_text: has(text(), 'Type your reply first'), nothing_sent: sent.filter(function (s) { return s.method === 'POST'; }).length === 0 };
    cache['#rp-input'] = { value: new Array(120).join('x'), textContent: '' };
    await click({ say: '' });
    r.child_limit_is_explained = has(text(), 'must be 1-100 characters');
    return r;
  },
  async roleplay_someone_elses_session_looks_missing() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride');
    await api('POST', '/api/roleplay/sessions/' + sid + '/turns', { text: 'private reply' });
    await learner(B_JAR, 'Bea', E('DOB_TEEN')); await mountRoleplay(sid);
    return { not_found: has(text(), 'Roleplay not found'), nothing_leaked: !has(html(), 'private reply') && !has(html(), 'Raju') };
  },
  async roleplay_signed_out() {
    await mountRoleplay();
    return { asks_to_sign_in: has(text(), 'Sign in to use roleplay') };
  },
  async adaptive_signed_out() {
    await mountAdaptive();
    return { asks_to_sign_in: has(text(), 'Sign in to see your next steps') };
  },
  async adaptive_new_learner_is_told_when_there_is_not_enough_evidence() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await mountAdaptive();
    var t = text();
    return { says_so_for_insights: has(t, 'Not enough evidence yet to say anything about your progress'), no_drills: has(t, 'No drills right now'), labelled: has(t, 'Generated wording is labelled') || has(t, 'labelled'),
             plan_ranked_by_records: has(t, 'ranked by your records'), no_xp_claims: has(t, 'earns no XP') };
  },
  async adaptive_shows_suggestions_with_the_evidence_behind_them() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await makeWeak(); await mountAdaptive();
    var t = text(), h = html();
    return { suggestion_for_the_weak_topic: has(t, 'Greetings') && has(t, 'review topic'), shows_why: has(t, 'Why: Greetings:') && has(t, 'of the last'), apply_button: has(h, 'data-apply='),
             insight_with_numbers: has(t, 'You have been missing Greetings questions'), plan_listed: has(t, "Today's plan, in order"), drill_offered: has(h, 'data-drill='), no_answer_flags: !has(h, 'is_correct') };
  },
  async adaptive_applying_a_suggestion() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await makeWeak(); await mountAdaptive();
    var id = /data-apply="(\d+)"/.exec(html())[1];
    await click({ apply: id });
    var recs = (await api('GET', '/api/ai/recommendations')).data.recommendations;
    return { says_noted: has(text(), 'Noted. Open it from the menu or here: #/'), shows_taken: has(text(), 'Taken ✓'), server_agrees: recs.some(function (r) { return String(r.id) === id && r.status === 'applied'; }) };
  },
  async adaptive_answering_a_drill() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await makeWeak();
    var before = (await api('GET', '/api/gamification')).data.xp.total;
    await mountAdaptive();
    var h = html(), m = /data-drill="(\d+)" data-choice="(\d+)"/.exec(h), id = m[1], choices = [], x;
    var re = new RegExp('data-drill="' + id + '" data-choice="(\\d+)"', 'g');
    while ((x = re.exec(h))) choices.push(x[1]);
    var sawRight = false, sawWrong = false;
    for (var i = 0; i < choices.length; i++) { await click({ drill: id, choice: choices[i] }); var tt = text(); if (has(tt, 'Correct ✓')) sawRight = true; if (has(tt, 'Not quite')) sawWrong = true; }
    var t = text();
    var after = (await api('GET', '/api/gamification')).data.xp.total;
    return { has_a_drill: !!m, offered_several_choices: choices.length >= 3, shows_both_outcomes_correctly: sawRight && sawWrong, reveals_the_answer_after: has(t, 'Answer:'), says_practice_only: has(t, 'earns no XP'), no_xp_change: before === after };
  },
  async adaptive_labels_a_model_ranking() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN'));
    fake['/api/ai/adaptive-plan'] = { date: '2026-09-01', source: 'llm', mode: 'teen', enough_evidence: true, phase6_plan: { generated: false, done: 0, total: 0 },
                                      items: [{ rank: 1, kind: 'next_lesson', title: 'Greetings', reason: 'Next lesson', ai_note: 'Because: x.', target: { type: 'lesson', id: 1 }, evidence: [], in_phase6_plan: false, status: null }] };
    await mountAdaptive();
    var t = text();
    delete fake['/api/ai/adaptive-plan'];
    await mountAdaptive();
    return { says_a_model_ranked_it: has(t, 'ranked by an AI model'), built_in_ranking_is_labelled_as_records: has(text(), 'ranked by your records') && !has(text(), 'ranked by an AI model') };
  },

  async adaptive_for_a_child_is_the_same_page_without_a_model() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD')); await makeWeak(); await mountAdaptive();
    var t = text();
    return { works: has(t, 'Suggestions for you') && has(t, 'Practice drills made for you'), not_ranked_by_a_model: !has(t, 'ranked by an AI model'), drills_are_labelled: has(t, 'Practice made for you') };
  },
  async tutor_shows_the_current_suggestion_apart_from_the_chat() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); await makeWeak(); var id = await newConversation(); await mountTutor(id);
    var t = text();
    cache['#at-input'] = { value: 'what next?', textContent: '' }; await click({ send: '' });
    var after = text();
    return { card_shown: has(html(), 'id="at-suggestion"') && has(t, 'Suggested next step (generated from your records)'), names_the_activity: has(t, 'Greetings'),
             tutor_quotes_it_as_a_stored_fact: has(after, 'Suggested next step (from your learning plan)') };
  },
  async tutor_for_a_child_has_no_suggestion_card() {
    await learner(A_JAR, 'Kiki', E('DOB_CHILD')); await makeWeak(); var id = await newConversation(); await mountTutor(id);
    return { no_card: !has(html(), 'at-suggestion') };
  },
  async roleplay_shows_how_an_answer_was_understood() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await solve(sid, 1); await mountRoleplay(sid);
    cache['#rp-input'] = { value: 'Kitne rupaye honge?', textContent: '' }; await click({ say: '' });
    var t1 = text();
    var r = { understood: has(t1, 'Understood: your wording means the same.') && has(t1, '2 of 2 key words matched'), advanced: has(t1, 'Step 3 of 7') && has(t1, '✓ Correct') };
    cache['#rp-input'] = { value: 'Kitni door hai', textContent: '' }; await click({ say: '' });
    var t2 = text();
    r.close_is_explained = has(t2, 'Close: 2 of 3 key words matched.') && has(t2, '(1 key word missing)') && has(t2, "Hint: You're close: 1 key word missing.");
    var resolved = KEY.transport[0].concat(KEY.transport[1]);                                   // steps 1 and 2 are done, so their model answers may be shown
    r.no_answer_leak = !ALL_ANSWERS().some(function (a) { return has(unescapeHtml(html()), a) && resolved.indexOf(a) < 0; });
    return r;
  },
  async roleplay_offers_practice_for_missed_phrases() {
    await learner(A_JAR, 'Aria', E('DOB_TEEN')); var sid = await startSession('Auto-rickshaw ride'); await mountRoleplay(sid);
    for (var i = 0; i < 3; i++) { cache['#rp-input'] = { value: 'zzz', textContent: '' }; await click({ say: '' }); }
    for (var j = 1; j < KEY.transport.length; j++) await api('POST', '/api/roleplay/sessions/' + sid + '/turns', { text: KEY.transport[j][0] });
    await mountRoleplay(sid);
    await click({ complete: '' });
    var t = text();
    return { shows_practice_next: has(html(), 'id="rp-remediation"') && has(t, 'Practise next') && has(t, 'Practice drill:'), links_to_the_drills: has(t, 'Open my practice drills'), keeps_feedback: has(t, '6 of 7 steps correct') };
  },
  async navigation_for_parents_has_no_ai_pages() {
    as(A_JAR);
    await api('POST', '/api/auth/register', { email: 'par' + Date.now() + '@example.com', password: 'ui-password-123', display_name: 'Pat', role: 'parent' });
    await win.AgeMode.refresh();
    var nav = win.AgeMode.filterNav([['#/', 'H', 'Home'], ['#/ai-tutor', 'T', 'Tutor Chat'], ['#/ai-roleplay', 'R', 'Roleplay'], ['#/ai-insights', 'A', 'Adaptive Learning'], ['#/rewards', 'W', 'Rewards']]);
    return { parent_gets_none_of_them: nav.every(function (n) { return ['#/ai-tutor', '#/ai-roleplay', '#/ai-insights', '#/rewards'].indexOf(n[0]) < 0; }) && nav.some(function (n) { return n[0] === '#/parent'; }) };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
