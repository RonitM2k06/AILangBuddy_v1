// Drives the real frontend/profile.js + frontend/voice.js in JavaScriptCore (osascript) against a live test server.
// The microphone, MediaRecorder, Blob, clock and timers are stubs; HTTP is real (via curl). Each scenario prints one line
// "## {json}" with named boolean checks. Inputs come from the environment: BASE, ROOT, WORKDIR, SCENARIO.
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO');
var JAR = WORKDIR + '/cookies.txt', UPLOAD = WORKDIR + '/upload.bin';

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function sh(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}
var uploads = [];
function fetch(url, opts) {
  opts = opts || {};
  var args = ['-s', '-i', '-b', JAR, '-c', JAR, '-X', opts.method || 'GET'];
  var h = opts.headers || {}; for (var k in h) { args.push('-H'); args.push(k + ': ' + h[k]); }
  if (opts.body && opts.body.__bytes !== undefined) {                       // a recorded Blob: send its bytes
    $(opts.body.__bytes).writeToFileAtomicallyEncodingError(UPLOAD, false, 4, null);
    uploads.push({ url: url, type: h['Content-Type'], size: opts.body.size });
    args.push('--data-binary'); args.push('@' + UPLOAD);
  } else if (opts.body) { args.push('--data-binary'); args.push(opts.body); }
  args.push(BASE + url);
  var raw = sh(args), split = raw.indexOf('\r\n\r\n');
  var head = raw.slice(0, split), text = raw.slice(split + 4);
  var status = parseInt(/HTTP\/[\d.]+ (\d+)/.exec(head)[1], 10);
  return Promise.resolve({ ok: status >= 200 && status < 300, status: status, json: function () { return Promise.resolve(JSON.parse(text)); } });
}

// ---- stubbed browser ----
var cache = {};
var rootEl = { innerHTML: '', onclick: null, onchange: null, querySelector: function (s) { return cache[s] || (cache[s] = { textContent: '' }); } };
var document = { getElementById: function (id) { return id === 'voice-root' ? rootEl : null; }, body: { contains: function () { return true; } } };
var fakeNow = 1000000, intervals = [], streamStops = 0, gum = 0, recStarts = 0, recStops = 0, recorders = [];
var cfg = { gumError: null, text: 'नमस्ते', payloadKind: 'normal', startThrows: false, pron: '' };
var win = { LANGUAGES: [], Date: { now: function () { return fakeNow; } },
            setInterval: function (fn) { intervals.push({ fn: fn, cleared: false }); return intervals.length; },
            clearInterval: function (id) { if (intervals[id - 1]) intervals[id - 1].cleared = true; } };
var spoken = [];
win.Engine = { canSpeak: true, speak: function (p) { spoken.push(p.hi); } };
function advance(ms) { fakeNow += ms; intervals.filter(function (i) { return !i.cleared; }).forEach(function (i) { i.fn(); }); }
function utf8len(s) { return unescape(encodeURIComponent(s)).length; }
win.Blob = function (parts, opts) {
  this.__bytes = parts.map(function (p) { return p && p.__bytes !== undefined ? p.__bytes : String(p); }).join('');
  this.size = utf8len(this.__bytes); this.type = (opts && opts.type) || '';
};
function pad(n) { return new Array(n + 1).join('\u0000'); }
function payload() {
  if (cfg.payloadKind === 'tiny') return 'OggSxxxxxx';
  if (cfg.payloadKind === 'wrongtype') return 'RIFF\u0000\u0000\u0000\u0000WAVE' + pad(1200);       // a WAV file presented as Ogg
  if (cfg.payloadKind === 'fail') return 'OggS' + 'MOCKFAIL\n' + pad(1200);
  return 'OggS' + 'MOCKSTT:' + cfg.text + '\n' + cfg.pron + pad(1200);       // cfg.pron: controlled pronunciation markers for the mock provider
}
win.MediaRecorder = function (stream, o) { this.stream = stream; this.mimeType = (o && o.mimeType) || ''; recorders.push(this); };
win.MediaRecorder.isTypeSupported = function (t) { return t === 'audio/ogg;codecs=opus'; };
win.MediaRecorder.prototype.start = function () { if (cfg.startThrows) throw new Error('nope'); recStarts++; };
win.MediaRecorder.prototype.stop = function () {
  recStops++;
  if (this.ondataavailable) this.ondataavailable({ data: new win.Blob([payload()], { type: this.mimeType }) });
  if (this.onstop) this.onstop();
};
var stream = { getTracks: function () { return [{ stop: function () { streamStops++; } }]; } };
win.navigator = { mediaDevices: { getUserMedia: function () {
  gum++;
  if (cfg.gumError) { var e = new Error('x'); e.name = cfg.gumError; return Promise.reject(e); }
  return Promise.resolve(stream);
} } };

var lastMount = null;
var timeoutStub = function (f) { lastMount = f(); };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', read(p))(win, document, fetch, timeoutStub); }
load('frontend/profile.js'); load('frontend/voice.js');

var tick = async function () { for (var i = 0; i < 120; i++) await null; };
var html = function () { return rootEl.innerHTML; };
var unescapeHtml = function (t) { return t.replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
var text = function () { return unescapeHtml(rootEl.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); };
var inner = function (attr) { var m = new RegExp(attr + '[^>]*>([^<]*)<').exec(rootEl.innerHTML); return m ? unescapeHtml(m[1]) : null; };
var click = async function (d) { await rootEl.onclick({ target: { closest: function () { return { dataset: d }; } } }); await tick(); };
var api = win.LBApi.api;
var sessions = async function () { return (await api('GET', '/api/speaking/sessions')).data.sessions; };
var mount = async function () { win.VoiceView.page(); await lastMount; await tick(); };
async function login(role) {
  await api('POST', '/api/auth/register', { email: 'v' + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com', password: 'ui-password-123', display_name: 'Voice', role: role || 'learner' });
  await api('PUT', '/api/profile', { native_language: 'en', target_language: 'hi', cefr_level: 'A1', date_of_birth: '2000-01-01' });
}
function has(s, sub) { return s.indexOf(sub) >= 0; }

async function recordAndSubmit(ms) { await click({ record: '' }); advance(ms || 2500); await click({ stop: '' }); await click({ submit: '' }); }
var ASKED = 'नमस्ते, आप कैसे हैं?';
var BAD_WORDS = /(Great|Perfect|Well done|Excellent|Good job|Nice work|Well pronounced|Correct!|✅|mispronounc|your pronunciation of|phoneme|vowel|consonant)/i;   // praise, verdicts, invented sound errors

var scenarios = {
  async signed_out() {
    await mount();
    return { asks_to_sign_in: has(text(), 'Sign in to practise speaking'), no_record_button: !has(html(), 'data-record') };
  },
  async unsupported_browser() {
    win.navigator = {}; await login(); await mount();
    return { explains: has(text(), "can't record audio"), record_disabled: has(html(), 'data-record disabled'), prompt_still_shown: has(html(), 'data-hear'),
             no_permission_asked: gum === 0, no_session_created: (await sessions()).length === 0 };
  },
  async stt_unavailable() {
    await login(); await mount();
    return { explains: has(text(), "Speech recognition isn't set up"), record_disabled: has(html(), 'data-record disabled'), no_permission_asked: gum === 0 };
  },
  async permission_denied() {
    cfg.gumError = 'NotAllowedError'; await login(); await mount();
    await click({ record: '' });
    var r = { message_shown: has(text(), 'Microphone access was blocked'), back_to_idle: has(html(), 'data-record') && !has(html(), 'data-indicator'),
              asked_once: gum === 1, no_session_created: (await sessions()).length === 0, nothing_recorded: recStarts === 0 && recorders.length === 0 };
    cfg.gumError = null; await click({ record: '' });
    r.retry_works_after_allowing = has(html(), 'data-indicator'); r.retry_created_one_session = (await sessions()).length === 1;
    return r;
  },
  async no_microphone() {
    cfg.gumError = 'NotFoundError'; await login(); await mount(); await click({ record: '' });
    return { message_shown: has(text(), 'No microphone was found'), no_session_created: (await sessions()).length === 0 };
  },
  async successful_recording() {
    await login(); await mount();
    var r = {};
    r.idle_has_privacy_note = has(text(), 'only on while you see the red recording indicator');
    r.nothing_before_click = gum === 0 && recStarts === 0 && (await sessions()).length === 0;     // no silent recording
    await click({ record: '' });
    r.recording_indicator = has(html(), 'data-indicator') && has(text(), 'Recording');
    r.requested_mic_once = gum === 1 && recStarts === 1;
    r.session_created_after_permission = (await sessions()).length === 1 && (await sessions())[0].stage === 'created';
    advance(3200);
    r.timer_shows_elapsed = cache['[data-timer]'].textContent === '00:03';
    await click({ stop: '' });
    r.mic_released_on_stop = streamStops === 1 && recStops === 1;
    r.review_shown = has(html(), 'data-submit') && has(text(), 'Recorded 00:03');
    await click({ submit: '' });
    var t = text();
    r.upload_sent_with_recorder_type = uploads.length === 1 && uploads[0].type === 'audio/ogg;codecs=opus' && /duration_ms=3200/.test(uploads[0].url);
    r.result_shown = has(html(), 'data-asked') && has(html(), 'data-heard');
    r.asked_and_heard_are_separate = has(html(), 'You were asked to say') && has(html(), 'Speech recognition heard');
    r.heard_text_rendered = inner('data-heard') === cfg.text;
    r.asked_text_is_the_prompt = inner('data-asked') === 'नमस्ते, आप कैसे हैं?' && inner('data-asked') !== inner('data-heard');
    r.disclaimer_present = has(t, 'not a pronunciation score');
    r.no_quality_claims = !/(Correct|Great|Well done|Perfect|Excellent|\d+%|Good pronunciation)/.test(t) && !has(t, '✅');
    r.deletion_noted = has(t, 'recording was deleted');
    var s = await sessions();
    r.server_session_completed = s.length === 1 && s[0].stage === 'completed' && s[0].transcript === cfg.text;
    r.next_and_retry_offered = has(html(), 'data-next') && has(html(), 'data-again');
    return r;
  },
  async empty_recording() {
    cfg.payloadKind = 'tiny'; await login(); await mount(); await click({ record: '' }); advance(1500); await click({ stop: '' });
    var s = await sessions();
    return { message_shown: has(text(), "didn't catch anything"), back_to_idle: has(html(), 'data-record'), nothing_uploaded: uploads.length === 0,
             session_cancelled: s.length === 1 && s[0].stage === 'cancelled', mic_released: streamStops === 1 };
  },
  async too_short_recording() {
    await login(); await mount(); await click({ record: '' }); advance(100); await click({ stop: '' });
    var s = await sessions();
    return { message_shown: has(text(), "didn't catch anything"), nothing_uploaded: uploads.length === 0, session_cancelled: s[0].stage === 'cancelled' };
  },
  async maximum_duration() {
    await login(); await mount(); await click({ record: '' });
    advance(31000); await tick();
    return { stopped_by_itself: recStops === 1 && streamStops === 1, review_shown: has(html(), 'data-submit'), shows_the_limit: has(text(), 'Recorded 00:30'),
             timer_stopped: intervals.every(function (i) { return i.cleared; }) };
  },
  async cancel_and_retry() {
    await login(); await mount(); await click({ record: '' }); advance(2000); await click({ stop: '' });
    await click({ again: '' });
    var r = { record_again_returns_to_idle: has(html(), 'data-record'), first_session_cancelled: (await sessions())[0].stage === 'cancelled', nothing_uploaded: uploads.length === 0 };
    await click({ record: '' });
    r.second_recording_started = has(html(), 'data-indicator') && (await sessions()).length === 2;
    await click({ cancel: '' });
    var s = await sessions();
    r.cancel_during_recording_releases_mic = streamStops === 2 && recStops === 2;
    r.both_sessions_cancelled = s.length === 2 && s.every(function (x) { return x.stage === 'cancelled'; });
    r.back_to_idle = has(html(), 'data-record') && !has(html(), 'data-indicator');
    return r;
  },
  async stt_failure_is_shown_safely() {
    cfg.payloadKind = 'fail'; await login(); await mount(); await click({ record: '' }); advance(2000); await click({ stop: '' }); await click({ submit: '' });
    var s = await sessions();
    return { error_shown: has(text(), 'Speech recognition had a problem'), no_transcript_block: !has(html(), 'data-heard'), try_again_offered: has(html(), 'data-again'),
             server_session_failed: s[0].stage === 'failed', no_raw_error_leak: !has(text(), 'MOCKFAIL') && !has(text(), 'Traceback') };
  },
  async upload_rejected_by_server() {
    cfg.payloadKind = 'wrongtype'; await login(); await mount(); await click({ record: '' }); advance(2000); await click({ stop: '' }); await click({ submit: '' });
    var s = await sessions();
    return { server_message_shown: has(text(), 'does not look like the audio type'), try_again_offered: has(html(), 'data-again'), session_cancelled: s[0].stage === 'cancelled', mic_released: streamStops === 1 };
  },
  async recorder_failure() {
    await login(); await mount(); await click({ record: '' });
    await recorders[0].onerror({}); await tick();
    var s = await sessions();
    return { message_shown: has(text(), 'Recording failed'), mic_released: streamStops === 1, session_cancelled: s[0].stage === 'cancelled', back_to_idle: has(html(), 'data-record') };
  },
  async recorder_cannot_start() {
    cfg.startThrows = true; await login(); await mount(); await click({ record: '' });
    var s = await sessions();
    return { message_shown: has(text(), "couldn't start recording"), mic_released: streamStops === 1, session_cancelled: s[0].stage === 'cancelled' };
  },
  async pronunciation_is_a_separate_result() {
    cfg.text = ASKED; cfg.pron = 'MOCKPRON:18\nMOCKPRONC:fluency=66\nMOCKPRONW:नमस्ते=90\nMOCKPRONW:आप=41\n';
    await login(); await mount(); await recordAndSubmit();
    var t = text(), h = html(), r = {};
    r.transcript_block = inner('data-heard') === ASKED && has(h, 'Speech recognition heard');
    r.transcript_note_not_a_score = has(t, 'it is not a pronunciation score');
    r.word_check_block = has(h, 'data-content-card') && inner('data-content-count') === '4 of 4 words recognised';
    r.word_check_says_it_is_not_pronunciation = has(t, 'It does not measure how you pronounced them');
    r.pronunciation_block_is_separate = has(h, 'data-pron-card') && h.indexOf('data-content-card') < h.indexOf('data-pron-card') && h.indexOf('data-heard') < h.indexOf('data-pron-card');
    r.score_shown = /^18\s*\/ 100$/.test(inner('data-pron-score').replace(/\s+/g, ' ').trim()) || has(h, 'data-pron-score>18 <');
    r.perfect_transcript_but_low_pronunciation = inner('data-content-count') === '4 of 4 words recognised' && has(h, 'data-pron-score>18');
    r.test_provider_is_labelled = has(h, 'data-pron-badge') && has(t, 'Not a real measurement of how you said it');
    r.components_listed = has(h, 'data-components') && has(t, 'fluency: 66 / 100');
    r.word_scores_listed = has(h, 'data-word-scores') && has(t, 'आप 41');
    r.words_to_practise_from_provider_scores = has(t, 'Words to practise (word scores from the provider): आप (41)');
    r.limitation_in_feedback = has(h, 'data-feedback') && has(t, 'controlled test values, not a measurement');
    r.explains_two_measurements = has(h, 'data-two-measurements') && has(t, 'two separate measurements');
    r.no_invented_claims = !BAD_WORDS.test(t) && !/\d+%/.test(t);
    r.deleted_after_assessment = has(t, 'recording was deleted');
    r.next_and_retry_offered = has(h, 'data-next') && has(h, 'data-again');
    var s = await sessions();
    r.server_session_completed = s.length === 1 && s[0].stage === 'completed';
    return r;
  },
  async poor_transcript_with_high_pronunciation_is_shown_as_is() {
    cfg.text = 'कुछ और'; cfg.pron = 'MOCKPRON:95\n';
    await login(); await mount(); await recordAndSubmit();
    var t = text(), h = html();
    return { content_shows_the_mismatch: inner('data-content-count') === '0 of 4 words recognised', score_still_high: has(h, 'data-pron-score>95'),
             recogniser_miss_is_not_called_a_pronunciation_fault: has(t, 'does not by itself show a pronunciation problem') && !/your pronunciation of/i.test(t),
             only_an_overall_score_is_reported: has(t, 'only an overall score') && !has(h, 'data-components') && !has(h, 'data-word-scores') };
  },
  async pronunciation_failure_can_be_retried() {
    cfg.text = ASKED; cfg.pron = 'MOCKPRONFAIL\n';
    await login(); await mount(); await recordAndSubmit();
    var r = { transcript_still_shown: inner('data-heard') === ASKED, word_check_still_shown: inner('data-content-count') === '4 of 4 words recognised',
              pronunciation_not_available: has(html(), 'data-pron-unavailable') && has(text(), 'Pronunciation analysis had a problem'), no_score_element: !has(html(), 'data-pron-score'),
              retry_offered: has(html(), 'data-reassess') };
    await click({ reassess: '' });
    r.retry_is_a_new_attempt_and_shows_the_same_outcome = has(html(), 'data-pron-unavailable') && has(html(), 'data-reassess');
    var rows = await api('GET', '/api/speaking/pronunciation/history');
    r.both_attempts_recorded = rows.data.history.length === 2 && rows.data.history.every(function (x) { return x.status === 'failed' && x.pronunciation_score === null; });
    r.page_still_usable = has(html(), 'data-again') && has(html(), 'data-next');
    return r;
  },
  async no_signal_is_reported_without_inventing_a_score() {
    cfg.text = ASKED; cfg.pron = '';
    await login(); await mount(); await recordAndSubmit();
    return { not_available: has(html(), 'data-pron-unavailable'), message: has(text(), 'had nothing to report'), no_score: !has(html(), 'data-pron-score'), word_check_shown: inner('data-content-count') === '4 of 4 words recognised' };
  },
  async pronunciation_unavailable_on_a_server_without_a_provider() {
    cfg.text = ASKED;
    await login(); await mount(); await recordAndSubmit();
    var t = text(), h = html();
    return { word_check_shown: inner('data-content-count') === '4 of 4 words recognised', pronunciation_card_says_not_available: has(h, 'data-pron-unavailable') && has(t, "Pronunciation analysis isn't available on this server"),
             no_score: !has(h, 'data-pron-score'), no_retry_for_a_missing_provider: !has(h, 'data-reassess'), feedback_explains_the_word_check: has(t, 'does not measure pronunciation'),
             transcript_still_shown: inner('data-heard') === ASKED };
  },
  async choosing_another_phrase() {
    await login(); await mount();
    var opts = []; var re = /<option value="(\d+)"/g, m; while ((m = re.exec(html()))) opts.push(m[1]);
    await rootEl.onchange({ target: { dataset: { prompt: '' }, value: opts[5] } }); await tick();
    return { many_prompts_offered: opts.length === 35, selection_changes_the_prompt: has(html(), '<option value="' + opts[5] + '" selected>') };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
