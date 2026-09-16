// Consent-gated Yandex.Metrika (spec §8, A7). The Metrika script is only created after the
// visitor pressed "Agree"; the decision is remembered in localStorage("ea-consent").
// mc.yandex.ru is allowed in the CSP script-src, so no inline script is needed.
const KEY = "ea-consent";

function decision() {
  try {
    return localStorage.getItem(KEY) || "";
  } catch (e) {
    return "";
  }
}

function remember(value) {
  try {
    localStorage.setItem(KEY, value);
  } catch (e) {
    /* ignore */
  }
}

export function loadMetrika(id) {
  if (!id || window.ym || document.getElementById("ea-metrika")) return;
  window.ym =
    window.ym ||
    function () {
      (window.ym.a = window.ym.a || []).push(arguments);
    };
  window.ym.l = Date.now();
  const script = document.createElement("script");
  script.id = "ea-metrika";
  script.async = true;
  script.src = "https://mc.yandex.ru/metrika/tag.js";
  document.head.appendChild(script);
  window.ym(Number(id), "init", {
    clickmap: false,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: false,
    ecommerce: false,
  });
}

export function initConsent() {
  const banner = document.querySelector('[data-component="consent"]');
  if (!banner) return;
  const id = banner.dataset.metrikaId;
  const current = decision();
  if (current === "yes") {
    loadMetrika(id);
    return;
  }
  if (current === "no") return;
  banner.hidden = false;
  banner.addEventListener("click", (event) => {
    const button = event.target.closest("[data-consent]");
    if (!button) return;
    remember(button.dataset.consent);
    banner.hidden = true;
    if (button.dataset.consent === "yes") loadMetrika(id);
  });
}
