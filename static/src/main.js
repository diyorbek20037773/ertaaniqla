// Entry point bundled by esbuild (npm run build:js) → static/dist/main.js
// HTMX + Alpine are vendored through npm and bundled here so no third-party CDN is needed (CSP).
import htmx from "htmx.org";
import Alpine from "alpinejs";

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

document.documentElement.classList.remove("no-js");
Alpine.start();
