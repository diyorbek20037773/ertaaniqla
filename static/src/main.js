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

document.documentElement.classList.remove("no-js");
Alpine.start();
initToolbar();
initConsent();
initNav();
