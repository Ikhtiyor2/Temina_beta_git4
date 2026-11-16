(function () {
  var tg = window.Telegram && window.Telegram.WebApp;
  var preview = document.documentElement.classList.contains("is-tma-preview");
  if ((!tg || !tg.initData) && !preview) return;

  var root = document.documentElement;
  root.classList.add("is-tma");
  var lang = (document.body && document.body.getAttribute("data-lang")) || "ru";
  var authed = document.body && document.body.getAttribute("data-authenticated") === "1";
  var gate = document.getElementById("tmaGate");
  var gateText = document.getElementById("tmaGateText");
  var gateRetry = document.getElementById("tmaGateRetry");

  var copy = lang === "en"
    ? { signingIn: "Signing in…", failed: "Couldn't sign in through Telegram.", retry: "Try again" }
    : { signingIn: "Входим…", failed: "Не удалось войти через Telegram.", retry: "Повторить" };

  function applyTheme() {
    var params = tg.themeParams || {};
    if (params.bg_color) root.style.setProperty("--bg", params.bg_color);
    if (params.text_color) root.style.setProperty("--txt", params.text_color);
    if (params.hint_color) root.style.setProperty("--muted", params.hint_color);
    if (params.secondary_bg_color) root.style.setProperty("--bg-surface", params.secondary_bg_color);
    if (params.section_separator_color) root.style.setProperty("--border", params.section_separator_color);
    var bg = /^#[0-9a-fA-F]{6}$/.test(params.bg_color || "") ? params.bg_color : "#0D0D10";
    try {
      if (tg.setHeaderColor) tg.setHeaderColor(bg);
      if (tg.setBackgroundColor) tg.setBackgroundColor(bg);
    } catch (e) {}
  }

  function isTabRoot(path) {
    var roots = ["/dashboard/", "/workouts/", "/quests/", "/leaderboard/", "/profile/", "/"];
    for (var i = 0; i < roots.length; i++) {
      if (path === roots[i]) return true;
    }
    return false;
  }

  function setupChrome() {
    if (!tg || !tg.initData) return;
    try { tg.expand(); } catch (e) {}
    try { if (tg.disableVerticalSwipes) tg.disableVerticalSwipes(); } catch (e) {}
    applyTheme();
    if (location.pathname.indexOf("/train/") === 0) root.classList.add("is-tma-focus");

    if (tg.BackButton) {
      if (isTabRoot(location.pathname) || location.pathname.indexOf("/login") === 0 || location.pathname.indexOf("/registration") === 0) {
        tg.BackButton.hide();
      } else {
        tg.BackButton.show();
        tg.BackButton.onClick(function () {
          if (window.history.length > 1) window.history.back();
          else window.location.href = "/dashboard/";
        });
      }
    }

    var tabs = document.querySelectorAll(".bottomNav a");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener("click", function () {
        try { tg.HapticFeedback && tg.HapticFeedback.selectionChanged(); } catch (e) {}
      });
    }
  }

  function csrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function safeNext(value) {
    if (!value || value.charAt(0) !== "/" || value.indexOf("//") === 0) return "";
    return value;
  }

  function showGate(kind) {
    if (!gate) return;
    gate.hidden = false;
    if (gateText) gateText.textContent = kind === "error" ? copy.failed : copy.signingIn;
    if (gateRetry) gateRetry.hidden = kind !== "error";
  }

  function hideGate() {
    if (gate) gate.hidden = true;
  }

  function afterLogin(data) {
    var next = safeNext(new URLSearchParams(window.location.search).get("next"));
    if (data && data.isNew) {
      window.location.replace("/welcome/");
      return;
    }
    if (next) {
      window.location.replace(next);
      return;
    }
    var path = window.location.pathname;
    if (path === "/" || path === "/home/" || path === "/index/" || path.indexOf("/login") === 0 || path.indexOf("/registration") === 0 || path.indexOf("/signin") === 0) {
      window.location.replace("/dashboard/");
      return;
    }
    window.location.reload();
  }

  function authenticate() {
    showGate("loading");
    return fetch("/api/auth/telegram/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify({ initData: tg.initData })
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok || !data.ok) throw new Error((data && data.error) || "auth_failed");
        afterLogin(data);
      });
    }).catch(function () {
      showGate("error");
    });
  }

  setupChrome();
  if (preview) {
    hideGate();
    return;
  }
  if (gateRetry) gateRetry.addEventListener("click", authenticate);
  if (!authed) authenticate();
  else hideGate();
})();
