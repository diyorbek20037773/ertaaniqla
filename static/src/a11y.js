// Accessibility toolbar (spec §9, A8): font scale, high contrast, reduce motion.
// State lives in localStorage("ea-a11y") and is mirrored to <html data-*> attributes that
// tokens.css reacts to. base.html applies the stored state early (inline nonce'd script) so
// there is no flash; this module wires the buttons.
const KEY = "ea-a11y";

export function readState() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}") || {};
  } catch (e) {
    return {};
  }
}

export function applyState(state) {
  const root = document.documentElement;
  if (state.font && state.font !== "100") root.setAttribute("data-font-scale", state.font);
  else root.removeAttribute("data-font-scale");
  if (state.contrast) root.setAttribute("data-contrast", "high");
  else root.removeAttribute("data-contrast");
  if (state.motion) root.setAttribute("data-reduce-motion", "true");
  else root.removeAttribute("data-reduce-motion");
}

function save(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (e) {
    /* private mode: keep in-memory only */
  }
}

function syncButtons(toolbar, state) {
  toolbar.querySelectorAll("[data-a11y]").forEach((button) => {
    const kind = button.dataset.a11y;
    let pressed = false;
    if (kind === "font") pressed = (state.font || "100") === button.dataset.value;
    if (kind === "contrast") pressed = Boolean(state.contrast);
    if (kind === "motion") pressed = Boolean(state.motion);
    button.setAttribute("aria-pressed", pressed ? "true" : "false");
  });
}

export function initToolbar() {
  const toolbar = document.querySelector('[data-component="a11y-toolbar"]');
  if (!toolbar) return;
  const state = readState();
  applyState(state);
  syncButtons(toolbar, state);
  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-a11y]");
    if (!button) return;
    const kind = button.dataset.a11y;
    if (kind === "font") state.font = button.dataset.value;
    if (kind === "contrast") state.contrast = !state.contrast;
    if (kind === "motion") state.motion = !state.motion;
    applyState(state);
    save(state);
    syncButtons(toolbar, state);
  });
}
