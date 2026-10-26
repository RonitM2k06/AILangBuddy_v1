// Voice practice (#/voice): say a phrase, record it with the microphone, see what speech recognition heard.
// The transcript is shown next to what you were asked to say. It is NOT a pronunciation score and is never described as one.
// The microphone is requested only when you press Record, is on only while the red indicator shows, and is released afterwards.
// Additive: the prototype's own Speaking page (#/speaking) is untouched.
(function () {
  const { api, errText, esc } = window.LBApi;
  const W = window;
  const alive = (root) => document.body.contains(root);
  const MIN_MS = 500, MIN_BYTES = 800;                   // below this we did not record anything worth sending
  const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

  const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">🎙️ Voice practice</div><h1>Say it out loud</h1>
    <p class="sub">Record yourself saying a phrase and see what speech recognition heard.</p></div></div>${inner}`;
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;
  const fmt = (ms) => { const s = Math.floor(ms / 1000); return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); };

  function blocked(res) {
    if (res.status === 401) return note(`<h2>Sign in to practise speaking</h2><p class="muted">Your sessions are saved to your account.</p><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Learner accounts only</h2><p class="muted">Voice practice is for learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><p class="muted">Choose the language you want to learn and your level.</p><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }
  function micError(e) {
    const n = e && e.name;
    if (n === "NotAllowedError" || n === "SecurityError") return "Microphone access was blocked. Allow the microphone for this site in your browser settings, then press Record again.";
    if (n === "NotFoundError" || n === "OverconstrainedError") return "No microphone was found. Connect one and try again.";
    if (n === "NotReadableError") return "The microphone is in use by another app. Close it and try again.";
    return "We couldn't start the microphone. Please try again.";
  }
  const supported = () => !!(W.navigator && W.navigator.mediaDevices && W.navigator.mediaDevices.getUserMedia && W.MediaRecorder);

  async function upload(id, blob, ms) {
    try {
      const r = await fetch(`/api/speaking/sessions/${id}/recording?duration_ms=${Math.max(1, Math.round(ms))}`,
        { method: "POST", headers: { "Content-Type": blob.type || "audio/webm", "X-Requested-With": "XMLHttpRequest" }, body: blob });   // raw audio + the CSRF signal
      let data = null; try { data = await r.json(); } catch (e) {}
      return { ok: r.ok, status: r.status, data };
    } catch (e) { return { ok: false, status: 0, data: null }; }
  }

  async function mount() {
    const root = document.getElementById("voice-root"); if (!root) return;
    const res = await api("GET", "/api/speaking/prompts");
    if (!alive(root)) return;
    const b = blocked(res);
    if (b) { root.innerHTML = shell(b); return; }
    if (!res.ok) { root.innerHTML = shell(note(`<p class="muted">Couldn't load speaking prompts. Please try again.</p>`)); return; }
    const { prompts, stt } = res.data;
    const caps = res.data.capabilities || {};                 // what this language allows BEFORE recording (transcription, pronunciation)
    const banner = await window.LBApi.reviewBanner();
    let typed = "", typedResult = null;
    if (!prompts.length) {
      root.innerHTML = shell(note(`<h2>No speaking prompts for this language and level yet</h2><p class="muted">The rest of LingoBuddy works as before.</p><a class="btn btn-primary" href="#/pack">Open First Week</a>`));
      return;
    }
    const maxMs = stt.max_recording_ms || 30000;
    let selected = (prompts.find((p) => !p.practised) || prompts[0]).item.id;
    let state = "idle", msg = "", session = null, stream = null, recorder = null, chunks = [], blob = null, startedAt = 0, elapsed = 0, timer = null, result = null;
    let assessment = null, assessError = "", reassessing = false, resultId = null;       // the pronunciation assessment of the finished session (a different measurement from the transcript)

    const current = () => prompts.find((p) => p.item.id === selected).item;
    const release = () => {                       // the microphone is never left on
      if (timer) { W.clearInterval(timer); timer = null; }
      if (stream) { try { stream.getTracks().forEach((t) => t.stop()); } catch (e) {} stream = null; }
    };
    const cancelSession = async () => { if (session) { const id = session.id; session = null; await api("POST", `/api/speaking/sessions/${id}/cancel`); } };
    const reset = (message) => { release(); recorder = null; chunks = []; blob = null; result = null; assessment = null; assessError = ""; reassessing = false; state = "idle"; msg = message || ""; draw(); };
    const abort = async (message) => { release(); await cancelSession(); reset(message); };

    function promptCard() {
      const it = current();
      return `<div class="card"><div class="eyebrow" style="margin-bottom:8px">You are asked to say</div>
        <div class="deva" style="font-weight:700;font-size:26px">${esc(it.text)}</div>
        <div style="color:var(--brand);font-weight:600">${esc(it.pronunciation || "")}</div>
        <div class="muted">${esc(it.meaning || "")}</div>
        <div class="row" style="margin-top:10px"><button class="btn btn-ghost btn-sm" data-hear>🔊 Hear it</button>
          <select class="pc-in" data-prompt ${state === "idle" || state === "result" ? "" : "disabled"}>${prompts.map((p) => `<option value="${p.item.id}" ${p.item.id === selected ? "selected" : ""}>${esc(p.item.pronunciation || p.item.text)}${p.practised ? " ✓" : ""}</option>`).join("")}</select></div></div>`;
    }
    function draw() {
      let body = "";
      if (state === "result" && result) body = resultHTML();
      else if (state === "idle") {
        const unavailable = !supported() ? "Your browser can't record audio here (it needs microphone access and MediaRecorder). You can still practise listening."
          : !stt.available ? "Speech recognition isn't set up on this server, so a recording can't be turned into text yet."
          : caps.transcription === "unsupported_language" ? `Speech recognition here doesn't support ${caps.language_name || "this language"}, so a recording can't be turned into text or scored.`
          : "";
        body = `${promptCard()}<div class="card" style="text-align:center;margin-top:12px">
          <button class="btn btn-primary btn-lg" data-record ${unavailable ? "disabled" : ""}>🎙️ Record</button>
          <div class="muted" style="margin-top:8px;font-size:13px">${unavailable ? esc(unavailable) : `The microphone is only on while you see the red recording indicator. Up to ${Math.round(maxMs / 1000)} seconds.`}</div>
          ${msg ? `<div style="margin-top:8px;color:#d8284b" data-msg>${esc(msg)}</div>` : ""}</div>`;
      } else if (state === "requesting") {
        body = `${promptCard()}<div class="card muted" style="text-align:center;margin-top:12px">Waiting for microphone permission…</div>`;
      } else if (state === "recording" || state === "stopping") {
        body = `${promptCard()}<div class="card" style="text-align:center;margin-top:12px"><div style="font-size:18px;font-weight:700"><span style="color:#d8284b" data-indicator>🔴 Recording</span> <span data-timer>${fmt(elapsed)}</span> <span class="muted">/ ${fmt(maxMs)}</span></div>
          <div class="row" style="justify-content:center;margin-top:12px"><button class="btn btn-primary" data-stop ${state === "stopping" ? "disabled" : ""}>⏹ Stop</button><button class="btn btn-ghost" data-cancel>Cancel</button></div></div>`;
      } else if (state === "review") {
        body = `${promptCard()}<div class="card" style="text-align:center;margin-top:12px"><b>Recorded ${fmt(elapsed)}</b>
          <div class="muted" style="font-size:13px">Send it to be turned into text, or record again.</div>
          <div class="row" style="justify-content:center;margin-top:12px"><button class="btn btn-primary" data-submit>Use this recording</button><button class="btn btn-ghost" data-again>↺ Record again</button><button class="btn btn-ghost" data-cancel>Cancel</button></div></div>`;
      } else if (state === "uploading" || state === "processing" || state === "assessing") {
        body = `${promptCard()}<div class="card muted" style="text-align:center;margin-top:12px" data-status>${state === "uploading" ? "Sending your recording…" : state === "assessing" ? "Checking pronunciation…" : "Turning your speech into text…"}</div>`;
      } else if (state === "error") {
        body = `${promptCard()}<div class="card" style="margin-top:12px"><b data-msg>${esc(msg)}</b><div class="row" style="margin-top:10px"><button class="btn btn-primary" data-again>↺ Try again</button></div></div>`;
      }
      root.innerHTML = shell(banner + body + (state === "idle" || state === "result" ? typedCard() : ""));
    }
    // Typed practice works for every language and every device: it compares the letters typed with the phrase. It hears nothing and is no score.
    // Latin accents are ignored ("cafe" matches "café"); other scripts' vowel signs are kept
    const fold = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").normalize("NFC").replace(/[.,!?।"“”'’‘:;()\-]/g, " ").replace(/\s+/g, " ").trim();
    function typedCard() {
      const it = current();
      const verdict = typedResult === null ? "" : typedResult
        ? `<div style="margin-top:8px" data-typed-ok><b>✅ That matches the phrase.</b></div>`
        : `<div style="margin-top:8px" data-typed-no><b>Not the same yet.</b> <span class="muted">The phrase is “${esc(it.pronunciation || it.text)}” (${esc(it.text)}).</span></div>`;
      return `<div class="card" style="margin-top:12px" data-typed-card><div class="eyebrow" style="margin:0 0 6px">⌨️ Typed check</div>
        <div class="muted" style="font-size:13px">${/[^\p{Script=Latin}\P{L}]/u.test(it.text || "") ? `Type the phrase in Roman letters or ${/[\u0C80-\u0CFF]/.test(it.text) ? "Kannada script" : /[\u0B80-\u0BFF]/.test(it.text) ? "Tamil script" : /[\u0980-\u09FF]/.test(it.text) ? "Bengali script" : /[\u0C00-\u0C7F]/.test(it.text) ? "Telugu script" : /[\u0620\u0655\u065A\u065B\u0672\u06C4]/.test(it.text) ? "Kashmiri script" : /[\u0600-\u06FF]/.test(it.text) ? "Urdu script" : "Devanagari"}.` : "Type the phrase; accents are optional."} This compares the letters you type; it does not hear you or score pronunciation.</div>
        <div class="row" style="margin-top:8px"><input class="pc-in" data-typed aria-label="Type the phrase" value="${esc(typed)}" style="flex:1;min-width:0" />
          <button class="btn btn-ghost" data-typed-check>Check</button></div>${verdict}</div>`;
    }
    const RETRYABLE = ["provider_error", "provider_timeout", "malformed_output", "no_signal"];
    function pronunciationCard() {
      if (reassessing) return `<div class="card muted" style="margin-top:12px;border:2px solid var(--brand)" data-pron-card>Checking pronunciation…</div>`;
      const p = assessment && assessment.pronunciation;
      if (p && p.available) {
        const badge = p.is_measurement ? "" : `<div class="chip warn" style="margin-top:6px" data-pron-badge>Test score from a ${esc(p.method_label || p.method)}. Not a real measurement of how you said it.</div>`;
        const comps = Object.keys(p.components || {}).length
          ? `<ul style="margin:8px 0 0;padding-left:18px" data-components>${Object.keys(p.components).sort().map((k) => `<li>${esc(k.replace("_", " "))}: ${p.components[k]} / 100</li>`).join("")}</ul>` : "";
        const words = (p.word_scores || []).length
          ? `<div class="muted" style="margin-top:8px;font-size:13px" data-word-scores>Word scores: ${p.word_scores.map((w) => `${esc(w.word)} ${w.score}`).join(" · ")}</div>` : "";
        return `<div class="card" style="margin-top:12px;border:2px solid var(--brand)" data-pron-card><div class="eyebrow" style="margin-bottom:6px">Pronunciation</div>
          <div style="font-size:34px;font-weight:800" data-pron-score>${p.score} <span style="font-size:16px;font-weight:600" class="muted">/ 100</span></div>${badge}${comps}${words}</div>`;
      }
      const err = p && p.error ? p.error : { code: "", message: assessError || "Pronunciation couldn't be assessed this time." };
      const retry = (!assessment || RETRYABLE.indexOf(err.code) >= 0) ? `<div class="row" style="margin-top:8px"><button class="btn btn-ghost btn-sm" data-reassess>Try assessing again</button></div>` : "";
      return `<div class="card" style="margin-top:12px;border:2px solid var(--brand)" data-pron-card><div class="eyebrow" style="margin-bottom:6px">Pronunciation</div>
        <div style="font-weight:700" data-pron-unavailable>Not available</div><div class="muted" data-pron-error>${esc(err.message)}</div>${retry}</div>`;
    }
    function resultHTML() {
      const it = current(), t = result.transcript, c = assessment && assessment.content_match;
      const word = c ? `<div class="card" style="margin-top:12px;background:var(--surface-2)" data-content-card><div class="eyebrow" style="margin-bottom:6px">Word check: what was recognised</div>
          <div style="font-weight:700" data-content-count>${c.words_matched} of ${c.words_expected} words recognised</div>
          <div class="muted" style="font-size:13px">This compares the words speech recognition heard with the words of the phrase. It does not measure how you pronounced them.</div></div>` : "";
      const feedback = assessment && assessment.feedback && assessment.feedback.length
        ? `<div class="card" style="margin-top:12px" data-feedback><div class="eyebrow" style="margin-bottom:6px">Feedback</div><ul style="margin:0;padding-left:18px">${assessment.feedback.map((f) => `<li class="${f.type === "notice" ? "muted" : ""}">${esc(f.text)}</li>`).join("")}</ul></div>` : "";
      return `<div class="grid g2" style="align-items:start">
        <div class="card"><div class="eyebrow" style="margin-bottom:8px">You were asked to say</div><div class="deva" style="font-weight:700;font-size:22px" data-asked>${esc(it.text)}</div>
          <div style="color:var(--brand);font-weight:600">${esc(it.pronunciation || "")}</div><div class="muted">${esc(it.meaning || "")}</div></div>
        <div class="card" style="background:var(--surface-2)"><div class="eyebrow" style="margin-bottom:8px">Speech recognition heard</div><div class="deva" style="font-weight:700;font-size:22px" data-heard>${esc(t.text)}</div>
          <div class="muted" style="font-size:13px">via ${esc(t.provider)}. This is only what the recogniser heard; it is not a pronunciation score.</div></div></div>
        ${word}${pronunciationCard()}${feedback}
        <p class="muted" style="font-size:13px;margin:10px 0" data-two-measurements>The word check and the pronunciation score are two separate measurements: a clear transcript does not mean good pronunciation, and a difference in the transcript does not mean poor pronunciation.
          ${result.recording && !result.recording.kept ? "Your recording was deleted after it was transcribed." : ""}</p>
        <div class="row"><button class="btn btn-ghost" data-again>↺ Try again</button><button class="btn btn-primary" data-next>Next phrase →</button></div>`;
    }

    async function start() {
      msg = ""; state = "requesting"; draw();
      try { stream = await W.navigator.mediaDevices.getUserMedia({ audio: true }); }
      catch (e) { reset(micError(e)); return; }
      const r = await api("POST", "/api/speaking/sessions", { item_id: selected });     // only after permission: no orphan sessions
      if (!r.ok) { release(); reset(errText(r)); return; }
      session = r.data.session;
      try {
        const mime = MIME_CANDIDATES.find((t) => W.MediaRecorder.isTypeSupported && W.MediaRecorder.isTypeSupported(t));
        recorder = mime ? new W.MediaRecorder(stream, { mimeType: mime }) : new W.MediaRecorder(stream);
        chunks = [];
        recorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = onStopped;
        recorder.onerror = () => { abort("Recording failed. Please try again."); };
        recorder.start();
      } catch (e) { await abort("We couldn't start recording. Please try again."); return; }
      startedAt = W.Date.now(); elapsed = 0; state = "recording";
      timer = W.setInterval(tick, 200);
      draw();
    }
    function tick() {
      elapsed = W.Date.now() - startedAt;
      if (elapsed >= maxMs) { elapsed = maxMs; stop(); return; }        // the maximum length ends the recording by itself
      const el = root.querySelector("[data-timer]"); if (el) el.textContent = fmt(elapsed);
    }
    function stop() {
      if (state !== "recording") return;
      state = "stopping"; if (timer) { W.clearInterval(timer); timer = null; }
      elapsed = Math.min(W.Date.now() - startedAt, maxMs);
      try { recorder.stop(); } catch (e) { onStopped(); }
      draw();
    }
    async function onStopped() {
      if (state !== "stopping") return;
      release();
      blob = new W.Blob(chunks, { type: (recorder && recorder.mimeType) || "audio/webm" });
      if (blob.size < MIN_BYTES || elapsed < MIN_MS) { await abort("We didn't catch anything. Try again a little closer to the microphone."); return; }
      state = "review"; draw();
    }
    async function assess(id) {                 // a separate step from transcription, with its own result
      assessment = null; assessError = "";
      const as = await api("POST", `/api/speaking/sessions/${id}/assess-pronunciation`);
      if (as.ok) assessment = as.data.assessment; else assessError = errText(as);
      const fresh = await api("GET", `/api/speaking/sessions/${id}`);       // the recording may have been deleted by now
      if (fresh.ok && fresh.data.session.transcript) result = fresh.data.session;
      resultId = id;
    }
    async function submit() {
      state = "uploading"; draw();
      const up = await upload(session.id, blob, elapsed);
      if (!up.ok) { const m = up.data && typeof up.data.detail === "string" ? up.data.detail : "We couldn't send your recording."; await cancelSession(); release(); state = "error"; msg = m; draw(); return; }
      state = "processing"; draw();
      const tr = await api("POST", `/api/speaking/sessions/${session.id}/transcribe`);
      if (!alive(root)) return;
      if (!tr.ok) { state = "error"; msg = errText(tr); draw(); return; }
      const s = tr.data.session;
      if (s.stage === "completed" && s.transcript) {
        const done = prompts.find((x) => x.item.id === selected); if (done) done.practised = true;
        const id = session.id; session = null; blob = null;
        result = s; state = "assessing"; draw();
        await assess(id);
        if (!alive(root)) return;
        state = "result"; draw();
      } else { session = null; blob = null; state = "error"; msg = (s.error && s.error.message) || "Speech recognition didn't work this time."; draw(); }
    }

    root.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.record !== undefined) await start();
      else if (d.stop !== undefined) stop();
      else if (d.submit !== undefined) await submit();
      else if (d.again !== undefined) { await abort(""); }
      else if (d.cancel !== undefined) { if (state === "recording") { try { recorder.onstop = null; recorder.stop(); } catch (e) {} } await abort(""); }
      else if (d.next !== undefined) { const nxt = prompts.find((p) => !p.practised) || prompts[0]; selected = nxt.item.id; reset(""); }
      else if (d.reassess !== undefined) { reassessing = true; draw(); await assess(resultId); reassessing = false; draw(); }
      else if (d.hear !== undefined) {
        const it = current();
        if (!(W.Engine && W.Engine.canSpeak)) { msg = "Audio isn't available in this browser."; draw(); }
        else if (W.Engine.hasVoice && !W.Engine.hasVoice(caps.locale)) { msg = `This device has no ${caps.language_name || "voice for this language"} voice, so the phrase can't be played. Read it: ${it.pronunciation || it.text}`; draw(); }
        else W.Engine.speak({ hi: it.text, roman: it.pronunciation }, { locale: caps.locale });
      }
      else if (d.typedCheck !== undefined) {
        const it = current(), box = root.querySelector("[data-typed]");
        typed = box ? box.value : "";
        typedResult = !!fold(typed) && [it.text, it.pronunciation].some((x) => x && fold(x) === fold(typed));
        draw();
      }
    };
    root.onchange = (ev) => { if (ev.target && ev.target.dataset && ev.target.dataset.prompt !== undefined && (state === "idle" || state === "result")) { selected = +ev.target.value; typed = ""; typedResult = null; reset(""); } };
    if (W.addEventListener) W.addEventListener("hashchange", () => { if (!alive(root) || !document.getElementById("voice-root")) { if (state === "recording") { try { recorder.onstop = null; recorder.stop(); } catch (e) {} } release(); cancelSession(); } });
    draw();
  }

  window.VoiceView = { page() { setTimeout(mount, 0); return `<div id="voice-root"><div class="card muted">Loading…</div></div>`; } };
})();
