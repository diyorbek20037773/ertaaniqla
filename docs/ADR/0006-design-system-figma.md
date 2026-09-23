# ADR-0006 — Design system from Figma (M5b)

Status: accepted · Date: 2026-09-23 · Follows: ADR-0005 · Implements: DECISIONS D-003

## Context

D-003 froze the UI at wireframe level: every visual value lives in `static/src/tokens.css` and
`templates/components/`, so a design could be applied without touching Python. The designer's
file arrived — Figma `Erta aniqla` (`y76CeUEqpXAuCtaJxB5LUk`), 7 desktop frames at 1728 px:

| Frame | node-id |
|---|---|
| Landing page | `2408:5` |
| Ayollar saratoni — ko'krak bezi | `2408:194` |
| Skrining | `2408:940` |
| Davolashni tashkil etish | `2408:1396` |
| Qo'llab-quvvatlash | `2408:1794` |
| Kasallikdan keyingi hayot | `2408:2128` |
| Ayollar saratoni — bachadon bo'yni | `2408:2489` |

The file defines no Figma variables — every colour, size and radius is a raw value on a node.

## Decision

### 1. Tokens, not hexes
Every value read off the Figma nodes is named in `tokens.css` (`--c-pink-*`, `--c-purple-*`,
`--c-lime`, `--grad-*`, `--glass-*`, `--fs-*`, `--radius-*`). Templates and `components.css`
reference tokens only; no template ever carries a hex. D-003's contract is preserved: **no Python
changes** are required by the design.

### 2. Type scale is fluid, not fixed
Figma specifies one viewport (1728 px). The portal is mobile-first on 3G (spec §5), so each Figma
size became a `clamp()` between a mobile value at 390 px and the Figma value at 1728 px
(`--fs-hero` 36→96 px, `--fs-body` 18→32 px, …). Radii scale the same way — a 200 px capsule on a
390 px screen would swallow the card. The scale stays in `rem`, so the accessibility toolbar's
×1.25 / ×1.5 still works.

### 3. Typeface: Albert Sans, self-hosted, with a Cyrillic fallback
CSP is `font-src 'self'` (§8) — no Google Fonts CDN. Albert Sans (OFL 1.1) is served from
`static/fonts/` as two variable `woff2` files (latin, latin-ext) plus italics. **Albert Sans has
no Cyrillic subset**, so `ru` and `uz_Cyrl` fall back to Manrope (OFL 1.1) through
`unicode-range`; Cyrillic italics are synthesised. Per-language cost: uz ≈ 32 KB, ru ≈ 15 KB.

### 4. Contrast: Figma is kept pixel-perfect; AA lives in the high-contrast theme
**Client decision, 2026-09-23.** The designer's pink/purple fills are part of the brand and
darkening them (the AA-compliant option) pushed the cards visually in front of the hero. So:

* the default theme reproduces Figma exactly, including white text on `--c-pink-300`
  (≈ 2.3:1) and gradient headings;
* `html[data-contrast="high"]` collapses every gradient and glass surface to solid
  black-on-white / yellow and **is fully WCAG 2.1 AA**; the toolbar is on every page and its
  state persists in `localStorage`;
* everything else stays AA regardless of theme: focus rings, keyboard order, target size ≥ 44 px,
  alt text, heading order, form labels, motion and transparency preferences.

**Consequence — CI gates change:** `lighthouserc.json` `categories:accessibility` moves from
`error ≥ 0.95` to `warn ≥ 0.90`, and pa11y ignores `color-contrast` on the default theme while a
dedicated run asserts AA with `data-contrast="high"`. This is a documented deviation from the
CLAUDE.md non-negotiable "WCAG 2.1 AA"; it is recorded in `docs/TZ_TRACE.md` against the
accessibility row, with the date and the decision-maker.

### 5. Glass surfaces degrade
`backdrop-filter: blur(12.25px)` on large cards is expensive on low-end Android over 3G. The
blur is applied through `--glass-blur`, which drops to `0px` under
`@media (prefers-reduced-transparency: reduce)` and in the high-contrast theme; the surface stays
readable because the border and the 36 % white fill carry the shape.

### 6. Information architecture stays TZ, visuals come from Figma
The Figma header shows five links (Asosiy / Haqimizda / Bo'limlar / Shifokorlar / Savol-Javob),
which contradicts TZ §II (two sections, 🎗 / 🎀, five menu items each). Per CLAUDE.md the TZ wins:
the menu **structure** is unchanged, only its appearance follows Figma (italic links, `Uz` pill,
gradient search pill, per-topic tab bar on inner pages).

### 7. Children's section waits
Figma has no interior pages for the children's section — the client is designing them and the
pattern and illustrations will change. M5b therefore ships the purple token set and the shared
structure; the children's visuals land in a follow-up (M5c) when those frames exist.

### 8. Medical copy is not imported
The Figma frames contain finished medical text. Per CLAUDE.md that text is **not** copied into
templates or fixtures; only structure is implemented and the seeds keep
`[[TODO: content — copywriter]]` / `[[VERIFY: doctor]]`.

## Consequences

* `tokens.css`, `fonts.css`, `components.css`, `tailwind.config.js` and the templates change;
  no migrations, no Python.
* Assets (logo, blobs, ribbon, bow, icons, illustrations) are committed under
  `static/img/figma/` — Figma's asset URLs expire after 7 days, so nothing may reference them.
* CSS budget: 7.4 KB gz after M5b-1 (limit 40 KB); fonts add ≈ 32 KB per language, outside the
  CSS budget but inside the LCP budget — hence `font-display: swap` and subsetting.
* The default theme is knowingly below AA on colour contrast. Anyone changing that needs a new
  ADR, not a code review comment.
