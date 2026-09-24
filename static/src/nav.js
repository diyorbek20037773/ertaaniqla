// components/nav.html — one <details> tree serves both layouts (works without JS on mobile).
// Desktop (≥ 64rem): the outer "Menu" disclosure is always open and each section's
// mega-menu behaves as a dropdown — one open at a time, closed by Escape or an outside click.
// No-JS desktop is covered in CSS with ::details-content (components.css).
const DESKTOP = window.matchMedia("(min-width: 64rem)");

export function initNav() {
  const toggle = document.querySelector(".site-nav__toggle");
  if (!toggle) return;
  const menus = [...document.querySelectorAll(".mega-menu")];
  const closeAll = (except) => menus.forEach((m) => { if (m !== except) m.open = false; });

  const sync = () => {
    toggle.open = DESKTOP.matches;
    if (DESKTOP.matches) closeAll(null);
  };
  sync();
  DESKTOP.addEventListener("change", sync);

  menus.forEach((menu) => {
    menu.addEventListener("toggle", () => {
      if (DESKTOP.matches && menu.open) closeAll(menu);
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !DESKTOP.matches) return;
    const open = menus.find((m) => m.open);
    if (open) {
      open.open = false;
      open.querySelector("summary")?.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (DESKTOP.matches && !event.target.closest(".mega-menu")) closeAll(null);
  });
}
