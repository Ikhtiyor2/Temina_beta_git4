(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const gate = document.getElementById("gate");
  const shell = document.getElementById("shell");
  const screen = document.getElementById("screen");
  const title = document.getElementById("title");
  const back = document.getElementById("back");
  const debug = document.body.dataset.debug === "1";
  const athlete = document.body.dataset.athlete || "";
  const fallbackPhoto = document.body.dataset.workout || "";
  function t(key, vars) {
    return (window.TeminaI18n && window.TeminaI18n.t) ? window.TeminaI18n.t(key, vars) : key;
  }
  function loc() {
    return (window.TeminaI18n && window.TeminaI18n.lang() === "uz") ? "uz-UZ" : "ru-RU";
  }
  function titles() {
    return {
      home: t("nav.home"),
      trainings: t("nav.trainings"),
      competitions: t("nav.competitions"),
      profile: t("nav.profile"),
    };
  }
  function scopes() {
    return [
      ["global", t("scope.global")],
      ["friends", t("scope.friends")],
      ["city", t("scope.city")],
      ["region", t("scope.region")],
      ["university", t("scope.university")],
      ["school", t("scope.school")],
    ];
  }
  const exercises = ["PUSHUP", "SQUAT", "PULLUP", "CRUNCH", "TABATA", "RUN"];
  function weekNames() {
    return t("week.days").split(",");
  }

  const state = {
    tab: "home",
    stack: [],
    questType: "daily",
    boardScope: "global",
    challengeFilter: "incoming",
    session: null,
    timer: null,
    runWatch: null,
  };

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function icon(name, size) {
    const s = size || 20;
    const paths = {
      "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
      "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
      flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
      zap: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
      footprints: '<path d="M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z"/><path d="M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z"/><path d="M16 17h4"/><path d="M4 13h4"/>',
      timer: '<path d="M10 2h4"/><path d="M12 14l3-3"/><circle cx="12" cy="14" r="8"/>',
      sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
      target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
      trophy: '<path d="M10 14.66v1.626a2 2 0 0 1-.976 1.696A5 5 0 0 0 7 21.978"/><path d="M14 14.66v1.626a2 2 0 0 0 .976 1.696A5 5 0 0 1 17 21.978"/><path d="M18 9h1.5a1 1 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z"/><path d="M6 9H4.5a1 1 0 0 1 0-5H6"/>',
      swords: '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/><line x1="19" x2="21" y1="21" y2="19"/><polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/><line x1="5" x2="9" y1="14" y2="18"/><line x1="7" x2="4" y1="17" y2="20"/><line x1="3" x2="5" y1="19" y2="21"/>',
      users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      medal: '<path d="M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15"/><path d="M11 12 5.12 2.2"/><path d="m13 12 5.88-9.8"/><path d="M8 7h8"/><circle cx="12" cy="17" r="5"/><path d="M12 18v-2h-.5"/>',
      check: '<path d="M20 6 9 17l-5-5"/>',
      crown: '<path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"/><path d="M5 21h14"/>',
      chevron: '<path d="m9 18 6-6-6-6"/>',
      settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
      logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><path d="M21 12H9"/>',
      pin: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
      plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
      send: '<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/>',
      pen: '<path d="M12 20h9"/><path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z"/>',
      brain: '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M19.938 10.5a4 4 0 0 1 .585.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M19.967 17.484A4 4 0 0 1 18 18"/>',
      star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
      lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
      cap: '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    };
    return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      (paths[name] || "") + "</svg>";
  }

  function csrf() {
    // Login rotates the cookie; the token rendered into the page is then stale.
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const input = document.querySelector("input[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  async function api(path, options) {
    const opts = options || {};
    const headers = { Accept: "application/json" };
    if (opts.body) {
      headers["Content-Type"] = "application/json";
      headers["X-CSRFToken"] = csrf();
    }
    const response = await fetch(path, {
      method: opts.method || "GET",
      credentials: "same-origin",
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      const error = new Error(data.detail || data.error || data.code || "request_failed");
      error.status = response.status;
      error.code = data.code;
      throw error;
    }
    return data;
  }

  function showGate(heading, text, mode) {
    shell.hidden = true;
    gate.hidden = false;
    document.getElementById("gateTitle").textContent = heading;
    document.getElementById("gateText").textContent = text;
    document.getElementById("gateRetry").hidden = mode !== "retry";
    document.getElementById("gateDemo").hidden = !(debug && mode === "login");
  }

  function openApp() {
    gate.hidden = true;
    shell.hidden = false;
    if (tg && tg.initData) {
      tg.ready();
      tg.expand();
      tg.setHeaderColor("#140f1c");
      tg.setBackgroundColor("#140f1c");
    }
    const dateEl = document.querySelector(".desktop-date");
    if (dateEl) {
      dateEl.textContent = new Date().toLocaleDateString(loc(), {
        weekday: "long", day: "numeric", month: "long",
      }).toUpperCase();
    }
    if (window.TeminaI18n) window.TeminaI18n.applyChrome();
    ensurePageDecor();
    render();
  }

  function current() {
    return state.stack.length ? state.stack[state.stack.length - 1] : { name: state.tab };
  }

  function setTab(tab) {
    state.tab = tab;
    state.stack = [];
    document.querySelectorAll(".nav-item").forEach(function (button) {
      button.classList.toggle("active", button.dataset.tab === tab);
    });
    if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
    render();
  }

  function push(name, heading, params) {
    state.stack.push({ name: name, title: heading, params: params || {} });
    render();
  }

  function showBack(on) {
    back.hidden = !on;
    if (tg && tg.BackButton) {
      if (on) tg.BackButton.show();
      else tg.BackButton.hide();
    }
  }

  function photo(url, index) {
    const fallback = index % 2 ? athlete : (fallbackPhoto || athlete);
    return esc(url || fallback);
  }

  function cover(url, index) {
    const fallback = photo("", index);
    return '<img src="' + photo(url, index) + '" alt="" onerror="this.onerror=null;this.src=\'' + fallback + '\'">';
  }

  function shortDate(value) {
    const date = new Date(value);
    if (!value || isNaN(date.getTime())) return String(value || "");
    return date.toLocaleDateString(loc(), { day: "numeric", month: "short" });
  }

  function initials(name) {
    return esc(String(name || "T").split(/\s+/).map(function (part) { return part[0] || ""; }).join("").slice(0, 2).toUpperCase());
  }

  function tgUser() {
    return (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || null;
  }

  function personName(me) {
    const u = tgUser();
    const fromTg = u ? [u.first_name, u.last_name].filter(Boolean).join(" ").trim() : "";
    return (me && me.displayName) || fromTg || (me && me.username) || t("athlete");
  }

  function personPhoto(me) {
    const u = tgUser();
    return (me && me.avatarUrl) || (u && u.photo_url) || "";
  }

  function isoDay(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + d;
  }

  function goalLine(value, goal, unit) {
    if (!goal) return esc(value || 0) + (unit ? " <small>" + unit + "</small>" : "");
    return esc(value || 0) + " <small>/ " + esc(goal) + (unit ? " " + unit : "") + "</small>";
  }

  function goalPct(value, goal) {
    if (!goal) return value ? 100 : 0;
    return Math.min(100, Math.round(((value || 0) / goal) * 100));
  }

  function face(entry, name) {
    const src = entry && entry.avatarUrl;
    if (src) {
      return '<img class="podium-avatar object-cover" src="' + esc(src) + '" alt="" referrerpolicy="no-referrer">';
    }
    return '<span class="podium-avatar">' + initials(name) + "</span>";
  }

  function heading(text, go, label) {
    return '<div class="section-heading"><h2>' + text + "</h2>" +
      (go ? '<button class="text-link" type="button" ' + go + ">" + (label || t("chrome.all")) + " " +
        icon("arrow-right", 13) + "</button>" : "") +
      "</div>";
  }

  function row(name, sub, attrs, extra, glyph) {
    return '<button class="row" type="button" ' + attrs + '><span class="row-icon">' +
      (glyph || icon("chevron", 17)) + "</span><div><h3>" +
      name + "</h3>" + (sub ? "<p>" + sub + "</p>" : "") + '</div><span class="row-action">' +
      (extra || icon("chevron", 17)) + "</span></button>";
  }

  function chip(id, key, label, active) {
    return '<button type="button" data-' + id + '="' + esc(key) + '"' +
      (active === key ? ' class="is-on"' : "") + ">" + esc(label) + "</button>";
  }

  function segments(id, items, active) {
    return '<div class="segments" role="tablist">' + items.map(function (item) {
      return '<button type="button" data-' + id + '="' + esc(item[0]) + '" class="' +
        (active === item[0] ? "on" : "") + '">' + esc(item[1]) + "</button>";
    }).join("") + "</div>";
  }

  function podium(entries) {
    const top = (entries || []).slice(0, 3);
    if (!top.length) return "";
    const order = [top[1] || null, top[0], top[2] || null];
    return '<div class="podium">' + order.map(function (entry, i) {
      if (!entry) return "<div></div>";
      const place = i === 1 ? 1 : i === 0 ? 2 : 3;
      const name = entry.displayName || entry.username || t("player");
      return '<button class="podium-col place-' + place + '" type="button" data-player="' +
        esc(entry.playerId) + '">' + (place === 1 ? '<span class="podium-crown">' + icon("crown", 22) + "</span>" : "") +
        face(entry, name) + "<strong>" + esc(name) +
        "</strong><small>" + esc(entry.totalXp || 0) + ' XP</small><span class="podium-step">' +
        place + "</span></button>";
    }).join("") + "</div>";
  }

  function duelCard(item, rival, mark) {
    const me = Number(item.myResult || item.challengerResult || 0);
    const them = Number(item.opponentResult || item.goalValue || 0);
    const share = Math.round((me / (me + them || 1)) * 100);
    return '<button class="duel" type="button" data-go="challenge" data-id="' + esc(item.id) +
      '"><div class="duel-top"><span class="duel-side"><span class="podium-avatar">' + t("chrome.you") + "</span><b>" +
      esc(me) + '</b></span><span class="duel-vs">VS</span><span class="duel-side"><b>' +
      esc(them) + '</b><span class="podium-avatar alt">' + esc(mark) +
      '</span></span></div><div class="duel-bar"><span style="width:' + share +
      '%"></span></div><div class="duel-meta"><span>' + esc(rival) + " · " +
      esc(item.exerciseType) + "</span><span>" + esc(item.status) + "</span></div></button>";
  }

  function friendCard(item) {
    const name = item.displayName || item.username || t("player");
    return '<div class="friend">' + face(item, name) + "<div><h3>" +
      esc(name) + "</h3><p>" + t("level.n", { n: item.level || 1 }) + "</p></div>" +
      '<button class="sport-button" type="button" data-go="create" data-id="' +
      esc(item.playerId) + '">' + t("friends.duel") + "</button></div>";
  }

  function shareTelegram(text) {
    const link = "https://t.me/share/url?url=" + encodeURIComponent(location.origin + "/app/") +
      "&text=" + encodeURIComponent(text);
    if (tg && tg.openTelegramLink && tg.initData) tg.openTelegramLink(link);
    else window.open(link, "_blank");
  }

  function cssStyle(s) {
    return Object.keys(s).map(function (key) {
      const name = key.replace(/[A-Z]/g, function (ch) { return "-" + ch.toLowerCase(); });
      let val = s[key];
      if (typeof val === "number" && name !== "opacity") val += "px";
      return name + ":" + val;
    }).join(";");
  }

  function decoLayer(kind, extraClass) {
    const shapes = DECOR[kind] || [];
    return '<div class="deco-layer' + (extraClass ? " " + extraClass : "") + '" aria-hidden="true">' +
      shapes.map(function (shape) {
        return '<span class="deco deco-' + shape.k + (shape.c ? " " + shape.c : "") +
          '" style="' + cssStyle(shape.s) + '"></span>';
      }).join("") + "</div>";
  }

  const DECOR = {
    page: [
      { k: "disc", c: "float", s: { width: 220, height: 220, top: "16%", right: -120, opacity: 0.5 } },
      { k: "ring", s: { width: 150, height: 150, top: "6%", left: -70, opacity: 0.22 } },
      { k: "arc", c: "spin violet", s: { width: 280, height: 280, bottom: "8%", right: -110, opacity: 0.55 } },
      { k: "hatch", c: "drift", s: { width: 190, height: 190, bottom: "30%", left: -100, opacity: 0.45 } },
      { k: "dots", s: { width: 60, height: 84, top: "42%", right: 18, opacity: 0.28 } },
      { k: "dots", s: { width: 48, height: 48, bottom: "16%", left: 22, opacity: 0.22 } },
      { k: "plus", c: "twinkle", s: { top: "24%", left: "7%" } },
      { k: "plus", c: "twinkle", s: { top: "64%", right: "9%", animationDelay: "1.2s" } },
      { k: "plus", c: "twinkle", s: { bottom: "9%", left: "38%", animationDelay: "2.1s" } },
    ],
    hero: [
      { k: "dots", s: { width: 60, height: 36, top: 24, left: 24, opacity: 0.8 } },
      { k: "ring", s: { width: 120, height: 120, top: "30%", right: -44, borderWidth: 4 } },
      { k: "disc", c: "float", s: { width: 170, height: 170, bottom: -80, right: -60, opacity: 0.9 } },
      { k: "hatch", s: { width: 120, height: 120, bottom: 30, right: 70, opacity: 0.55 } },
      { k: "plus", s: { top: 30, left: 108 } },
      { k: "plus", s: { top: "22%", right: 110 } },
    ],
    banner: [
      { k: "ring", s: { width: 92, height: 92, bottom: -34, right: 90, opacity: 0.55 } },
      { k: "dots", s: { width: 48, height: 36, top: 16, right: 20, opacity: 0.6 } },
      { k: "hatch", c: "light", s: { width: 120, height: 120, top: -50, right: -30, opacity: 0.45 } },
      { k: "plus", s: { bottom: 18, right: 34 } },
    ],
    cover: [
      { k: "disc", c: "float", s: { width: 180, height: 180, top: -70, right: -60 } },
      { k: "ring", s: { width: 88, height: 88, top: "40%", right: -34, opacity: 0.85 } },
      { k: "hatch", s: { width: 150, height: 150, bottom: -60, left: -50, opacity: 0.6 } },
      { k: "dots", c: "wide-only", s: { width: 72, height: 48, top: "38%", right: 84, opacity: 0.55 } },
      { k: "arc", c: "spin", s: { width: 220, height: 220, bottom: -120, right: "34%", opacity: 0.3 } },
      { k: "plus", c: "twinkle", s: { top: 26, left: "46%" } },
      { k: "plus", c: "twinkle", s: { bottom: 40, left: "30%", animationDelay: "1.4s" } },
    ],
  };

  function fmt(n) {
    return Number(n || 0).toLocaleString("ru-RU");
  }

  function ensurePageDecor() {
    if (!shell.querySelector(".bg-decor")) {
      shell.insertAdjacentHTML("afterbegin", decoLayer("page", "bg-decor"));
    }
  }

  function leader(entry) {
    const name = entry.displayName || entry.username || t("player");
    return '<button class="leader' + (entry.isMe ? " me" : "") + '" type="button" data-player="' +
      esc(entry.playerId) + '"><span class="rank">' + esc(entry.rank || "·") +
      "</span>" + face(entry, name) + "<div><div class=\"leader-name\">" +
      esc(name) + '</div><div class="leader-level">' + t("level.n", { n: entry.level }) +
      '</div></div><span class="leader-xp">' + esc(entry.totalXp || 0) + " XP</span></button>";
  }

  function bindClicks(selector, fn) {
    screen.querySelectorAll(selector).forEach(function (node) {
      node.addEventListener("click", function () { fn(node); });
    });
  }

  function bindNav(root) {
    (root || screen).querySelectorAll("[data-go]").forEach(function (node) {
      if (node.dataset.bound) return;
      node.dataset.bound = "1";
      node.addEventListener("click", function () {
        const go = node.dataset.go;
        const id = node.dataset.id;
        if (go === "workout") push("workout", t("screen.workout"), { id: id });
        else if (go === "run") push("run", t("screen.run"));
        else if (go === "week") push("week", t("screen.week"));
        else if (go === "stats") push("stats", t("screen.stats"), { metric: id || "calories" });
        else if (go === "board") push("board", t("screen.board"));
        else if (go === "friends") push("friends", t("screen.friends"));
        else if (go === "challenges") push("challenges", t("screen.challenges"));
        else if (go === "create") push("create", t("screen.create"), { opponentId: id });
        else if (go === "challenge") push("challenge", t("screen.challenge"), { id: id });
        else if (go === "seasons") push("seasons", t("screen.seasons"));
        else if (go === "badges") push("badges", t("screen.badges"));
        else if (go === "player") push("player", t("screen.player"), { id: id });
        else if (go === "quests") push("quests", t("screen.quests"));
        else if (go === "search") push("search", t("screen.search"));
        else if (go === "trainings") setTab("trainings");
        else if (go === "profile") setTab("profile");
        else if (go === "edit") push("edit", t("screen.edit"));
        else if (go === "location") push("location", t("screen.location"));
        else if (go === "settings") push("settings", t("screen.settings"));
      });
    });
  }

  async function render() {
    if (!state.session) clearInterval(state.timer);
    const page = current();
    const headingText = page.title || titles()[state.tab];
    title.textContent = headingText;
    const nested = Boolean(state.stack.length);
    const focused = Boolean(state.session);
    const camLive = Boolean(state.session && state.session.kind === "workout" && state.session.wantsCamera);
    shell.classList.toggle("is-root", !nested && !focused);
    shell.classList.toggle("is-focus", focused || nested);
    shell.classList.toggle("is-cam", camLive);
    const pageDecor = shell.querySelector(".bg-decor");
    if (pageDecor) pageDecor.hidden = focused;
    showBack(false);
    screen.className = camLive ? "session-cam" : ("entrance" + (nested || state.tab !== "home" ? " content-width" : ""));
    screen.innerHTML = '<p class="muted">' + t("loading") + "</p>";
    try {
      if (state.session && state.session.kind === "workout") renderWorkoutSession();
      else if (state.session && state.session.kind === "run") renderRunSession();
      else if (page.name === "workout") await renderWorkout(page.params.id);
      else if (page.name === "run") await renderRun();
      else if (page.name === "stats") await renderStats(page.params.metric);
      else if (page.name === "week") await renderWeek();
      else if (page.name === "board") await renderBoard();
      else if (page.name === "friends") await renderFriends();
      else if (page.name === "player") await renderPlayer(page.params.id);
      else if (page.name === "challenges") await renderChallenges();
      else if (page.name === "challenge") await renderChallenge(page.params.id);
      else if (page.name === "create") await renderCreateChallenge(page.params.opponentId);
      else if (page.name === "seasons") await renderSeasons();
      else if (page.name === "badges") await renderBadges();
      else if (page.name === "quests") await renderQuests();
      else if (page.name === "search") await renderSearch();
      else if (page.name === "edit") await renderEditProfile(false);
      else if (page.name === "location") await renderEditProfile(true);
      else if (page.name === "settings") await renderSettings();
      else if (state.tab === "home") await renderHome();
      else if (state.tab === "trainings") await renderWorkouts();
      else if (state.tab === "competitions") await renderCompete();
      else await renderProfile();
    } catch (error) {
      screen.innerHTML = '<p class="notice">' + esc(error.message || t("loadFail")) + "</p>";
    }
    if (nested && !state.session && !screen.querySelector(".nested-header")) {
      screen.insertAdjacentHTML("afterbegin",
        '<div class="nested-header"><button type="button" class="icon-control" id="nestedBack" aria-label="' + t("chrome.back") + '">' +
        icon("arrow-left", 20) + "</button><h1>" + esc(headingText) + "</h1></div>");
      document.getElementById("nestedBack").addEventListener("click", goBack);
    }
  }

  async function renderHome() {
    const data = await api("/api/v1/dashboard/");
    const me = await api("/api/v1/users/me/");
    const board = await api("/api/v1/leaderboard/?limit=3").catch(function () { return { entries: [] }; });
    const week = await api("/api/v1/week-plan/current/").catch(function () { return { weekPlan: null }; });
    const metrics = data.metrics || {};
    const featured = data.featuredWorkout;
    const name = personName(Object.assign({}, data.profile || {}, me));
    const calGoal = metrics.calorieGoal || 0;
    const stepGoal = metrics.stepsGoal || 0;
    const actGoal = metrics.activityGoal || 0;
    const calPct = goalPct(metrics.caloriesToday, calGoal);
    const stepPct = goalPct(metrics.stepsToday, stepGoal);
    const actPct = goalPct(metrics.activeMinutes, actGoal);
    const days = (week.weekPlan && week.weekPlan.days) || [];
    const trained = {};
    (metrics.workoutDatesThisWeek || []).forEach(function (day) { trained[day] = true; });
    const done = weekNames().filter(function (_, i) {
      const now = new Date();
      const monday = new Date(now);
      monday.setDate(now.getDate() - ((now.getDay() + 6) % 7) + i);
      const plan = days[i];
      return (plan && plan.completed) || trained[isoDay(monday)];
    }).length;
    screen.innerHTML =
      '<div class="greeting"><div><p class="eyebrow">' + t("home.kicker") + "</p>" +
      "<h1>" + t("home.hello", { name: esc(name) }) + ' <span class="text-primary">✦</span></h1></div>' +
      '<button class="streak" type="button" data-go="profile">' + icon("flame", 17) + " " +
      t("home.streak", { n: metrics.workoutStreak || me.workoutStreak || 0 }) + "</button></div>" +
      '<section class="hero"><img src="' + photo(athlete) + '" alt="' + t("home.heroAlt") + '">' +
      decoLayer("hero") +
      '<div class="hero-copy"><div class="hero-label">' + icon("zap", 12) + " " + t("home.heroLabel") + "</div>" +
      "<h2>" + t("home.heroTitle1") + "<br>" + t("home.heroTitle2") + " <span>" + t("home.heroTitle3") + "</span></h2>" +
      "<p>" + t("home.heroText") + "</p>" +
      '<button class="sport-button" type="button" data-go="workout" data-id="' + esc((featured && featured.id) || "") +
      '">' + t("home.start") + " " + icon("arrow-right", 16) + "</button></div>" +
      '<span class="hero-tag sticker"><span>Make your move ↗</span></span></section>' +
      heading(t("home.activity"), 'data-go="stats" data-id="calories"', t("home.today")) +
      '<div class="stats-grid">' +
        '<button class="stat" type="button" data-go="stats" data-id="calories"><div class="stat-icon">' + icon("flame", 22) +
        '</div><div class="flex-1"><p class="stat-name">' + t("home.cal") + '</p><p class="stat-value">' +
        goalLine(metrics.caloriesToday, calGoal, t("unit.kcal")) + "</p>" +
        '<div class="progress-track"><span style="width:' + calPct + '%"></span></div></div></button>' +
        '<button class="stat" type="button" data-go="stats" data-id="steps"><div class="stat-icon">' + icon("footprints", 22) +
        '</div><div class="flex-1"><p class="stat-name">' + t("home.steps") + '</p><p class="stat-value">' +
        goalLine(metrics.stepsToday, stepGoal, "") + "</p>" +
        '<div class="progress-track"><span style="width:' + stepPct + '%"></span></div></div></button>' +
        '<button class="stat" type="button" data-go="stats" data-id="activity"><div class="stat-icon">' + icon("timer", 22) +
        '</div><div class="flex-1"><p class="stat-name">' + t("home.active") + '</p><p class="stat-value">' +
        goalLine(metrics.activeMinutes, actGoal, t("unit.min")) + "</p>" +
        '<div class="progress-track"><span style="width:' + actPct + '%"></span></div></div></button>' +
      "</div>" +
      '<div class="home-columns"><section>' +
      heading(t("home.more"), 'data-go="run"', t("home.run")) +
      '<div class="quick-grid"><button class="quick-card ai" type="button" data-go="week">' +
      icon("sparkles", 21) + icon("arrow-right", 16).replace("<svg ", '<svg class="card-arrow" ') +
      "<h3>" + t("home.aiTitle") + "</h3><p>" + t("home.aiText") + "</p></button>" +
      '<button class="quick-card" type="button" data-go="quests">' +
      icon("target", 21).replace("<svg ", '<svg class="text-lime" ') +
      icon("arrow-right", 16).replace("<svg ", '<svg class="card-arrow text-muted-foreground" ') +
      "<h3>" + t("home.questTitle") + "</h3><p>" + t("home.questText") + "</p></button></div></section><section>" +
      heading(t("home.yourWeek"), 'data-go="week"', t("home.allPlan")) +
      '<button class="week-card block" type="button" data-go="week"><div class="week-card-top"><span>' + t("week.this") +
      "</span><strong>" + t("week.of", { done: done, total: days.length || 7 }) + "</strong></div><div class=\"week-days\">" +
      weekNames().map(function (label, i) {
        const now = new Date();
        const monday = new Date(now);
        monday.setDate(now.getDate() - ((now.getDay() + 6) % 7) + i);
        const day = days[i];
        const finished = (day && day.completed) || trained[isoDay(monday)];
        const cls = finished ? "done" : (i === (new Date().getDay() + 6) % 7 ? "current" : "");
        return '<span class="day">' + label + '<span class="day-dot ' + cls + '">' +
          (finished ? icon("check", 14) : (i + 1)) + "</span></span>";
      }).join("") + '</div><p class="week-caption">' + icon("flame", 12) +
      (done
        ? t("week.captionDone", { n: done, word: window.TeminaI18n.plural(done, "week.one", "week.few", "week.many") })
        : t("week.captionEmpty")) +
      "</p></button></section></div>" +
      '<div class="dashboard-bottom"><section>' +
      heading(t("home.recent"), 'data-go="trainings"', t("home.history")) +
      recentList(data.recentWorkouts || []) + "</section><section>" +
      heading(t("home.top"), 'data-go="board"', t("home.rating")) +
      '<div class="leader-list">' + (board.entries || []).map(leader).join("") + "</div></section></div>";
    bindNav();
    bindClicks("[data-player]", function (node) { push("player", t("screen.player"), { id: node.dataset.player }); });
    document.querySelector("[data-go=profile]") && document.querySelector(".streak").addEventListener("click", function () { setTab("profile"); });
  }

  function recentList(items) {
    if (!items.length) return '<p class="notice">' + t("home.noWorkouts") + "</p>";
    return '<div class="workout-list">' + items.map(function (item, i) {
      return '<div class="workout-item">' + cover(fallbackPhoto, i) + "<div><h3>" +
        esc(item.exercise) + "</h3><p>" + t("home.reps", { n: item.reps, date: shortDate(item.date) }) + "</p></div></div>";
    }).join("") + "</div>";
  }

  async function renderWorkouts() {
    const data = await api("/api/v1/workouts/");
    const workouts = data.workouts || [];
    const tabata = workouts.find(function (item) { return (item.parentType || "").toUpperCase() === "TABATA"; });
    screen.innerHTML =
      '<p class="eyebrow">' + t("train.kicker") + '</p><h1 class="page-title">' + t("nav.trainings") + "</h1>" +
      '<button class="feature-banner" type="button" data-go="workout" data-id="' + esc((tabata && tabata.id) || "") +
      '">' + decoLayer("banner") +
      '<div><span class="eyebrow text-foreground">' + t("train.tabataKicker") + "</span>" +
      " <h2>" + t("train.tabataTitle") + "</h2><p>" + t("train.tabataText") + "</p></div>" +
      icon("timer", 42) + "</button>" +
      heading(t("train.pick")) +
      '<div class="catalog-grid">' + workouts.map(function (workout, i) {
        return '<button class="catalog-card" type="button" data-go="workout" data-id="' + esc(workout.id) +
          '">' + cover(workout.imageUrl, i) + '<div class="catalog-card-content"><div class="flex justify-between items-center"><h3>' +
          esc(workout.title) + "</h3>" + icon("arrow-right", 18) + "</div><p>" +
          t("train.meta", { min: workout.durationMin, cal: workout.calories }) + "</p></div></button>";
      }).join("") + "</div>";
    bindNav();
  }

  async function renderWorkout(id) {
    const workout = await api("/api/v1/workouts/" + encodeURIComponent(id) + "/");
    const moves = (workout.exercises || []).map(function (exercise) {
      const name = exercise.title || exercise.name || exercise.id;
      const dose = exercise.sets && exercise.reps ? exercise.sets + " × " + exercise.reps : "";
      return row(esc(name), esc(dose), "");
    }).join("");
    screen.innerHTML =
      cover(workout.imageUrl, 1).replace("<img ", '<img class="detail-photo" ') +
      '<span class="chip">' + esc(workout.difficulty || t("train.kind")) + "</span>" +
      '<h2 class="page-title" style="margin-top:12px">' + esc(workout.title) + "</h2>" +
      '<p class="detail-summary">' + esc(workout.subtitle || "") + "</p>" +
      '<div class="detail-metrics"><div><strong>' + esc(workout.durationMin) + "</strong><small>" + t("train.minutes") + "</small></div>" +
      "<div><strong>" + esc(workout.calories) + "</strong><small>" + t("unit.kcal") + "</small></div></div>" +
      heading(t("train.program")) + moves +
      '<button class="full-button" id="startWorkout" type="button">' + t("train.start") + "</button>";
    document.getElementById("startWorkout").addEventListener("click", function () { startWorkout(workout); });
  }

  function workoutUsesCamera(workout) {
    if (!workout || workout.supportsAiCounter === false) return false;
    const kind = String(workout.parentType || workout.aiExerciseType || "").toUpperCase();
    return kind === "PUSHUP" || kind === "SQUAT" || kind === "PULLUP" || kind === "CRUNCH" || kind === "PLANK";
  }

  function loadScriptOnce(src) {
    return new Promise(function (resolve, reject) {
      const found = document.querySelector('script[data-temina-src="' + src + '"]');
      if (found) {
        if (found.getAttribute("data-temina-loaded") === "1") return resolve();
        found.addEventListener("load", function () { resolve(); }, { once: true });
        found.addEventListener("error", reject, { once: true });
        return;
      }
      const script = document.createElement("script");
      const timeout = setTimeout(function () { fail(); }, 20000);
      function fail() {
        clearTimeout(timeout);
        script.remove();
        script.dispatchEvent(new Event("error"));
        reject(new Error("script_load_failed"));
      }
      script.src = src;
      script.setAttribute("data-temina-src", src);
      script.onload = function () { clearTimeout(timeout); script.setAttribute("data-temina-loaded", "1"); resolve(); };
      script.addEventListener("error", function () {
        clearTimeout(timeout);
        script.remove();
        reject(new Error("script_load_failed"));
      }, { once: true });
      document.head.appendChild(script);
    });
  }

  function ensurePoseLibs() {
    return loadScriptOnce("https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js")
      .then(function () { return loadScriptOnce("https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"); })
      .then(function () { return loadScriptOnce("https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"); })
      .then(function () { return loadScriptOnce("/static/js/mediapipe-client.js?v=bot12"); })
      .then(function () { return loadScriptOnce("/static/js/temina-exercise-detector.js?v=bot12"); })
      .then(function () { return loadScriptOnce("/static/js/temina-camera-pose.js?v=bot15"); });
  }

  function requestCameraStream() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error("no-media"));
    }
    return navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1280, max: 1920 }, height: { ideal: 720, max: 1080 } },
      audio: false,
    });
  }

  function stopCameraSession(session) {
    if (!session) return;
    if (session.camHandle && typeof session.camHandle.cancel === "function") {
      session.camHandle.cancel();
    }
    session.camHandle = null;
    if (session.stream) session.stream.getTracks().forEach(function (track) { track.stop(); });
    session.stream = null;
  }

  function cameraError(session, message) {
    if (state.session !== session) return;
    session.camError = message;
    const statusEl = document.getElementById("camStatus");
    if (statusEl) statusEl.textContent = message;
    const overlay = document.getElementById("camOverlay");
    if (overlay) {
      overlay.classList.add("temina-cp-overlay--visible", "temina-cp-overlay--error");
      overlay.querySelector(".temina-cp-overlay-title").textContent = t("train.camErr");
      overlay.querySelector(".temina-cp-overlay-sub").textContent = message;
    }
    const retry = document.getElementById("camRetryButton");
    if (retry) retry.hidden = false;
  }

  async function prepareWorkoutCamera(session) {
    if (session.cameraStarting) return;
    session.cameraStarting = true;
    const retry = document.getElementById("camRetryButton");
    if (retry) retry.hidden = true;
    const libs = ensurePoseLibs().then(function () { return null; }, function (err) { return err; });
    try {
      // Request access from the tap, but show the session before awaiting permission or AI.
      const stream = await requestCameraStream();
      if (state.session !== session || session.finishing) { stream.getTracks().forEach(function (track) { track.stop(); }); return; }
      session.stream = stream;
      const video = document.getElementById("camVideo");
      video.srcObject = stream;
      video.play().catch(function () {});
      document.getElementById("camStatus").textContent = t("train.camAi");
      const libError = await libs;
      if (state.session !== session || session.finishing) return;
      if (libError) { cameraError(session, t("train.camMissing")); return; }
      attachWorkoutCamera();
    } catch (error) {
      cameraError(session, t("train.camDenied"));
    } finally {
      session.cameraStarting = false;
    }
  }

  function drawPoseFrame(canvas, results) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!results.poseLandmarks) return;
    ctx.save();
    ctx.scale(-1, 1);
    ctx.translate(-canvas.width, 0);
    if (window.POSE_CONNECTIONS) {
      const lm = results.poseLandmarks;
      for (let c = 0; c < window.POSE_CONNECTIONS.length; c++) {
        const pair = window.POSE_CONNECTIONS[c];
        const a = lm[pair[0]], b = lm[pair[1]];
        if (!a || !b) continue;
        ctx.strokeStyle = "rgba(200,255,62,0.9)";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(a.x * canvas.width, a.y * canvas.height);
        ctx.lineTo(b.x * canvas.width, b.y * canvas.height);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  function attachWorkoutCamera() {
    const session = state.session;
    if (!session || !session.wantsCamera) return;
    const video = document.getElementById("camVideo");
    const canvas = document.getElementById("camCanvas");
    const overlay = document.getElementById("camOverlay");
    const statusEl = document.getElementById("camStatus");
    if (!video || !canvas) return;
    if (!session.stream) {
      if (statusEl) statusEl.textContent = session.camError || t("train.camDenied");
      if (overlay) {
        overlay.classList.add("temina-cp-overlay--visible", "temina-cp-overlay--error");
        const titleEl = overlay.querySelector(".temina-cp-overlay-title");
        const subEl = overlay.querySelector(".temina-cp-overlay-sub");
        if (titleEl) titleEl.textContent = t("train.camErr");
        if (subEl) subEl.textContent = session.camError || t("train.camDenied");
      }
      return;
    }
    if (!window.TeminaCameraPose) {
      if (statusEl) statusEl.textContent = t("train.camMissing");
      return;
    }
    if (session.camHandle && typeof session.camHandle.cancel === "function") session.camHandle.cancel();
    if (window.TeminaExerciseDetector) {
      const i18nLang = window.TeminaI18n && typeof window.TeminaI18n.lang === "function" ? window.TeminaI18n.lang() : "ru";
      session.detector = window.TeminaExerciseDetector.create(session.exercise, i18nLang === "en" ? "en" : "ru");
      session.detector.reset();
    }
    canvas.style.background = "transparent";
    session.camHandle = window.TeminaCameraPose.launch({
      video: video,
      canvas: canvas,
      loadingOverlay: overlay,
      stream: session.stream || null,
      strings: {
        starting: t("train.camStart"),
        cameraPrompt: t("train.camPrompt"),
        cameraReady: t("train.camAi"),
        ready: t("train.camReady"),
        permissionDenied: t("train.camDenied"),
        noCamera: t("train.camNone"),
        notSupported: t("train.camMissing"),
        notLoaded: t("train.camMissing"),
        genericError: t("train.camErr"),
        overlayLoadTitle: t("train.camStart"),
        overlayAiTitle: t("train.camAi"),
        overlayErrorTitle: t("train.camErr"),
      },
      onRetryRequest: function () { stopCameraSession(session); prepareWorkoutCamera(session); },
      onError: function (error) { cameraError(session, error.message || t("train.camErr")); },
      onResults: function (results) {
        drawPoseFrame(canvas, results);
        const live = state.session;
        if (!live || !live.detector) return;
        const out = live.detector.process(results.poseLandmarks);
        live.reps = live.detector.getCount();
        const repsEl = document.getElementById("camReps");
        if (repsEl) repsEl.textContent = String(live.reps || 0);
        if (statusEl && out && out.feedback) statusEl.textContent = out.feedback;
        const coach = document.getElementById("camCoach");
        if (coach) {
          const err = out && out.errors && out.errors[0];
          coach.textContent = err ? (err.message || "") : "";
        }
      },
      onStatus: function (phase) {
        if (!statusEl) return;
        if (phase === "running") statusEl.textContent = t("train.camReady");
        else if (phase === "camera_live") statusEl.textContent = t("train.camAi");
        else if (phase === "error") statusEl.textContent = t("train.camErr");
        else statusEl.textContent = t("train.camStart");
      },
    });
  }

  async function startWorkout(workout) {
    if (state.session) return;
    const wantsCamera = workoutUsesCamera(workout);
    state.session = {
      kind: "workout",
      id: null,
      title: workout.title,
      exercise: String(workout.parentType || workout.aiExerciseType || "PUSHUP").toUpperCase(),
      startedAt: Date.now(),
      calories: workout.calories,
      minutes: workout.durationMin,
      reps: 0,
      stage: null,
      wantsCamera: wantsCamera,
      stream: null,
      camError: "",
      camHandle: null,
      detector: null,
    };
    const session = state.session;
    render();
    if (wantsCamera) prepareWorkoutCamera(session);
    try {
      const started = await api("/api/v1/workouts/" + encodeURIComponent(workout.id) + "/start/", { method: "POST", body: {} });
      if (!started.sessionId) throw new Error(t("loadFail"));
      if (state.session !== session) return;
      session.id = started.sessionId;
      const finish = document.getElementById("finish");
      if (finish) finish.disabled = false;
    } catch (error) {
      if (state.session !== session) return;
      stopCameraSession(session);
      clearInterval(state.timer);
      state.session = null;
      await render();
      const message = document.createElement("p");
      message.className = "notice";
      message.textContent = t("loadFail") + ": " + error.message;
      screen.prepend(message);
    }
  }

  function renderWorkoutSession() {
    clearInterval(state.timer);
    const session = state.session;
    title.textContent = session.title;
    if (session.wantsCamera) {
      screen.innerHTML =
        '<div class="cam-stage" id="camStage">' +
        '<video id="camVideo" playsinline muted autoplay></video>' +
        '<canvas id="camCanvas"></canvas>' +
        '<div id="camOverlay" class="temina-cp-overlay temina-cp-overlay--visible" aria-hidden="false">' +
        '<div class="temina-cp-overlay-card"><div class="temina-cp-spinner-wrap"><div class="temina-cp-spinner"></div></div>' +
        '<p class="temina-cp-overlay-title">' + t("train.camStart") + "</p>" +
        '<p class="temina-cp-overlay-sub">' + t("train.camPrompt") + "</p></div></div>" +
        '<p class="cam-status" id="camStatus">' + (session.camError || t("train.camStart")) + "</p>" +
        '<div class="cam-shade"></div>' +
        '<div class="cam-hud">' +
        '<p class="cam-count" id="camReps">' + (session.reps || 0) + "</p>" +
        '<p class="cam-clock" id="clock">00:00</p>' +
        '<p class="cam-coach" id="camCoach"></p>' +
        '<button class="full-button cam-finish" id="finish" type="button">' + t("train.finish") + "</button>" +
        "</div></div>" +
        '<div id="camRetry"></div>';
    } else {
      screen.innerHTML =
        '<p class="eyebrow">' + t("train.live") + '</p>' +
        '<p class="session-number" id="clock">00:00</p>' +
        '<p class="notice">' + t("train.hold") + "</p>" +
        '<button class="full-button" id="finish" type="button">' + t("train.finish") + "</button>";
    }
    tick();
    state.timer = setInterval(tick, 1000);
    document.getElementById("finish").addEventListener("click", finishWorkout);
    document.getElementById("finish").disabled = !session.id;
    if (session.wantsCamera) {
      const retry = document.createElement("button");
      retry.id = "camRetryButton";
      retry.className = "full-button cam-finish";
      retry.textContent = t("gate.retry");
      retry.hidden = true;
      retry.addEventListener("click", function () { stopCameraSession(session); prepareWorkoutCamera(session); });
      document.querySelector(".cam-hud").prepend(retry);
    }
  }

  function tick() {
    const node = document.getElementById("clock");
    if (!node || !state.session) return;
    const seconds = Math.floor((Date.now() - state.session.startedAt) / 1000);
    node.textContent = String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
  }

  async function finishWorkout() {
    const session = state.session;
    if (!session || !session.id || session.finishing) return;
    session.finishing = true;
    document.getElementById("finish").disabled = true;
    const durationSec = Math.max(1, Math.floor((Date.now() - session.startedAt) / 1000));
    const calories = Math.round((session.calories || 0) * (durationSec / Math.max(60, (session.minutes || 1) * 60)));
    clearInterval(state.timer);
    stopCameraSession(session);
    const integrity = session.detector && session.detector.getIntegrity ? session.detector.getIntegrity() : {};
    const reps = session.detector && session.detector.getCount ? session.detector.getCount() : (session.reps || 0);
    let done;
    try {
      done = await api("/api/v1/workout-sessions/" + session.id + "/finish/", {
      method: "POST",
      body: {
        durationSec: durationSec,
        calories: calories,
        reps: reps,
        integrity: integrity,
        errorsCount: integrity.critical_violations || 0,
      },
      });
    } catch (error) {
      session.finishing = false;
      const finish = document.getElementById("finish");
      if (finish) finish.disabled = false;
      const message = document.createElement("p");
      message.className = "notice";
      message.textContent = t("loadFail") + ": " + error.message;
      (document.querySelector(".cam-hud") || screen).appendChild(message);
      return;
    }
    const challengeId = session.challengeId;
    state.session = null;
    shell.classList.remove("is-cam");
    screen.className = "entrance";
    if (challengeId && done.sessionId && (done.reps || 0) > 0) {
      try {
        await api("/api/v1/challenges/" + challengeId + "/submit/", {
          method: "POST",
          body: { result: done.reps, sessionId: done.sessionId },
        });
      } catch (error) { /* keep result */ }
    }
    screen.innerHTML = '<div class="empty-state"><h2>' + t("train.done") + "</h2><p>" + t("train.xp", { n: done.xpEarned || 0 }) + "</p></div>";
    setTimeout(function () { state.stack = []; setTab("home"); }, 900);
  }

  async function renderRun() {
    const history = await api("/api/v1/runs/history/?limit=8");
    const runs = history.runs || [];
    screen.innerHTML =
      '<div class="empty-state"><h2>' + t("run.ready") + "</h2><p>" + t("run.hint") + "</p></div>" +
      '<button class="full-button" id="startRun" type="button">' + t("run.start") + "</button>" +
      (runs.length ? heading(t("home.history")) + runs.map(function (run) {
        return row(esc(run.status), t("run.row", { km: run.distanceKm || 0, sec: run.durationSec || 0 }), "");
      }).join("") : "");
    document.getElementById("startRun").addEventListener("click", startRun);
  }

  async function startRun() {
    const run = await api("/api/v1/runs/start/", { method: "POST", body: {} });
    state.session = { kind: "run", id: run.runId, startedAt: Date.now(), paused: false };
    if (navigator.geolocation) {
      state.runWatch = navigator.geolocation.watchPosition(function (pos) {
        api("/api/v1/runs/" + state.session.id + "/track/", {
          method: "PATCH",
          body: {
            points: [{
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              timestamp: new Date().toISOString(),
              accuracy: pos.coords.accuracy,
              speedMps: pos.coords.speed,
            }],
          },
        }).catch(function () {});
      }, function () {}, { enableHighAccuracy: true });
    }
    render();
  }

  function renderRunSession() {
    clearInterval(state.timer);
    const session = state.session;
    screen.innerHTML =
      '<p class="eyebrow">' + (session.paused ? t("run.paused") : t("run.live")) + '</p><p class="session-number" id="clock">00:00</p>' +
      '<div class="actions"><button class="sport-button" id="pauseRun" type="button">' +
      (session.paused ? t("run.resume") : t("run.pause")) +
      '</button><button class="sport-button ghost" id="finishRun" type="button">' + t("run.finish") + "</button></div>";
    tick();
    state.timer = setInterval(tick, 1000);
    document.getElementById("pauseRun").addEventListener("click", toggleRun);
    document.getElementById("finishRun").addEventListener("click", finishRun);
  }

  async function toggleRun() {
    const session = state.session;
    if (session.paused) {
      await api("/api/v1/runs/" + session.id + "/resume/", { method: "POST", body: {} });
      session.paused = false;
    } else {
      await api("/api/v1/runs/" + session.id + "/pause/", { method: "POST", body: {} });
      session.paused = true;
    }
    render();
  }

  async function finishRun() {
    const session = state.session;
    if (state.runWatch != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(state.runWatch);
      state.runWatch = null;
    }
    clearInterval(state.timer);
    const done = await api("/api/v1/runs/" + session.id + "/finish/", { method: "POST", body: {} });
    state.session = null;
    screen.innerHTML = '<div class="empty-state"><h2>' + t("run.done") + "</h2><p>" +
      t("run.doneMeta", { xp: done.xpEarned || 0, km: done.distanceKm || 0 }) + "</p></div>";
    setTimeout(function () { state.stack = []; setTab("home"); }, 900);
  }

  async function renderStats(metricName) {
    const data = await api("/api/v1/stats/" + encodeURIComponent(metricName) + "/?period=week");
    const points = data.points || [];
    const max = Math.max.apply(null, points.map(function (point) { return point.value || 0; }).concat([1]));
    screen.innerHTML =
      '<p class="eyebrow">' + t("stats.week") + '</p><p class="session-number">' + esc(Math.round(data.total || 0)) +
      ' <span style="font-size:18px;color:var(--muted-foreground)">' + esc(data.unit || metricName) + "</span></p>" +
      '<div class="bars">' + points.map(function (point) {
        const h = Math.max(8, Math.round(((point.value || 0) / max) * 100));
        return '<div style="height:' + h + '%"></div>';
      }).join("") + '</div><div class="bars-labels">' +
      points.map(function (point) { return "<span>" + esc(point.label) + "</span>"; }).join("") + "</div>";
  }

  async function renderWeek() {
    const data = await api("/api/v1/week-plan/current/");
    const plan = data.weekPlan;
    if (!plan) {
      screen.innerHTML =
        '<p class="notice">' + esc(data.detail || t("week.none")) + "</p>" +
        '<button class="full-button" id="makePlan" type="button">' + t("week.build") + "</button>";
      document.getElementById("makePlan").addEventListener("click", async function () {
        try {
          await api("/api/v1/week-plan/refresh/", { method: "POST", body: {} });
          render();
        } catch (error) {
          screen.innerHTML = '<p class="notice">' + esc(error.message) + "</p>";
        }
      });
      return;
    }
    screen.innerHTML = (plan.days || []).map(function (day) {
      if (day.isRest) return row(t("week.day", { n: day.dayIndex + 1 }), t("week.rest"), "");
      const first = (day.exercises || [])[0];
      const workoutId = day.counterProfileId || (first && first.counterProfileId);
      return row(esc(day.title || t("week.day", { n: day.dayIndex + 1 })), esc(day.focusNote || ""), 'data-go="workout" data-id="' + esc(workoutId || "") + '"');
    }).join("");
    bindNav();
  }

  async function renderCompete() {
    const [board, seasons, challenges] = await Promise.all([
      api("/api/v1/leaderboard/?limit=3"),
      api("/api/v1/seasons/current/").catch(function () { return { seasons: [] }; }),
      api("/api/v1/challenges/").catch(function () { return { challenges: [] }; }),
    ]);
    const season = (seasons.seasons || [])[0];
    const active = (challenges.challenges || []).find(function (item) {
      return item.status === "active" || item.status === "pending";
    });
    screen.innerHTML =
      '<p class="eyebrow">' + t("compete.kicker") + '</p><h1 class="page-title">' + t("nav.competitions") + "</h1>" +
      (season
        ? '<button class="feature-banner" type="button" data-go="seasons">' + decoLayer("banner") +
          '<div><span class="eyebrow text-foreground">' + t("compete.seasonLeft", { n: season.daysLeft }) +
          "</span><h2>" + esc(season.name) + "</h2><p>" + t("compete.record") + "</p></div>" +
          icon("trophy", 49) + "</button>"
        : "") +
      '<div class="stats-grid"><button class="stat" type="button" data-go="board"><div class="stat-icon text-primary">' +
      icon("trophy", 22) + '</div><div><p class="stat-name">' + t("compete.place") + '</p><strong class="stat-value">#' +
      esc(board.myRank || "—") + "</strong></div></button>" +
      '<button class="stat" type="button" data-go="challenges"><div class="stat-icon text-violet">' +
      icon("swords", 22) + '</div><div><p class="stat-name">' + t("compete.wins") + '</p><strong class="stat-value">' +
      esc((challenges.challenges || []).length) + "</strong></div></button>" +
      '<button class="stat" type="button" data-go="profile"><div class="stat-icon text-lime">' +
      icon("zap", 22) + '</div><div><p class="stat-name">' + t("compete.seasonXp") + '</p><strong class="stat-value">' +
      esc(board.myXp || board.myTotalXp || "—") + "</strong></div></button></div>" +
      heading(t("compete.challengeSelf")) +
      row(t("compete.challenges"), active ? t("compete.incomingOne") : t("compete.challengeFriend"), 'data-go="challenges"', "", icon("swords")) +
      row(t("scope.friends"), t("compete.friendsTogether"), 'data-go="friends"', "", icon("users")) +
      row(t("compete.badges"), t("compete.badgesSub"), 'data-go="badges"', "", icon("medal")) +
      heading(t("compete.leaders"), 'data-go="board"', t("compete.allBoard")) +
      '<div class="leader-list">' + (board.entries || []).map(leader).join("") + "</div>";
    bindNav();
    bindClicks("[data-player]", function (node) { push("player", t("screen.player"), { id: node.dataset.player }); });
  }

  async function renderBoard() {
    const data = await api("/api/v1/leaderboard/?limit=30&scope=" + encodeURIComponent(state.boardScope));
    const compact = [["global", t("scope.global")], ["city", t("scope.city")], ["university", t("scope.university")], ["friends", t("scope.friends")]];
    const me = (data.entries || []).find(function (entry) { return entry.isMe; });
    screen.innerHTML =
      segments("scope", compact, state.boardScope) +
      (data.needsProfile
        ? '<p class="notice">' + t("board.needCity") + "</p>"
        : podium(data.entries) + '<div class="leader-list">' + (data.entries || []).map(leader).join("") + "</div>") +
      (me
        ? '<div class="my-place"><span class="rank">#' + esc(me.rank) + '</span><span class="podium-avatar">' + t("chrome.you") + '</span><div><strong>' + t("compete.place") + "</strong><small>" +
          t("level.n", { n: me.level }) + '</small></div><span class="leader-xp">' + esc(me.totalXp || 0) + " XP</span></div>"
        : "");
    bindClicks("[data-scope]", function (node) { state.boardScope = node.dataset.scope; render(); });
    bindClicks("[data-player]", function (node) { push("player", t("screen.player"), { id: node.dataset.player }); });
  }

  async function renderFriends() {
    const data = await api("/api/v1/friends/");
    const friends = data.friends || [];
    const incoming = data.incoming || [];
    screen.innerHTML =
      '<button class="full-button" id="tgShare" type="button">' + t("friends.inviteTg") + "</button>" +
      heading(t("friends.yours", { n: friends.length })) +
      (friends.length ? '<div class="friend-list">' + friends.map(friendCard).join("") + "</div>" : '<p class="notice">' + t("friends.empty") + "</p>") +
      '<input class="input-field" id="friendQuery" placeholder="' + t("friends.placeholder") + '">' +
      '<div class="actions"><button class="sport-button" id="searchFriend" type="button">' + t("friends.find") + "</button>" +
      '<button class="sport-button ghost" id="redeemCode" type="button">' + t("friends.code") + "</button></div>" +
      '<p class="notice">' + t("friends.yourCode", { code: esc(data.inviteCode || "—") }) + '</p><div id="searchHits"></div>' +
      (incoming.length ? heading(t("friends.requests")) + incoming.map(function (item) {
        return '<div class="row"><span class="avatar">' + initials(item.displayName) + "</span><div><h3>" +
          esc(item.displayName) + '</h3></div><span class="row-action"><button class="sport-button" data-accept="' +
          esc(item.friendshipId) + '" type="button">' + t("friends.accept") + "</button></span></div>";
      }).join("") : "");
    document.getElementById("tgShare").addEventListener("click", function () {
      shareTelegram(t("friends.share", { code: data.inviteCode || "" }));
    });
    document.getElementById("searchFriend").addEventListener("click", searchFriends);
    document.getElementById("redeemCode").addEventListener("click", redeemInvite);
    bindNav();
    bindClicks("[data-accept]", async function (node) {
      await api("/api/v1/friends/" + node.dataset.accept + "/accept/", { method: "POST", body: {} });
      render();
    });
    bindClicks("[data-player]", function (node) { push("player", t("screen.player"), { id: node.dataset.player }); });
  }

  async function searchFriends() {
    const query = document.getElementById("friendQuery").value.trim();
    const box = document.getElementById("searchHits");
    if (query.length < 2) {
      box.innerHTML = '<p class="notice">' + t("friends.min2") + "</p>";
      return;
    }
    try {
      const data = await api("/api/v1/players/search/?q=" + encodeURIComponent(query));
      box.innerHTML = (data.players || []).map(function (item) {
        return row(esc(item.displayName), t("friends.lvl", { n: item.level }), 'data-add="' + esc(item.playerId) + '"', t("friends.add"));
      }).join("") || '<p class="notice">' + t("friends.none") + "</p>";
      bindClicks("[data-add]", async function (node) {
        await api("/api/v1/friends/request/", { method: "POST", body: { playerId: Number(node.dataset.add) } });
        render();
      });
    } catch (error) {
      box.innerHTML = '<p class="notice">' + esc(error.message) + "</p>";
    }
  }

  async function redeemInvite() {
    const code = document.getElementById("friendQuery").value.trim();
    await api("/api/v1/invites/redeem/", { method: "POST", body: { inviteCode: code } });
    render();
  }

  async function renderPlayer(id) {
    const player = await api("/api/v1/players/" + encodeURIComponent(id) + "/");
    screen.innerHTML =
      '<div class="profile-head"><span class="avatar lg">' + initials(player.displayName) + "</span><div><h2>" +
      esc(player.displayName) + "</h2><p>" + t("level.n", { n: player.level }) +
      (player.city ? " · " + esc(player.city) : "") + "</p></div></div>" +
      '<div class="detail-metrics"><div><strong>#' + esc(player.rank || "—") + "</strong><small>" + t("player.inBoard") + "</small></div>" +
      "<div><strong>" + esc(player.totalXp) + "</strong><small>" + t("player.xp") + "</small></div></div>" +
      (player.isFriend && !player.isMe
        ? '<button class="full-button" type="button" data-go="create" data-id="' + esc(player.playerId) + '">' + t("player.challenge") + "</button>"
        : "");
    bindNav();
  }

  async function renderChallenges() {
    const data = await api("/api/v1/challenges/");
    const friends = await api("/api/v1/friends/");
    const names = {};
    (friends.friends || []).forEach(function (item) { names[item.playerId] = item.displayName; });
    const filter = state.challengeFilter;
    const list = (data.challenges || []).filter(function (item) {
      if (filter === "incoming") return item.status === "pending";
      if (filter === "active") return item.status === "active";
      return item.status !== "pending" && item.status !== "active";
    });
    screen.innerHTML =
      segments("ch-filter", [["incoming", t("ch.incoming")], ["active", t("ch.active")], ["out", t("ch.out")]], filter) +
      (list.map(function (item) {
        const other = names[item.opponentId] || names[item.challengerId] || ("#" + item.id);
        return duelCard(item, other, initials(other));
      }).join("") || '<p class="notice">' + t("ch.quiet") + "</p>") +
      '<button class="full-button" type="button" data-go="friends">' + t("player.challenge") + "</button>" +
      '<button class="full-button sport-button ghost" id="tgDuel" type="button">' + t("ch.callTg") + "</button>";
    bindNav();
    bindClicks("[data-ch-filter]", function (node) { state.challengeFilter = node.dataset.chFilter; render(); });
    document.getElementById("tgDuel").addEventListener("click", function () {
      shareTelegram(t("ch.share"));
    });
  }

  async function renderCreateChallenge(opponentId) {
    screen.innerHTML =
      '<label class="eyebrow">' + t("ch.exercise") + '</label><div class="filter-row">' +
      exercises.map(function (type) { return chip("ex", type, type, "PUSHUP"); }).join("") + "</div>" +
      '<label class="eyebrow">' + t("ch.goal") + '</label><input class="input-field" id="goalValue" type="number" value="30">' +
      '<label class="eyebrow">' + t("ch.wager") + '</label><input class="input-field" id="wagerXp" type="number" value="10">' +
      '<button class="full-button" id="sendChallenge" type="button">' + t("ch.create") + "</button>";
    let selected = "PUSHUP";
    bindClicks("[data-ex]", function (node) {
      selected = node.dataset.ex;
      screen.querySelectorAll("[data-ex]").forEach(function (button) {
        button.classList.toggle("is-on", button.dataset.ex === selected);
      });
    });
    document.getElementById("sendChallenge").addEventListener("click", async function () {
      await api("/api/v1/challenges/create/", {
        method: "POST",
        body: {
          opponentId: Number(opponentId),
          exerciseType: selected,
          goalValue: Number(document.getElementById("goalValue").value || 0),
          wagerXp: Number(document.getElementById("wagerXp").value || 10),
        },
      });
      state.stack.pop();
      push("challenges", t("screen.challenges"));
    });
  }

  async function renderChallenge(id) {
    const data = await api("/api/v1/challenges/");
    const item = (data.challenges || []).find(function (row) { return String(row.id) === String(id); });
    if (!item) {
      screen.innerHTML = '<p class="notice">' + t("ch.missing") + "</p>";
      return;
    }
    const actions = [];
    if (item.status === "pending") {
      actions.push('<button class="sport-button" data-act="accept" type="button">' + t("friends.accept") + "</button>");
      actions.push('<button class="sport-button ghost" data-act="decline" type="button">' + t("ch.decline") + "</button>");
    }
    if (item.status === "active") {
      actions.push('<button class="full-button" data-act="train" type="button">' + t("ch.join") + "</button>");
    }
    screen.innerHTML =
      '<div class="empty-state"><h2>' + t("ch.vs") + "</h2><p>" + esc(item.exerciseType) +
      ". " + t("ch.goalLine", { goal: item.goalValue, xp: item.wagerXp }) + "</p></div>" +
      duelCard(item, t("ch.rival"), "VS") +
      '<div class="actions">' + actions.join("") + "</div>";
    bindClicks("[data-act]", async function (node) {
      const act = node.dataset.act;
      if (act === "train") {
        const catalog = await api("/api/v1/workouts/");
        const match = (catalog.workouts || []).find(function (workout) {
          return (workout.parentType || "").toUpperCase() === item.exerciseType;
        }) || (catalog.workouts || [])[0];
        if (!match) return;
        const started = await api("/api/v1/workouts/" + encodeURIComponent(match.id) + "/start/", { method: "POST", body: {} });
        state.session = {
          kind: "workout",
          id: started.sessionId,
          title: match.title,
          startedAt: Date.now(),
          calories: match.calories,
          minutes: match.durationMin,
          challengeId: item.id,
        };
        render();
        return;
      }
      await api("/api/v1/challenges/" + item.id + "/" + act + "/", { method: "POST", body: {} });
      render();
    });
  }

  async function renderSeasons() {
    const data = await api("/api/v1/seasons/current/");
    const seasons = data.seasons || [];
    if (!seasons.length) {
      screen.innerHTML = '<p class="notice">' + t("season.empty") + "</p>";
      return;
    }
    const blocks = [];
    for (let i = 0; i < seasons.length; i += 1) {
      const season = seasons[i];
      let ranks = { entries: [] };
      try { ranks = await api("/api/v1/seasons/" + season.id + "/rankings/"); } catch (error) { ranks = { entries: [] }; }
      blocks.push(
        '<div class="feature-banner">' + decoLayer("banner") + "<div><h2>" + esc(season.name) + "</h2><p>" +
        t("season.left", { n: season.daysLeft, rank: season.myRank || "—" }) + "</p></div></div>" +
        '<div class="leader-list">' + (ranks.entries || []).slice(0, 20).map(function (entry) {
          const name = (entry.snapshot && (entry.snapshot.displayName || entry.snapshot.username)) || ("#" + entry.rank);
          return '<div class="leader"><span class="rank">' + esc(entry.rank) + '</span><div><div class="leader-name">' +
            esc(name) + '</div></div><span class="leader-xp">' + esc(entry.totalXp) + " XP</span></div>";
        }).join("") + "</div>"
      );
    }
    screen.innerHTML = blocks.join("");
  }

  async function renderQuests() {
    const data = await api("/api/v1/quests/?type=" + state.questType);
    screen.innerHTML =
      '<div class="filter-row">' + chip("quest-type", "daily", t("quest.daily"), state.questType) +
      chip("quest-type", "weekly", t("quest.weekly"), state.questType) + "</div>" +
      ((data.quests || []).map(function (quest) {
        const extra = quest.status === "completed_unclaimed"
          ? '<button class="sport-button" type="button" data-claim="' + esc(quest.id) + '">' + t("quest.claim") + "</button>"
          : (quest.status === "claimed" ? '<span class="chip">' + t("quest.claimed") + "</span>" : '<span class="chip">' + t("quest.progress") + "</span>");
        return row(esc(quest.title), esc(quest.progressCurrent) + " / " + esc(quest.progressTarget) + " · +" + esc(quest.rewardXp) + " XP", "", extra);
      }).join("") || '<p class="notice">' + t("quest.empty") + "</p>");
    bindClicks("[data-quest-type]", function (node) { state.questType = node.dataset.questType; render(); });
    bindClicks("[data-claim]", async function (node) {
      node.disabled = true;
      await api("/api/v1/quests/" + node.dataset.claim + "/claim/", { method: "POST", body: {} });
      render();
    });
  }

  async function renderSearch() {
    const data = await api("/api/v1/workouts/");
    screen.innerHTML =
      '<input class="input-field" id="q" placeholder="' + t("search.placeholder") + '">' +
      '<div id="hits"></div>';
    const hits = document.getElementById("hits");
    function draw() {
      const q = document.getElementById("q").value.toLowerCase();
      const list = (data.workouts || []).filter(function (item) {
        return !q || (item.title || "").toLowerCase().indexOf(q) >= 0;
      });
      hits.innerHTML = list.map(function (item) {
        return row(esc(item.title), esc(item.durationMin) + " " + t("unit.min"), 'data-go="workout" data-id="' + esc(item.id) + '"');
      }).join("") || '<p class="notice">' + t("search.empty") + "</p>";
      bindNav(hits);
    }
    document.getElementById("q").addEventListener("input", draw);
    draw();
  }

  function avatarMarkup(me) {
    const src = personPhoto(me);
    if (src) {
      return '<img class="avatar object-cover" src="' + esc(src) + '" alt="" referrerpolicy="no-referrer">';
    }
    return '<span class="avatar">' + initials(personName(me)) + "</span>";
  }

  function linkRow(title, go) {
    return '<button class="row" type="button" data-go="' + go + '"><strong>' + title + "</strong>" +
      icon("arrow-right", 17).replace("<svg ", '<svg class="ml-auto" ') + "</button>";
  }

  function field(id, label, value, extra) {
    return '<label class="field-label">' + label + '<input class="input-field" id="' + id +
      '" value="' + esc(value == null ? "" : value) + '" ' + (extra || "") + "></label>";
  }

  function pfAvatar(me) {
    const src = personPhoto(me);
    if (src) {
      return '<img class="pf-avatar" src="' + esc(src) + '" alt="' + t("pf.avatar") + '" referrerpolicy="no-referrer">';
    }
    return '<span class="pf-avatar">' + initials(personName(me)) + "</span>";
  }

  function pfTitle(kicker, title, extra) {
    return '<div class="section-heading pf-title"><h2><span class="pf-kicker">' + kicker + "</span>" +
      title + "</h2>" + (extra || "") + "</div>";
  }

  function pfMenu(go, glyph, title, sub) {
    return '<button class="pf-menu-item" type="button" data-go="' + go + '"><span class="pf-menu-icon">' +
      glyph + '</span><span class="min-w-0 flex-1"><strong>' + title + "</strong><small>" + sub +
      "</small></span>" + icon("chevron", 18).replace("<svg ", '<svg class="text-muted-foreground" ') +
      "</button>";
  }

  function skillRadar(values, labels) {
    const c = 120, r = 78, n = values.length;
    function angle(i) { return (Math.PI * 2 * i) / n - Math.PI / 2; }
    function point(i, f) {
      return (c + Math.cos(angle(i)) * r * f) + "," + (c + Math.sin(angle(i)) * r * f);
    }
    function ring(f) {
      return values.map(function (_, i) { return point(i, f); }).join(" ");
    }
    const shape = values.map(function (v, i) {
      return point(i, Math.max(0.1, Math.min(1, v)));
    }).join(" ");
    const grids = [0.25, 0.5, 0.75, 1].map(function (f) {
      return '<polygon points="' + ring(f) + '" class="pf-radar-grid"/>';
    }).join("");
    const axes = values.map(function (_, i) {
      const p = point(i, 1).split(",");
      return '<line x1="' + c + '" y1="' + c + '" x2="' + p[0] + '" y2="' + p[1] + '" class="pf-radar-grid"/>';
    }).join("");
    const dots = values.map(function (v, i) {
      const p = point(i, Math.max(0.1, Math.min(1, v))).split(",");
      return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4" class="pf-radar-dot"/>';
    }).join("");
    const texts = labels.map(function (label, i) {
      const cos = Math.cos(angle(i)), sin = Math.sin(angle(i));
      const x = c + cos * (r + 12), y = c + sin * (r + 18) + 4;
      const anchor = cos > 0.3 ? "start" : cos < -0.3 ? "end" : "middle";
      return '<text x="' + x + '" y="' + y + '" text-anchor="' + anchor + '" class="pf-radar-label">' +
        esc(label) + "</text>";
    }).join("");
    return '<svg class="pf-radar" viewBox="-62 0 364 240" role="img" aria-label="' + t("pf.radar") + '">' +
      '<defs><linearGradient id="pf-radar-fill" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" stop-color="var(--violet)"/><stop offset="1" stop-color="var(--primary)"/>' +
      "</linearGradient></defs>" + grids + axes +
      '<polygon points="' + shape + '" class="pf-radar-shape"/>' + dots + texts + "</svg>";
  }

  async function renderProfile() {
    const me = await api("/api/v1/users/me/");
    const skills = me.skills || {};
    const skillSet = [
      ["strength", t("skill.strength"), skills.strength],
      ["stamina", t("skill.stamina"), skills.stamina],
      ["agility", t("skill.agility"), skills.agility],
      ["technique", t("skill.technique"), skills.technique],
    ];
    const values = skillSet.map(function (item) { return Number(item[2] || 1); });
    const max = Math.max(10, Math.max.apply(null, values));
    const name = personName(me);
    const inst = me.institutionName || me.institutionCustom || "";
    const badges = [
      { name: t("badge.first"), sub: t("badge.firstSub"), glyph: "footprints", open: (me.totalWorkouts || 0) > 0 },
      { name: t("badge.fire"), sub: t("badge.fireSub"), glyph: "flame", open: (me.workoutStreak || 0) >= 7 },
      { name: t("badge.win"), sub: t("badge.winSub"), glyph: "trophy", open: (me.challengesWon || 0) > 0 },
      { name: t("badge.up"), sub: t("badge.upSub"), glyph: "medal", open: (me.level || 1) >= 10 },
    ];
    const opened = badges.filter(function (b) { return b.open; }).length;
    const points = me.skillPoints || 0;
    screen.innerHTML =
      '<div class="pf"><section class="pf-cover">' + decoLayer("cover") +
        '<div class="pf-cover-top"><p class="eyebrow">' + t("pf.kicker") + "</p>" +
        '<button type="button" class="icon-control grid place-items-center" data-go="settings" aria-label="' + t("screen.settings") + '">' +
        icon("settings", 18) + "</button></div>" +
        '<div class="pf-id"><div class="pf-avatar-wrap">' + pfAvatar(me) +
        '<span class="pf-level" aria-label="' + t("level.aria", { n: me.level }) + '">' + esc(me.level) +
        "<small>LVL</small></span></div><div class=\"min-w-0\">" +
        '<span class="sticker"><span>' + t("pf.dont") + "</span></span>" +
        '<h2 class="pf-name">' + esc(name) + '</h2><div class="pf-chips">' +
        (me.telegramUsername ? '<span class="chip">@' + esc(me.telegramUsername) + "</span>" : "") +
        (me.city
          ? '<span class="chip">' + icon("pin", 12) + esc(me.city) + "</span>"
          : '<button class="chip chip-add" type="button" data-go="location">' + icon("pin", 12) + t("pf.addCity") + "</button>") +
        (inst ? '<span class="chip">' + icon("cap", 12) + esc(inst) +
          (me.course ? " · " + t("pf.course", { n: me.course }) : "") + "</span>" : "") +
        '</div></div></div><div class="pf-actions">' +
        '<button class="sport-button" type="button" data-go="edit">' + icon("pen", 16) + t("pf.edit") + "</button>" +
        '<button class="sport-button ghost" type="button" data-share="1">' + icon("send", 16) +
        t("pf.invite") + "</button></div></section>" +
      '<div class="pf-stats">' +
        pfStat(t("stat.level"), fmt(me.level), "", "star") +
        pfStat(t("stat.xp"), fmt(Math.round(me.totalXp || me.exp || 0)), "XP", "zap") +
        pfStat(t("stat.streak"), fmt(me.workoutStreak || 0), t("unit.days"), "flame") +
        pfStat(t("stat.workouts"), fmt(me.totalWorkouts || 0), "", "timer") +
      "</div>" +
      '<div class="pf-stats">' +
        pfStat(t("stat.cals"), fmt(Math.round(me.totalCalories || 0)), t("unit.kcal"), "flame") +
        pfStat(t("stat.reps"), fmt(me.totalReps || 0), "", "zap") +
        pfStat(t("stat.mins"), fmt(me.totalMinutes || 0), "", "timer") +
        pfStat(t("stat.wins"), fmt(me.challengesWon || 0), "", "trophy") +
      "</div>" +
      pfTitle("01", t("pf.skills")) +
      '<section class="pf-skills">' + skillRadar(values.map(function (v) { return v / max; }),
        skillSet.map(function (item) { return item[1]; })) +
      '<div class="pf-skill-list">' + skillSet.map(function (item) {
        return skillLine(item[0], item[1], item[2], max);
      }).join("") +
      '<p class="pf-hint">' + icon("target", 14) +
      (points ? t("pf.hintPoint") : t("pf.hintGrow")) +
      "</p></div></section>" +
      pfTitle("02", t("pf.achievements"),
        '<button class="text-link" type="button" data-go="badges">' + t("pf.of", { a: opened, b: badges.length }) + " " +
        icon("chevron", 14) + "</button>") +
      '<div class="pf-badges">' + badges.map(function (badge) {
        return '<button class="pf-badge' + (badge.open ? " open" : "") + '" type="button" data-go="badges">' +
          '<span class="pf-medal">' + icon(badge.open ? badge.glyph : "lock", badge.open ? 24 : 18) +
          "</span><strong>" + badge.name + "</strong><small>" + badge.sub + "</small></button>";
      }).join("") + "</div>" +
      pfTitle("03", t("pf.account")) +
      '<nav class="pf-menu" aria-label="' + t("pf.menu") + '">' +
        pfMenu("edit", icon("pen", 18), t("screen.edit"), me.fromTelegram ? t("pf.editSubTg") : t("pf.editSub")) +
        pfMenu("location", icon("pin", 18), t("pf.loc"), t("pf.locSub")) +
        pfMenu("week", icon("brain", 18), t("pf.ai"), t("pf.aiSub")) +
        pfMenu("friends", icon("users", 18), t("scope.friends"), t("pf.friendsSub")) +
        pfMenu("settings", icon("settings", 18), t("screen.settings"), t("pf.setSub")) +
      "</nav></div>";
    bindNav();
    bindClicks("[data-share]", function () {
      shareTelegram(t("share.me", { name: name, level: me.level }));
    });
    bindClicks("[data-skill]", async function (node) {
      try {
        await api("/api/v1/users/me/skills/upgrade/", { method: "POST", body: { skill: node.dataset.skill } });
        render();
      } catch (error) {
        screen.insertAdjacentHTML("afterbegin", '<p class="notice">' + esc(error.message) + "</p>");
      }
    });
  }

  function pfStat(label, value, unit, glyph) {
    return '<div class="pf-stat"><span class="pf-stat-icon">' + icon(glyph, 16) +
      '</span><p class="pf-stat-value">' + value + (unit ? "<small>" + unit + "</small>" : "") +
      '</p><p class="pf-stat-label">' + label + "</p></div>";
  }

  function skillLine(key, label, value, max) {
    const n = Number(value || 1);
    const pct = Math.max(4, Math.round((n / Math.max(1, max)) * 100));
    return '<button class="pf-skill" type="button" data-skill="' + key +
      '"><div class="pf-skill-top"><strong>' + label + "</strong><b>" + esc(n) +
      "</b></div><div class=\"pf-meter\"><span style=\"width:" + pct + '%"></span></div></button>';
  }

  async function renderEditProfile(locationOnly) {
    const me = await api("/api/v1/users/me/");
    const fields = locationOnly
      ? field("city", t("field.city"), me.city, "required") +
        field("region", t("field.region"), me.region) +
        field("institutionCustom", t("field.school"), me.institutionCustom || me.institutionName) +
        field("faculty", t("field.faculty"), me.faculty) +
        field("course", t("field.course"), me.course, 'inputmode="numeric"')
      : (me.fromTelegram
        ? '<p class="notice">' + t("edit.tg") +
          (me.telegramUsername ? " (@" + esc(me.telegramUsername) + ")" : "") + ".</p>" +
          field("city", t("field.city"), me.city)
        : field("displayName", t("field.name"), me.displayName, "required maxlength=\"120\"") +
          field("avatarUrl", t("field.avatar"), me.avatarUrl, 'type="url" maxlength="500"') +
          field("city", t("field.city"), me.city));
    screen.innerHTML = '<form id="profileForm">' + fields +
      '<p class="notice" id="formError" hidden></p>' +
      '<button class="full-button" type="submit">' + t("edit.save") + " " + icon("check", 18) + "</button></form>";
    document.getElementById("profileForm").addEventListener("submit", async function (event) {
      event.preventDefault();
      const err = document.getElementById("formError");
      err.hidden = true;
      const val = function (id) {
        const node = document.getElementById(id);
        return node ? node.value.trim() : "";
      };
      const body = locationOnly
        ? {
            city: val("city"),
            region: val("region"),
            institutionCustom: val("institutionCustom"),
            faculty: val("faculty"),
            course: val("course"),
          }
        : me.fromTelegram
          ? { city: val("city") }
          : {
              displayName: val("displayName"),
              avatarUrl: val("avatarUrl"),
              city: val("city"),
            };
      if (!locationOnly && body.avatarUrl && !/^https:\/\//i.test(body.avatarUrl)) {
        err.hidden = false;
        err.textContent = t("edit.https");
        return;
      }
      try {
        await api("/api/v1/users/me/", { method: "PATCH", body: body });
        goBack();
      } catch (error) {
        err.hidden = false;
        err.textContent = error.message || t("edit.fail");
      }
    });
  }

  async function renderSettings() {
    const me = await api("/api/v1/users/me/");
    const currentLang = window.TeminaI18n ? window.TeminaI18n.lang() : "ru";
    screen.innerHTML =
      '<p class="eyebrow">' + t("set.lang") + "</p>" +
      '<div class="lang-switch">' +
        '<button type="button" data-lang="ru"' + (currentLang === "ru" ? ' class="on"' : "") + ">" + t("set.ru") + "</button>" +
        '<button type="button" data-lang="uz"' + (currentLang === "uz" ? ' class="on"' : "") + ">" + t("set.uz") + "</button>" +
      "</div>" +
      '<p class="notice">' + t("set.invite", { code: esc(me.inviteCode || "—") }) + "</p>" +
      '<button class="sport-button ghost full-button" type="button" id="copyInvite">' + t("set.copy") + "</button>" +
      (window.TeminaIntro ? '<button class="full-button outline" type="button" id="replayIntro">' + esc(window.TeminaIntro.replayLabel()) + '</button>' : '') +
      '<button class="full-button outline" type="button" id="logoutBtn">' + icon("logout", 18) +
      " " + t("set.logout") + "</button>" +
      '<p class="notice" id="settingsError" hidden></p>';
    bindClicks("[data-lang]", function (node) {
      if (window.TeminaI18n) window.TeminaI18n.setLang(node.dataset.lang);
      render();
    });
    const replayIntro = document.getElementById("replayIntro");
    if (replayIntro) replayIntro.addEventListener("click", function () { window.TeminaIntro.show(true); });
    document.getElementById("copyInvite").addEventListener("click", async function () {
      const err = document.getElementById("settingsError");
      try {
        await navigator.clipboard.writeText(me.inviteCode || "");
        err.hidden = false;
        err.textContent = t("set.copied");
      } catch (error) {
        err.hidden = false;
        err.textContent = t("set.copyFail");
      }
    });
    document.getElementById("logoutBtn").addEventListener("click", async function () {
      const err = document.getElementById("settingsError");
      try {
        await api("/api/auth/logout/", { method: "POST", body: {} });
        window.location.href = "/";
      } catch (error) {
        err.hidden = false;
        err.textContent = t("set.logoutFail");
      }
    });
  }

  async function renderBadges() {
    const me = await api("/api/v1/users/me/");
    const badges = me.badges || [];
    screen.innerHTML = badges.length
      ? badges.map(function (badge) {
          return row(esc(badge.name || badge.title || badge.code || t("badge.one")), esc(badge.description || ""), "");
        }).join("")
      : '<p class="notice">' + t("badge.none") + "</p>";
  }

  function goBack() {
    if (state.session) return;
    if (state.stack.length) state.stack.pop();
    render();
  }

  document.querySelectorAll(".nav-item").forEach(function (button) {
    button.addEventListener("click", function () {
      if (state.session) return;
      setTab(button.dataset.tab);
    });
  });
  bindNav(document.querySelector(".topbar"));
  back.addEventListener("click", goBack);
  if (tg && tg.BackButton) tg.BackButton.onClick(goBack);
  document.getElementById("gateRetry").addEventListener("click", boot);

  async function boot() {
    if (window.TeminaI18n) window.TeminaI18n.applyChrome();
    showGate(t("gate.enter"), t("gate.checking"), "loading");
    try {
      if (window.TeminaIntro) {
        if (tg && tg.initData) { tg.ready(); tg.expand(); }
        await window.TeminaIntro.show();
      }
      if (tg && tg.initData) {
        await api("/api/auth/telegram/", { method: "POST", body: { initData: tg.initData } });
      }
      const me = await api("/api/auth/me/");
      if (!me.authenticated) {
        showGate(t("gate.openTg"), t("gate.needTg"), "login");
        return;
      }
      openApp();
    } catch (error) {
      const text = error.status === 503 ? t("gate.noToken") : t("gate.badSig");
      showGate(t("gate.fail"), text, "retry");
    }
  }

  boot();
})();
