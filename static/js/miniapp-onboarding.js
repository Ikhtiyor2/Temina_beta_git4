(function () {
  "use strict";
  const key = "temina_onboarding_v2";
  let active = null;
  const copy = {
    ru: {
      skip: "Пропустить", next: "Дальше", back: "Назад", start: "Погнали", replay: "Посмотреть обучение снова",
      hint: "Коснись справа — дальше · слева — назад", label: "Знакомство с Temina",
      slides: [
        ["ТВОЙ РИТМ", "ТВОЙ СПОРТ.\nТВОИ ПРАВИЛА.", "Находи время для себя. Тренируйся, замечай прогресс и становись сильнее с каждым днём."],
        ["УМНАЯ КАМЕРА", "ТЫ ДВИГАЕШЬСЯ.\nКАМЕРА СЧИТАЕТ.", "Поставь телефон так, чтобы тебя было видно целиком. Начни подход — AI поможет считать повторения."],
        ["ВЫЗОВ ПРИНЯТ", "ВМЕСТЕ —\nЕЩЁ СИЛЬНЕЕ.", "Добавляй друзей, бросай вызовы и поднимайся в рейтинге. Поддержка и немного соперничества — в одном месте."],
        ["НОВЫЙ УРОВЕНЬ", "КАЖДЫЙ ПОДХОД\nИМЕЕТ ЗНАЧЕНИЕ.", "Зарабатывай XP, открывай достижения и собирай свою историю побед. Начни с первой тренировки."],
      ],
    },
    uz: {
      skip: "O‘tkazib yuborish", next: "Keyingi", back: "Orqaga", start: "Boshladik", replay: "Qo‘llanmani qayta ko‘rish",
      hint: "O‘ngga bosing — keyingi · chapga — orqaga", label: "Temina bilan tanishing",
      slides: [
        ["SENING RITMING", "SENING SPORTING.\nSENING QOIDALARING.", "O‘zing uchun vaqt ajrat. Mashq qil, natijalarni kuzat va har kuni kuchliroq bo‘l."],
        ["AQLLI KAMERA", "SEN HARAKAT QIL.\nKAMERA SANAYDI.", "Telefonni butun tanang ko‘rinadigan qilib joylashtir. Mashqni boshla — AI takrorlarni sanashga yordam beradi."],
        ["CHORLOV QABUL QILINDI", "BIRGA —\nYANADA KUCHLI.", "Do‘stlarni qo‘sh, bellashuvga chorla va reytingda ko‘taril. Qo‘llab-quvvatlash va raqobat bir joyda."],
        ["YANGI DARAJA", "HAR BIR MASHQ\nAHAMIYATLI.", "XP to‘pla, yutuqlarni och va g‘alabalaring tarixini yarat. Birinchi mashqdan boshla."],
      ],
    },
  };
  function words() { return copy[window.TeminaI18n && window.TeminaI18n.lang()] || copy.ru; }
  function seen() { try { return localStorage.getItem(key) === "done"; } catch (_) { return false; } }
  function show(force) {
    if (active) return active;
    if (!force && seen()) return Promise.resolve();
    const root = document.getElementById("teminaIntro");
    if (!root) return Promise.resolve();
    const text = words();
    const previousFocus = document.activeElement;
    const surfaces = [document.getElementById("shell"), document.getElementById("gate")];
    const inertStates = surfaces.map(node => node && node.inert);
    surfaces.forEach(node => { if (node) node.inert = true; });
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    root.setAttribute("aria-label", text.label);
    root.hidden = false;
    root.classList.remove("intro-leaving");
    let index = 0;
    let closing = false;
    let resolveDone;
    active = new Promise(resolve => { resolveDone = resolve; });
    const progress = root.querySelector(".intro-progress");
    const photos = root.querySelectorAll(".intro-photo");
    const skip = root.querySelector(".intro-skip");
    const next = root.querySelector(".intro-next");
    const prev = root.querySelector(".intro-back");
    skip.textContent = text.skip;
    prev.setAttribute("aria-label", text.back);
    root.querySelector(".intro-hint").textContent = text.hint;
    progress.replaceChildren();
    text.slides.forEach((_, i) => {
      const segment = document.createElement("span");
      segment.className = "intro-segment";
      progress.appendChild(segment);
      photos[i].src = root.dataset.images + "slide-" + (i + 1) + ".webp";
    });
    function paint() {
      const slide = text.slides[index];
      photos.forEach((photo, i) => photo.classList.toggle("is-current", i === index));
      Array.from(progress.children).forEach((segment, i) => segment.classList.toggle("is-done", i <= index));
      root.querySelector(".intro-kicker").textContent = slide[0];
      root.querySelector(".intro-title").textContent = slide[1];
      root.querySelector(".intro-description").textContent = slide[2];
      root.querySelector(".intro-count").textContent = "0" + (index + 1) + " / 04";
      next.querySelector("span").textContent = index === 3 ? text.start : text.next;
      prev.disabled = index === 0;
      const content = root.querySelector(".intro-copy");
      if (content.getAnimations) content.getAnimations().forEach(animation => animation.cancel());
      if (content.animate && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        content.animate([{ opacity: 0, transform: "translateY(12px)" }, { opacity: 1, transform: "translateY(0)" }], { duration: 240, easing: "ease-out" });
      }
    }
    function finish() {
      if (closing) return;
      closing = true;
      try { localStorage.setItem(key, "done"); } catch (_) {}
      root.classList.add("intro-leaving");
      root.removeEventListener("click", click);
      root.removeEventListener("keydown", keyboard);
      root.removeEventListener("pointerdown", pointerDown);
      root.removeEventListener("pointerup", pointerUp);
      // Uncover the app only when the overlay is gone, preventing a dashboard flash.
      setTimeout(() => {
        root.hidden = true;
        document.body.style.overflow = oldOverflow;
        surfaces.forEach((node, i) => { if (node) node.inert = inertStates[i]; });
        if (previousFocus && previousFocus.isConnected && previousFocus !== document.body) previousFocus.focus();
        active = null;
        resolveDone();
      }, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 220);
    }
    function advance() { if (closing) return; if (index === 3) finish(); else { index++; paint(); } }
    function retreat() { if (closing) return; if (index > 0) { index--; paint(); } }
    let swipeStart = null;
    let ignoreClick = false;
    function pointerDown(event) { swipeStart = { x: event.clientX, y: event.clientY }; }
    function pointerUp(event) {
      if (!swipeStart) return;
      const dx = event.clientX - swipeStart.x;
      const dy = event.clientY - swipeStart.y;
      swipeStart = null;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {
        ignoreClick = true;
        if (dx < 0) advance(); else retreat();
        setTimeout(() => { ignoreClick = false; }, 0);
      }
    }
    function click(event) {
      if (ignoreClick) return;
      if (event.target.closest(".intro-skip")) return finish();
      if (event.target.closest(".intro-back")) return retreat();
      if (event.target.closest(".intro-next")) return advance();
      const bounds = root.getBoundingClientRect();
      if (event.clientX - bounds.left < bounds.width / 3) retreat(); else advance();
    }
    function keyboard(event) {
      if (event.key === "Escape") { event.preventDefault(); finish(); }
      if (event.key === "ArrowRight") { event.preventDefault(); advance(); }
      if (event.key === "ArrowLeft") { event.preventDefault(); retreat(); }
      if (event.key === "Tab") {
        const buttons = [skip, prev, next].filter(button => !button.disabled);
        const current = buttons.indexOf(document.activeElement);
        const target = event.shiftKey ? (current <= 0 ? buttons.length - 1 : current - 1) : (current + 1) % buttons.length;
        event.preventDefault(); buttons[target].focus();
      }
    }
    root.addEventListener("click", click);
    root.addEventListener("keydown", keyboard);
    root.addEventListener("pointerdown", pointerDown);
    root.addEventListener("pointerup", pointerUp);
    paint();
    skip.focus({ preventScroll: true });
    return active;
  }
  window.TeminaIntro = { show, replayLabel: () => words().replay };
})();
