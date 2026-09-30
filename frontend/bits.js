// Vanilla-JS ports of React Bits components (https://github.com/DavidHDev/react-bits):
// BlurText, CountUp, SpotlightCard, TiltedCard, Magnet, ClickSpark, DecryptedText,
// RotatingText, TextType, AnimatedContent. Call Bits.enhance(root) after each render.
(function () {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = matchMedia("(pointer: fine)").matches;

  // BlurText: words fade in from blur, staggered.
  function blurText(el) {
    if (el.dataset.bitsDone) return; el.dataset.bitsDone = 1;
    if (reduce) return;
    let i = 0;
    const walk = (node) => {
      [...node.childNodes].forEach((n) => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach((w) => {
            if (!w.trim()) return frag.appendChild(document.createTextNode(w));
            const s = document.createElement("span"); s.className = "blur-word"; s.textContent = w;
            s.style.animationDelay = i++ * 0.09 + "s"; frag.appendChild(s);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && n.tagName !== "BR") walk(n);
      });
    };
    walk(el);
  }

  // CountUp: animate numbers from 0 (data-count="78" data-suffix="%").
  function countUp(el) {
    if (el.dataset.bitsDone) return; el.dataset.bitsDone = 1;
    const to = parseFloat(el.dataset.count), suffix = el.dataset.suffix || "";
    if (reduce || !isFinite(to)) { el.textContent = to + suffix; return; }
    const dur = 1100, t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * e) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // DecryptedText: scramble characters, then resolve left→right.
  const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#%&*+=?@";
  function decrypt(el) {
    if (el.dataset.bitsDone) return; el.dataset.bitsDone = 1;
    const target = el.textContent; if (reduce) return;
    let frame = 0; const total = target.length + 12;
    const id = setInterval(() => {
      frame++;
      el.textContent = target.split("").map((c, i) => (c === " " || i < frame - 12 ? c : GLYPHS[(Math.random() * GLYPHS.length) | 0])).join("");
      if (frame >= total) { clearInterval(id); el.textContent = target; }
    }, 35);
  }

  // RotatingText: cycles words with a vertical slide (data-rotate="a|b|c").
  function rotating(el) {
    if (el.dataset.bitsDone) return; el.dataset.bitsDone = 1;
    const words = el.dataset.rotate.split("|"); let i = 0;
    el.innerHTML = `<span class="rot-word">${words[0]}</span>`;
    if (reduce) return;
    const id = setInterval(() => {
      if (!document.body.contains(el)) return clearInterval(id);
      const cur = el.firstElementChild; cur.classList.add("rot-out");
      i = (i + 1) % words.length;
      const nxt = document.createElement("span"); nxt.className = "rot-word rot-in"; nxt.textContent = words[i];
      el.appendChild(nxt); setTimeout(() => cur.remove(), 450);
    }, 2200);
  }

  // TextType: typewriter for fresh AI chat bubbles.
  function textType(el) {
    if (el.dataset.bitsDone) return; el.dataset.bitsDone = 1;
    const full = el.textContent; if (reduce || full.length > 400) return;
    el.textContent = ""; el.classList.add("typing-caret"); let i = 0;
    const id = setInterval(() => {
      i += 2; el.textContent = full.slice(0, i);
      const box = el.closest(".msgs"); if (box) box.scrollTop = box.scrollHeight;
      if (i >= full.length) { clearInterval(id); el.textContent = full; el.classList.remove("typing-caret"); }
    }, 18);
  }

  // AnimatedContent: fade/slide cards in as they enter the viewport, staggered.
  const io = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.08 }) : null;
  function reveal(root) {
    if (reduce || !io) return;
    root.querySelectorAll(".card, .insight, .situation, .quote, .tipbox").forEach((el, n) => {
      if (el.dataset.rv || el.closest(".chat")) return; el.dataset.rv = 1;
      el.classList.add("rv"); el.style.transitionDelay = Math.min(n, 10) * 45 + "ms"; io.observe(el);
    });
  }

  // SpotlightCard + TiltedCard + Magnet: one delegated pointer handler.
  if (fine && !reduce) {
    document.addEventListener("pointermove", (e) => {
      const card = e.target.closest(".card, .float-card");
      if (card) { const r = card.getBoundingClientRect(); card.style.setProperty("--mx", e.clientX - r.left + "px"); card.style.setProperty("--my", e.clientY - r.top + "px"); }
      const tilt = e.target.closest("[data-tilt]");
      if (tilt) {
        const r = tilt.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        tilt.style.transform = `perspective(900px) rotateX(${(-y * 9).toFixed(2)}deg) rotateY(${(x * 9).toFixed(2)}deg) translateY(-3px)`;
      }
      document.querySelectorAll("[data-magnet]").forEach((m) => {
        const r = m.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        const dx = e.clientX - cx, dy = e.clientY - cy, near = Math.hypot(dx, dy) < Math.max(r.width, r.height) * 0.9;
        m.style.transform = near ? `translate(${dx * 0.18}px, ${dy * 0.25}px)` : "";
      });
    }, { passive: true });
    document.addEventListener("pointerout", (e) => {
      const tilt = e.target.closest("[data-tilt]");
      if (tilt && !tilt.contains(e.relatedTarget)) tilt.style.transform = "";
    });
  }

  // ClickSpark: little burst of lines on every click.
  const cv = document.createElement("canvas"); cv.className = "spark-canvas"; document.body.appendChild(cv);
  const ctx = cv.getContext("2d"); let sparks = [], raf = 0;
  const size = () => { cv.width = innerWidth * devicePixelRatio; cv.height = innerHeight * devicePixelRatio; ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0); };
  size(); addEventListener("resize", size);
  function draw(t) {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    sparks = sparks.filter((s) => {
      const p = (t - s.t0) / 420; if (p >= 1) return false;
      const e = p * (2 - p), d = e * 22, len = 9 * (1 - e);
      ctx.strokeStyle = s.c; ctx.lineWidth = 2; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(s.x + d * Math.cos(s.a), s.y + d * Math.sin(s.a));
      ctx.lineTo(s.x + (d + len) * Math.cos(s.a), s.y + (d + len) * Math.sin(s.a)); ctx.stroke();
      return true;
    });
    raf = sparks.length ? requestAnimationFrame(draw) : 0;
  }
  if (!reduce) document.addEventListener("click", (e) => {
    const t0 = performance.now(); const c = ["#5b4bff", "#8b5cf6", "#ff4d6d", "#ff8a3d"][(Math.random() * 4) | 0];
    for (let i = 0; i < 8; i++) sparks.push({ x: e.clientX, y: e.clientY, a: (Math.PI * 2 * i) / 8, t0, c });
    if (!raf) raf = requestAnimationFrame(draw);
  });

  window.Bits = {
    enhance(root = document) {
      root.querySelectorAll("[data-blur]").forEach(blurText);
      root.querySelectorAll("[data-count]").forEach(countUp);
      root.querySelectorAll("[data-decrypt]").forEach(decrypt);
      root.querySelectorAll("[data-rotate]").forEach(rotating);
      root.querySelectorAll("[data-type]").forEach(textType);
      reveal(root);
    },
  };
})();
