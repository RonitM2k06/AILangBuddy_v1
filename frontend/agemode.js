// Age-aware experience. The server decides the mode (child / teen / adult) from the learner's profile; this only presents it.
// Child: a small, simple navigation and a game home. Teen: a "My Path" page added to the existing navigation. Adult: unchanged.
// Anonymous visitors and learners without a profile get no mode, so the prototype looks exactly as before for them.
// Admin (Phase 13): an account with the admin role gets only the admin console navigation, and nobody else is ever shown #/admin. This is presentation:
// every /api/admin/* call is authorised by the server, so a tampered client still gets 401/403.
(function () {
  const CHILD_NAV = [["#/kids", "🎮", "Adventure"], ["#/listening", "🎧", "Listen"], ["#/profile", "🙂", "Me"]];
  const CHILD_ROUTES = ["kids", "listening", "profile"];     // the routes a child is shown; anything else opens the adventure
  let info = null;
  let ready = false;                                   // true once the first refresh() has finished: until then we do not know who is looking, so #/admin is not redirected

  const mode = () => (info ? info.mode : null);
  function filterNav(list) {
    if (mode() === "admin") return window.AdminView.NAV;
    if (mode() === "child") return CHILD_NAV;
    if (mode() === "parent") { const out = list.filter((n) => !["#/rewards", "#/friends", "#/ai-tutor", "#/ai-roleplay", "#/ai-insights"].includes(n[0])); out.splice(1, 0, ["#/parent", "👪", "My Children"]); return out; }
    if (mode() === "teen") { const out = list.slice(); out.splice(1, 0, ["#/path", "🧭", "My Path"]); return out; }
    return list;
  }
  const HOME = { child: "kids", parent: "parent" };         // where a visitor who may not see the admin console is sent
  function routeFor(route) {
    if (mode() === "admin") return "admin";            // admins live in the console, whatever URL they typed
    if (route === "admin" && ready) {                  // anyone else is sent to their own home
      const home = HOME[mode()] || "";
      if (window.location && window.location.replace) window.location.replace("#/" + home);
      return home;
    }
    return mode() === "child" && !CHILD_ROUTES.includes(route) ? "kids" : route;
  }

  async function refresh() {
    const { api } = window.LBApi;
    const res = await api("GET", "/api/experience");
    info = res.ok ? res.data : null;
    if (res.status === 403) {                        // not a learner: a parent gets the family page in the navigation, an admin gets the console
      const me = await api("GET", "/api/auth/me");
      const roles = me.ok ? me.data.user.roles : [];
      info = roles.includes("admin") ? { mode: "admin", features: {} } : roles.includes("parent") ? { mode: "parent", features: {} } : null;
    }
    ready = true;
    const cls = document.body.classList;
    cls.remove("mode-child", "mode-teen", "mode-admin");
    if (mode() === "child" || mode() === "teen" || mode() === "admin") cls.add("mode-" + mode());
    return info;
  }

  window.AgeMode = { refresh, mode, filterNav, routeFor, features: () => (info ? info.features : {}) };
})();
