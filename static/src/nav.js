// components/nav.html — one <details> tree serves both layouts (works without JS on mobile).
// Desktop (≥ 64rem): the outer "Menu" disclosure is always open; «Bo'limlar» and the language
// menu are dropdowns — one open at a time, closed by Escape or a click outside.
// Inside «Bo'limlar» both sections are always expanded on desktop (CSS ::details-content).
// No-JS desktop is covered in CSS with ::details-content (components.css).
const DESKTOP = window.matchMedia("(min-width: 64rem)");

// EA-10: a scrolled tab bar opens with the current tab in view (no page scroll).
function revealActiveTab() {
  const list = document.querySelector(".section-tabs__list");
  const active = list?.querySelector(".is-active");
  if (!list || !active || list.scrollWidth <= list.clientWidth) return;
  const bar = list.getBoundingClientRect();
  const tab = active.getBoundingClientRect();
  list.scrollLeft += tab.left - bar.left - (bar.width - tab.width) / 2;
}

export function initNav() {
  revealActiveTab();
  const toggle = document.querySelector(".site-nav__toggle");
  if (!toggle) return;
  const dropdowns = [...document.querySelectorAll(".nav-dropdown")];
  const closeAll = (except) => dropdowns.forEach((d) => { if (d !== except) d.open = false; });

  const sync = () => {
    toggle.open = DESKTOP.matches;
    if (DESKTOP.matches) closeAll(null);
  };
  sync();
  DESKTOP.addEventListener("change", sync);

  dropdowns.forEach((dropdown) => {
    dropdown.addEventListener("toggle", () => {
      if (dropdown.open) closeAll(dropdown);
      // the search button opens a one-field panel: type straight away
      if (dropdown.open) dropdown.querySelector(".search-menu__panel input")?.focus();
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const open = dropdowns.find((d) => d.open);
    if (open) {
      open.open = false;
      open.querySelector("summary")?.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".nav-dropdown")) closeAll(null);
  });
}
