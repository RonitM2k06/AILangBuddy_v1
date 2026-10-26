// Rewards (#/rewards) and Friends (#/friends) for learners. XP, levels, streaks, freezes, achievements and challenge rewards are all
// worked out by the server from what the learner has really done; this page only shows them and asks to claim a finished challenge
// (it never sends an amount). Friends are added with a code the other learner gave out; the server refuses all of it for children.
// "Local Confidence" stays the measure of how ready you feel; XP is just for fun.
(function () {
  const { api, errText, esc } = window.LBApi;
  const alive = (root) => document.body.contains(root);
  const note = (html) => `<div class="card" style="max-width:560px">${html}</div>`;
  const bar = (v, max) => `<div class="bar"><i style="width:${max ? Math.min(100, Math.round((100 * v) / max)) : 0}%"></i></div>`;

  function blocked(res, what) {
    if (res.status === 401) return note(`<h2>Sign in to see ${what}</h2><a class="btn btn-primary" href="#/profile">Sign in</a>`);
    if (res.status === 403) return note(`<h2>Not available for this account</h2><p class="muted">${what[0].toUpperCase() + what.slice(1)} are for teen and adult learner accounts.</p>`);
    if (res.status === 409) return note(`<h2>Set up your profile first</h2><a class="btn btn-primary" href="#/profile">Open profile</a>`);
    return null;
  }

  // ---------- rewards ----------
  async function mountRewards() {
    const el = document.getElementById("rewards-root"); if (!el) return;
    const [sum, ach, chal] = await Promise.all([api("GET", "/api/gamification"), api("GET", "/api/gamification/achievements"), api("GET", "/api/gamification/challenges")]);
    if (!alive(el)) return;
    const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">⭐ Rewards</div><h1>Your rewards</h1>
      <p class="sub">XP and streaks are just for fun. Your Local Confidence still shows how ready you feel.</p></div></div>${inner}`;
    const b = blocked(sum, "rewards");
    if (b) { el.innerHTML = shell(b); return; }
    if (!sum.ok) { el.innerHTML = shell(note(`<p class="muted">Couldn't load your rewards. Please try again.</p>`)); return; }
    let s = sum.data, a = ach.ok ? ach.data.achievements : [], c = chal.ok ? chal.data.challenges : [], msg = "";

    const draw = () => {
      const x = s.xp, st = s.streak;
      const span = x.next_level_at === null ? 1 : x.next_level_at - x.level_start;
      el.innerHTML = shell(`<div class="grid g3" style="margin-bottom:14px">
          <div class="card"><div class="muted">Level</div><div style="font-size:30px;font-weight:800">${x.level} · ${esc(x.rank)}</div>
            ${bar(x.into_level, span)}<div class="muted" style="font-size:13px">${x.total} XP${x.to_next === null ? "" : " · " + x.to_next + " to level " + (x.level + 1)}</div></div>
          <div class="card"><div class="muted">Streak</div><div style="font-size:30px;font-weight:800">🔥 ${st.current} ${st.current === 1 ? "day" : "days"}</div>
            <div class="muted" style="font-size:13px">Longest ${st.longest}${st.at_risk ? " · learn today to keep it!" : ""}${st.active_today ? " · done for today ✓" : ""}</div></div>
          <div class="card"><div class="muted">Streak freezes</div><div style="font-size:30px;font-weight:800">❄️ ${st.freezes} / ${st.max_freezes}</div>
            <div class="muted" style="font-size:13px">One is earned every ${st.freeze_every} days in a row. It covers a day you miss.</div></div></div>
        <div class="muted" style="margin-bottom:14px">Today: ${s.today.xp} of ${s.today.cap} XP · timezone ${esc(s.timezone)} <button class="btn btn-ghost btn-sm" data-tz>Use my device's timezone</button> <span id="rw-msg">${esc(msg)}</span></div>
        <h3>Challenges</h3><div class="grid g2" style="margin-bottom:14px">${c.map((ch) => `<div class="card"><div class="row between"><b>${esc(ch.title)}</b><span class="chip ${ch.status === "claimed" ? "ok" : ""}">${esc(ch.period)}</span></div>
            ${bar(ch.progress, ch.target)}<div class="row between" style="margin-top:6px"><span class="muted">${ch.progress} / ${ch.target} · +${ch.reward_xp} XP</span>
            ${ch.status === "claimable" ? `<button class="btn btn-primary btn-sm" data-claim="${ch.id}">Claim</button>` : ch.status === "claimed" ? `<span class="chip ok">Claimed ✓</span>` : ""}</div></div>`).join("") || `<div class="muted">No challenges right now.</div>`}</div>
        <h3>Achievements</h3><div class="grid g3">${a.map((x) => `<div class="card" style="${x.unlocked ? "" : "opacity:.65"}"><b>${x.unlocked ? "🏅" : "🔒"} ${esc(x.title)}</b>
            <div class="muted" style="font-size:13px">${esc(x.description)}</div>${x.unlocked ? `<div class="muted" style="font-size:12px">Unlocked ${esc(x.unlocked_at.slice(0, 10))}</div>` : `${bar(x.progress, x.target)}<div class="muted" style="font-size:12px">${x.progress} / ${x.target} ${esc(x.unit)}</div>`}</div>`).join("")}</div>
        <h3 style="margin-top:14px">Recent XP</h3>${s.recent.length ? s.recent.map((r) => `<div class="muted">+${r.xp} · ${esc(r.what)} · ${esc(r.day)}</div>`).join("") : `<div class="muted">Finish an exercise, lesson or listening activity to earn your first XP.</div>`}`);
    };

    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.claim) {
        const r = await api("POST", `/api/gamification/challenges/${encodeURIComponent(d.claim)}/claim`);
        msg = r.ok ? "Reward claimed ✓" : errText(r);
      } else if (d.tz !== undefined) {
        const zone = window.Intl ? window.Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC";
        const r = await api("PUT", "/api/gamification/settings", { timezone: zone });
        msg = r.ok ? "Timezone saved ✓" : errText(r);
      } else return;
      const [s2, a2, c2] = await Promise.all([api("GET", "/api/gamification"), api("GET", "/api/gamification/achievements"), api("GET", "/api/gamification/challenges")]);
      if (s2.ok) s = s2.data; if (a2.ok) a = a2.data.achievements; if (c2.ok) c = c2.data.challenges;
      draw();
    };
    draw();
  }

  // ---------- friends ----------
  async function mountFriends() {
    const el = document.getElementById("friends-root"); if (!el) return;
    const shell = (inner) => `<div class="page-head"><div><div class="eyebrow">👥 Friends</div><h1>Friends</h1><p class="sub">Add friends with their code and see who earns the most XP this week.</p></div></div>${inner}`;
    let period = "week", msg = "";
    const load = async () => {
      const [f, lb] = await Promise.all([api("GET", "/api/social/friends"), api("GET", `/api/social/leaderboard?period=${period}`)]);
      if (!alive(el)) return false;
      const b = blocked(f, "friends");
      if (b) { el.innerHTML = shell(b); return false; }
      if (!f.ok) { el.innerHTML = shell(note(`<p class="muted">Couldn't load friends. Please try again.</p>`)); return false; }
      const d = f.data, entries = lb.ok ? lb.data.entries : [];
      el.innerHTML = shell(`<div class="grid g2">
        <div class="card"><b>My friend code</b><div style="font-size:24px;font-weight:800;letter-spacing:3px;margin:8px 0" id="fr-mycode">${esc(d.my_friend_code)}</div>
          <div class="muted" style="font-size:13px">Give it to a friend your age. You can make a new one any time.</div><button class="btn btn-ghost btn-sm" data-newcode style="margin-top:8px">New code</button></div>
        <div class="card"><b>Add a friend</b><div class="row" style="margin-top:8px"><input id="fr-code" class="pc-in" placeholder="Their code" maxlength="40" autocomplete="off" autocapitalize="characters" spellcheck="false" aria-label="Your friend's code" /><button class="btn btn-primary" data-add>Send request</button></div>
          <div class="muted" id="fr-msg" style="margin-top:8px">${esc(msg)}</div></div></div>
        ${d.incoming.length ? `<h3 style="margin-top:14px">Requests for you</h3>${d.incoming.map((r) => `<div class="card row between" style="margin-bottom:8px"><span><b>${esc(r.display_name)}</b> wants to be friends</span>
          <span><button class="btn btn-primary btn-sm" data-accept="${r.id}">Accept</button> <button class="btn btn-ghost btn-sm" data-reject="${r.id}">Not now</button></span></div>`).join("")}` : ""}
        ${d.outgoing.length ? `<h3 style="margin-top:14px">Waiting for an answer</h3>${d.outgoing.map((r) => `<div class="muted">${esc(r.display_name)}</div>`).join("")}` : ""}
        <h3 style="margin-top:14px">My friends</h3>${d.friends.length ? d.friends.map((fr) => `<div class="card row between" style="margin-bottom:8px"><span><b>${esc(fr.display_name)}</b> <span class="muted">Level ${fr.level} · ${esc(fr.rank)}</span></span>
          <button class="btn btn-ghost btn-sm" data-remove="${fr.id}">Remove</button></div>`).join("") : `<div class="muted">No friends yet.</div>`}
        <h3 style="margin-top:14px">Leaderboard</h3><div class="row" style="margin-bottom:8px"><button class="btn ${period === "week" ? "btn-primary" : "btn-ghost"} btn-sm" data-period="week">This week</button>
          <button class="btn ${period === "all" ? "btn-primary" : "btn-ghost"} btn-sm" data-period="all">All time</button></div>
        <div class="card">${entries.map((e) => `<div class="row between" style="padding:4px 0${e.is_me ? ";font-weight:800" : ""}"><span>${e.rank}. ${esc(e.display_name)}${e.is_me ? " (you)" : ""} <span class="muted">Level ${e.level}</span></span><span>${e.xp} XP</span></div>`).join("")}</div>`);
      return true;
    };
    el.onclick = async (ev) => {
      const t = ev.target.closest("button"); if (!t) return;
      const d = t.dataset;
      if (d.add !== undefined) {
        const code = el.querySelector("#fr-code").value.trim();
        if (!code) { el.querySelector("#fr-msg").textContent = "Type your friend's code."; return; }
        const r = await api("POST", "/api/social/friends/requests", { code });
        msg = r.ok ? "Request sent ✓" : errText(r);
      } else if (d.accept) { const r = await api("POST", `/api/social/friends/requests/${encodeURIComponent(d.accept)}/accept`); msg = r.ok ? "You are now friends ✓" : errText(r); }
      else if (d.reject) { const r = await api("POST", `/api/social/friends/requests/${encodeURIComponent(d.reject)}/reject`); msg = r.ok ? "" : errText(r); }
      else if (d.remove) { const r = await api("DELETE", `/api/social/friends/${encodeURIComponent(d.remove)}`); msg = r.ok ? "" : errText(r); }
      else if (d.newcode !== undefined) { const r = await api("POST", "/api/social/friend-code"); msg = r.ok ? "New code made ✓" : errText(r); }
      else if (d.period) period = d.period;
      else return;
      await load();
    };
    await load();
  }

  window.RewardsView = { page() { setTimeout(mountRewards, 0); return `<div id="rewards-root"><div class="card muted">Loading…</div></div>`; } };
  window.FriendsView = { page() { setTimeout(mountFriends, 0); return `<div id="friends-root"><div class="card muted">Loading…</div></div>`; } };
})();
