// Drives the real frontend/profile.js, twofactor.js, agemode.js and admin.js in JavaScriptCore (osascript) against a live test server
// (Phase 14D). HTTP is real (curl, one cookie jar per browser); timers and the DOM are stubs. TOTP codes are computed here from the setup
// key the page shows, exactly as an authenticator app would (HMAC-SHA1, 30 s, 6 digits), and each time step is used at most once.
// Each scenario prints one line "## {json}" with named boolean checks. Inputs: BASE, ROOT, WORKDIR, SCENARIO, PASSWORD, ADMIN_EMAIL.
ObjC.import('Foundation');
var envp = $.NSProcessInfo.processInfo.environment;
function E(k) { var v = envp.objectForKey(k); return v.isNil() ? '' : ObjC.unwrap(v); }
var BASE = E('BASE'), ROOT = E('ROOT'), WORKDIR = E('WORKDIR'), SCENARIO = E('SCENARIO'), PASSWORD = E('PASSWORD');
var JAR = WORKDIR + '/a.txt';

function read(p) { return $.NSString.stringWithContentsOfFileEncodingError(ROOT + '/' + p, 4, null).js; }
function curl(args) {
  var task = $.NSTask.alloc.init, pipe = $.NSPipe.pipe;
  task.launchPath = '/usr/bin/curl'; task.arguments = args; task.standardOutput = pipe; task.launch; task.waitUntilExit;
  return $.NSString.alloc.initWithDataEncoding(pipe.fileHandleForReading.readDataToEndOfFile, 4).js;
}
var sent = [];
function fetch(url, opts) {
  opts = opts || {};
  sent.push({ method: opts.method || 'GET', url: url, body: opts.body || null, headers: opts.headers || {} });
  var args = ['-s', '-i', '-b', JAR, '-c', JAR, '-X', opts.method || 'GET'];
  var h = opts.headers || {}; for (var k in h) { args.push('-H'); args.push(k + ': ' + h[k]); }
  if (opts.body) { args.push('--data-binary'); args.push(opts.body); }
  args.push(BASE + url);
  var raw = curl(args), split = raw.indexOf('\r\n\r\n');
  while (/^HTTP\/[\d.]+ 100/.test(raw)) { raw = raw.slice(split + 4); split = raw.indexOf('\r\n\r\n'); }
  var head = raw.slice(0, split), text = raw.slice(split + 4);
  var status = parseInt(/HTTP\/[\d.]+ (\d+)/.exec(head)[1], 10);
  return Promise.resolve({ ok: status >= 200 && status < 300, status: status, json: function () { return Promise.resolve(JSON.parse(text)); } });
}

// ---- stubbed browser ----
function element() {
  var kids = {};
  return { innerHTML: '', textContent: '', value: '', onclick: null, onchange: null, kids: kids, dataset: {},
           querySelector: function (s) { return kids[s] || (kids[s] = element()); }, querySelectorAll: function () { return []; },
           classList: { add: function () {}, remove: function () {} } };
}
var profileRoot = element(), adminRoot = element();
var storage = {};
var document = { getElementById: function (id) { return id === 'profile-root' ? profileRoot : id === 'admin-root' ? adminRoot : null; },
                 body: { contains: function () { return true; }, classList: { add: function () {}, remove: function () {} } } };
var win = { location: { hash: '#/admin', replace: function (h) { win.location.hash = h; } }, setInterval: function () { return 1; }, clearInterval: function () {},
            addEventListener: function () {}, dispatchEvent: function () {}, confirm: function () { return true; },
            localStorage: { getItem: function (k) { return storage[k] || null; }, setItem: function (k, v) { storage[k] = String(v); } },
            navigator: { clipboard: { writeText: function (t) { win.copied = t; return Promise.resolve(); } } } };
var timers = [];
var timeoutStub = function (f) { timers.push(f); };
var Event = function (t) { this.type = t; };
function load(p) { new Function('window', 'document', 'fetch', 'setTimeout', 'Event', 'localStorage', read(p))(win, document, fetch, timeoutStub, Event, win.localStorage); }
load('frontend/profile.js'); load('frontend/twofactor.js'); load('frontend/agemode.js'); load('frontend/admin.js');

async function settle() { for (var r = 0; r < 30; r++) { for (var i = 0; i < 200; i++) await null; var due = timers.splice(0); if (!due.length) break; for (var j = 0; j < due.length; j++) await due[j](); } }
function act(el, name) { return el.onclick({ target: { closest: function () { return { dataset: { act: name } }; } } }); }
function has(s, sub) { return s.indexOf(sub) >= 0; }
var api = win.LBApi.api;

// ---- TOTP, as an authenticator app computes it ----
function b32decode(s) {
  var A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567', bits = '', out = [];
  s = s.replace(/[\s=]/g, '').toUpperCase();
  for (var i = 0; i < s.length; i++) bits += ('00000' + A.indexOf(s[i]).toString(2)).slice(-5);
  for (var j = 0; j + 8 <= bits.length; j += 8) out.push(parseInt(bits.slice(j, j + 8), 2));
  return out;
}
function sha1(bytes) {
  var h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0], ml = bytes.length * 8, m = bytes.slice();
  m.push(0x80); while (m.length % 64 !== 56) m.push(0);
  for (var s = 56; s >= 0; s -= 8) m.push(s >= 32 ? 0 : (ml >>> s) & 0xff);
  var rotl = function (x, n) { return (x << n) | (x >>> (32 - n)); };
  for (var c = 0; c < m.length; c += 64) {
    var w = [];
    for (var i = 0; i < 16; i++) w[i] = (m[c + 4 * i] << 24) | (m[c + 4 * i + 1] << 16) | (m[c + 4 * i + 2] << 8) | m[c + 4 * i + 3];
    for (i = 16; i < 80; i++) w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    var a = h[0], b = h[1], d = h[2], e = h[3], f = h[4];
    for (i = 0; i < 80; i++) {
      var k, fn;
      if (i < 20) { fn = (b & d) | (~b & e); k = 0x5A827999; } else if (i < 40) { fn = b ^ d ^ e; k = 0x6ED9EBA1; }
      else if (i < 60) { fn = (b & d) | (b & e) | (d & e); k = 0x8F1BBCDC; } else { fn = b ^ d ^ e; k = 0xCA62C1D6; }
      var t = (rotl(a, 5) + fn + f + k + w[i]) | 0; f = e; e = d; d = rotl(b, 30); b = a; a = t;
    }
    h = [(h[0] + a) | 0, (h[1] + b) | 0, (h[2] + d) | 0, (h[3] + e) | 0, (h[4] + f) | 0];
  }
  var out = []; h.forEach(function (x) { out.push((x >>> 24) & 255, (x >>> 16) & 255, (x >>> 8) & 255, x & 255); }); return out;
}
function hmacSha1(key, msg) {
  if (key.length > 64) key = sha1(key);
  var k = key.slice(); while (k.length < 64) k.push(0);
  var ipad = k.map(function (x) { return x ^ 0x36; }), opad = k.map(function (x) { return x ^ 0x5c; });
  return sha1(opad.concat(sha1(ipad.concat(msg))));
}
function totpAt(secret, step) {
  var msg = [0, 0, 0, 0, (step >>> 24) & 255, (step >>> 16) & 255, (step >>> 8) & 255, step & 255];
  var mac = hmacSha1(b32decode(secret), msg), o = mac[19] & 15;
  var v = ((mac[o] & 127) << 24) | (mac[o + 1] << 16) | (mac[o + 2] << 8) | mac[o + 3];
  return ('000000' + (v % 1000000)).slice(-6);
}
var lastStep = {};
function nextCode(secret) {                                 // the earliest step the server still accepts (now-1 .. now+1, after the last used)
  for (;;) {
    var now = Math.floor(Date.now() / 1000 / 30);
    for (var s = now - 1; s <= now + 1; s++) if (lastStep[secret] === undefined || s > lastStep[secret]) { lastStep[secret] = s; return totpAt(secret, s); }
    delay(2);
  }
}

// ---- accounts ----
function fresh(tag) { return tag + Date.now() + Math.floor(Math.random() * 1e6) + '@example.com'; }
async function learner() { var email = fresh('l'); JAR = WORKDIR + '/' + email + '.txt'; await api('POST', '/api/auth/register', { email: email, password: PASSWORD, display_name: 'Lee' }); return email; }
async function enrollByApi() {
  var s = (await api('POST', '/api/auth/2fa/setup', { password: PASSWORD })).data;
  var r = await api('POST', '/api/auth/2fa/confirm', { code: nextCode(s.secret) });
  return { secret: s.secret, codes: r.data.recovery_codes };
}
async function mountProfile() { profileRoot.innerHTML = ''; win.ProfileView.page(); await settle(); }
function keyFrom(html) { var m = /<code id="tf-key" class="tf-key">([A-Z2-7 ]+)<\/code>/.exec(html); return m ? m[1].replace(/ /g, '') : null; }

var scenarios = {
  async setup_shows_the_qr_and_key_then_the_recovery_codes_once() {
    await learner(); await mountProfile();
    var card = profileRoot.kids['#pf-2fa'];
    var start = card.innerHTML;
    card.querySelector('#tf-password').value = PASSWORD; await act(card, 'setup'); await settle();
    var setupHtml = card.innerHTML, secret = keyFrom(setupHtml);
    await act(card, 'copy'); await settle();
    var qr = /<svg class="tf-qr" viewBox="0 0 (\d+) \1"[^>]*><rect[^>]*\/><path d="(M\d+ \d+h1v1h-1z)+" fill="#000"\/><\/svg>/.test(setupHtml);
    card.querySelector('#tf-code').value = nextCode(secret); await act(card, 'confirm'); await settle();
    var shown = card.innerHTML, codes = shown.match(/<code>([A-Z2-7]{4}(-[A-Z2-7]{4}){3})<\/code>/g) || [];
    await act(card, 'saved'); await settle();
    var after = card.innerHTML;
    await mountProfile();
    var again = profileRoot.kids['#pf-2fa'].innerHTML, status = (await api('GET', '/api/auth/2fa')).data;
    return { offers_setup: has(start, 'Set up two-factor authentication') && has(start, 'data-state="off"'), draws_a_local_qr: qr && !has(setupHtml, 'http'),
             shows_the_manual_key: !!secret && secret.length === 32, copy_button_copies_the_key: win.copied === secret,
             shows_ten_codes_once: codes.length === 10 && has(shown, 'not shown again'), codes_gone_after_saving: !/[A-Z2-7]{4}-[A-Z2-7]{4}-/.test(after),
             status_is_on: status.enabled === true && has(again, 'chip ok">On') && has(again, '10 recovery codes left'),
             nothing_secret_after_setup: !has(again, secret) && !has(after, secret) && !/[A-Z2-7]{4}-[A-Z2-7]{4}-/.test(again),
             nothing_stored_in_the_browser: Object.keys(storage).length === 0 };
  },
  async sign_in_asks_for_the_code_and_only_then_signs_in() {
    var email = await learner(); var tf = await enrollByApi();
    await api('POST', '/api/auth/logout');
    await mountProfile();
    profileRoot.kids['#pf-email'] = { value: email }; profileRoot.kids['#pf-pass'] = { value: PASSWORD };
    await profileRoot.kids['#pf-login'].onclick(); await settle();
    var step = profileRoot.innerHTML, signedOutDuring = (await api('GET', '/api/auth/me')).status === 401;
    profileRoot.querySelector('#tf-login-code').value = '000000'; await act(profileRoot, 'verify'); await settle();
    var wrong = profileRoot.innerHTML;
    profileRoot.querySelector('#tf-login-code').value = nextCode(tf.secret); await act(profileRoot, 'verify'); await settle();
    var me = await api('GET', '/api/auth/me');
    return { shows_the_code_step: has(step, 'data-state="mfa-challenge"') && has(step, 'autocomplete="one-time-code"'), no_session_before_the_code: signedOutDuring,
             wrong_code_is_said_plainly: has(wrong, 'That code is not correct') && has(wrong, 'mfa-challenge'),
             signed_in_after_the_code: me.status === 200 && me.data.user.email === email, back_on_the_profile: !has(profileRoot.innerHTML, 'mfa-challenge'),
             every_write_is_signalled: sent.filter(function (s) { return s.method !== 'GET'; }).every(function (s) { return s.headers['X-Requested-With'] === 'XMLHttpRequest'; }) };
  },
  async a_recovery_code_signs_in_instead() {
    var email = await learner(); var tf = await enrollByApi();
    await api('POST', '/api/auth/logout'); await mountProfile();
    profileRoot.kids['#pf-email'] = { value: email }; profileRoot.kids['#pf-pass'] = { value: PASSWORD };
    await profileRoot.kids['#pf-login'].onclick(); await settle();
    await act(profileRoot, 'toggle'); await settle();
    var toggled = profileRoot.innerHTML;
    profileRoot.querySelector('#tf-recovery').value = tf.codes[0]; await act(profileRoot, 'verify'); await settle();
    var me = await api('GET', '/api/auth/me'), status = (await api('GET', '/api/auth/2fa')).data;
    return { offers_a_recovery_code: has(toggled, 'id="tf-recovery"') && has(toggled, 'XXXX-XXXX-XXXX-XXXX'), signed_in: me.status === 200,
             the_code_is_spent: status.recovery_codes_remaining === 9 };
  },
  async new_codes_and_turning_it_off_from_the_card() {
    await learner(); var tf = await enrollByApi(); await mountProfile();
    var card = profileRoot.kids['#pf-2fa'];
    card.querySelector('#tf-regen-password').value = PASSWORD; card.querySelector('#tf-regen-code').value = nextCode(tf.secret);
    await act(card, 'regenerate'); await settle();
    var regen = card.innerHTML, codes = regen.match(/<code>([A-Z2-7]{4}(-[A-Z2-7]{4}){3})<\/code>/g) || [];
    var fresh = codes.map(function (c) { return c.replace(/<\/?code>/g, ''); });
    card.querySelector('#tf-off-password').value = 'wrong password'; card.querySelector('#tf-off-code').value = fresh[0];
    await act(card, 'disable'); await settle();
    var refused = card.kids['#tf-msg'].textContent, stillOn = (await api('GET', '/api/auth/2fa')).data.enabled;
    card.querySelector('#tf-off-password').value = PASSWORD; card.querySelector('#tf-off-code').value = fresh[0];
    await act(card, 'disable'); await settle();
    var off = card.innerHTML + ' ' + card.kids['#tf-msg'].textContent, status = (await api('GET', '/api/auth/2fa')).data;
    return { new_codes_shown_once: codes.length === 10 && tf.codes.every(function (c) { return !has(regen, c); }),
             wrong_password_is_refused: stillOn === true && has(refused, 'The password or the code is not correct'),
             turned_off: status.enabled === false && has(off, 'is off') && has(off, 'data-state="off"'), still_signed_in: (await api('GET', '/api/auth/me')).status === 200 };
  },
  async an_admin_must_turn_it_on_before_the_console_opens() {
    JAR = WORKDIR + '/admin.txt';
    await api('POST', '/api/auth/login', { email: E('ADMIN_EMAIL'), password: PASSWORD });
    await win.AgeMode.refresh();
    win.AdminView.page(); await settle();
    var gate = adminRoot.innerHTML, card = adminRoot.kids['#ad-2fa'], cardHtml = card ? card.innerHTML : '';
    var blocked = (await api('GET', '/api/admin/dashboard')).status;
    card.querySelector('#tf-password').value = PASSWORD; await act(card, 'setup'); await settle();
    var secret = keyFrom(card.innerHTML);
    card.querySelector('#tf-code').value = nextCode(secret); await act(card, 'confirm'); await settle();
    var codes = card.innerHTML, noOff = has(codes, 'Administrators cannot turn two-factor authentication off') && !has(codes, 'data-act="disable"');
    await act(card, 'saved'); await settle();
    var opened = adminRoot.innerHTML, dash = await api('GET', '/api/admin/dashboard');
    return { console_says_why: has(gate, 'data-state="mfa-required"') && has(gate, 'Turn on two-factor authentication'), not_sent_home: win.location.hash === '#/admin',
             setup_offered_in_place: has(cardHtml, 'Set up two-factor authentication') && has(cardHtml, 'Administrators must use it'), api_refused_before: blocked === 403,
             admin_cannot_turn_it_off: noOff, console_opens_after: dash.status === 200 && !has(opened, 'mfa-required') };
  },
  async a_wrong_password_on_setup_says_so_and_shows_no_key() {
    await learner(); await mountProfile();
    var card = profileRoot.kids['#pf-2fa'];
    card.querySelector('#tf-password').value = 'not the password'; await act(card, 'setup'); await settle();
    var html = card.innerHTML, msg = card.kids['#tf-msg'] ? card.kids['#tf-msg'].textContent : '';
    return { says_the_password_is_wrong: msg === 'That password is not correct.', no_key_or_qr: !has(html, 'tf-key') && !has(html, '<svg') };
  },
};

(async function () {
  var checks;
  try { checks = await scenarios[SCENARIO](); } catch (e) { checks = { harness_error: false, error: String(e) + ' ' + (e.stack || '') }; }
  console.log('## ' + JSON.stringify({ scenario: SCENARIO, checks: checks }));
})();
