// Entry point bundled by esbuild (npm run build:js) → static/dist/main.js
// HTMX + Alpine are vendored through npm and bundled here so no third-party CDN is needed.
// Alpine is the **CSP build**: no `new Function`, so the strict nonce-based CSP (spec §8)
// holds. Consequence: templates may only reference component properties / methods by name
// (`x-data="copyButton"`, `@click="copy"`, `x-show="copied"`) — every expression lives here.
import htmx from "htmx.org";
import Alpine from "@alpinejs/csp";
import { initToolbar } from "./a11y.js";
import { initConsent } from "./analytics.js";
import { initNav } from "./nav.js";

// The indicator CSS lives in components.css; htmx must not inject an inline <style> (CSP).
htmx.config.includeIndicatorStyles = false;
// EA-03: forms answer 400 (validation) and 429 (rate limit) with a partial that must be shown;
// htmx 2 drops every 4xx/5xx body by default, so the submit button looked dead.
htmx.config.responseHandling = [
  { code: "204", swap: false },
  { code: "[23]..", swap: true },
  { code: "^(400|422|429)$", swap: true, error: false },
  { code: "[45]..", swap: false, error: true },
];
window.htmx = htmx;
window.Alpine = Alpine;

// CSRF for HTMX POSTs (Django reads X-CSRFToken)
document.addEventListener("htmx:configRequest", (event) => {
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  if (token) event.detail.headers["X-CSRFToken"] = token;
});

// Any other failure (500, network): a translated line inside the target, read out once.
function showRequestError(event) {
  const target = event.detail.target;
  if (!target) return;
  target.querySelector(".htmx-error")?.remove();
  const message = document.createElement("p");
  message.className = "form-errors htmx-error";
  message.setAttribute("role", "alert");
  message.textContent = document.body.dataset.requestError || "Error";
  target.prepend(message);
}
document.addEventListener("htmx:responseError", showRequestError);
document.addEventListener("htmx:sendError", showRequestError);

// After a form swap move focus to the error summary or the thank-you box (spec §9).
document.addEventListener("htmx:afterSwap", (event) => {
  if (event.detail.requestConfig?.verb !== "post") return;
  const box = event.detail.target.querySelector(".form-errors[tabindex], .form-success[tabindex]");
  box?.focus();
});

function writeClipboard(text) {
  if (!text || !navigator.clipboard) return Promise.reject(new Error("clipboard unavailable"));
  return navigator.clipboard.writeText(text);
}

// components/share.html, media_library/materials_page.html — `data-copy` holds the text.
Alpine.data("copyButton", () => ({
  copied: false,
  copy() {
    const text = this.$el.dataset.copy || "";
    writeClipboard(text).then(
      () => {
        this.copied = true;
        setTimeout(() => (this.copied = false), 2500);
      },
      () => {},
    );
  },
}));

// components/embed_frame.html — click-to-load facade for Instagram / TikTok (spec §4.3).
Alpine.data("embedFacade", () => ({
  loaded: false,
  get idle() {
    return !this.loaded;
  },
  load() {
    this.loaded = true;
  },
}));

// tools/self_check_page.html — live count of ticked items; scoring stays on the server.
Alpine.data("checklist", () => ({
  count: 0,
  get label() {
    return this.count ? `${this.count} ✓` : "";
  },
  recount() {
    this.count = this.$root.querySelectorAll("input[type=checkbox]:checked").length;
  },
}));

// Horizontal rows (landing direction cards): «›» scrolls one screen on (wrapping to the start),
// «‹» one screen back. The arrows only show while the row overflows ([data-overflow]).
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-scroller-next], [data-scroller-prev]");
  if (!button) return;
  const track = button.closest("[data-scroller]")?.querySelector(".scroller__track");
  if (!track) return;
  const step = track.clientWidth * 0.9;
  if (button.hasAttribute("data-scroller-prev")) {
    track.scrollTo({ left: Math.max(0, track.scrollLeft - step), behavior: "smooth" });
    return;
  }
  const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
  track.scrollTo({ left: atEnd ? 0 : track.scrollLeft + step, behavior: "smooth" });
});
function markOverflow() {
  document.querySelectorAll("[data-scroller]").forEach((row) => {
    const track = row.querySelector(".scroller__track");
    if (track) row.toggleAttribute("data-overflow", track.scrollWidth > track.clientWidth + 4);
  });
}
markOverflow();
window.addEventListener("resize", markOverflow);

// A link to #q-12 / #bosqichlari opens that <details> (question cards, footer site map).
function openTarget() {
  const id = decodeURIComponent(location.hash.slice(1));
  // "" is not nullish: `id && …` left a string here and `target?.closest` threw on every page
  // without a hash — before Alpine.start(), so every widget died. Keep it null.
  const target = id ? document.getElementById(id) : null;
  if (!target) return;
  const details = target?.closest("details") || (target?.tagName === "DETAILS" ? target : null);
  if (details && !details.open) {
    details.open = true;
    target.scrollIntoView({ block: "start" });
  }
}
window.addEventListener("hashchange", openTarget);
openTarget();

document.documentElement.classList.remove("no-js");
Alpine.start();
initToolbar();
initConsent();
initNav();
