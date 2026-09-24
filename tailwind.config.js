/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./apps/**/*.py",
    "./static/src/**/*.js",
  ],
  // Modifier classes built in templates from data (`callout--{{ kind }}`,
  // `tool-result--{{ level }}`, `share__link--{{ key }}` …) never appear literally, so the
  // purge dropped them and the urgency colours silently vanished. Keep every BEM modifier.
  // Guarded by tests/perf/test_budgets.py::test_every_component_modifier_survives_the_purge.
  safelist: [{ pattern: /^(callout|tool-result|tool-result__test|share__link|symptom|steps|video|embed|pill|button|field|capsule-card|search-result|institution|material|cards-grid|text-card|text-cards|cta)--[a-z0-9_-]+$/ }],
  theme: {
    extend: {
      colors: {
        brand: "var(--brand)",
        "brand-soft": "var(--brand-soft)",
        info: "var(--info)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        // Figma palette (M5b, ADR-0006) — see static/src/tokens.css
        pink: {
          200: "var(--c-pink-200)",
          300: "var(--c-pink-300)",
          400: "var(--c-pink-400)",
          500: "var(--c-pink-500)",
          600: "var(--c-pink-600)",
          700: "var(--c-pink-700)",
          800: "var(--c-pink-800)",
          900: "var(--c-pink-900)",
        },
        purple: {
          300: "var(--c-purple-300)",
          400: "var(--c-purple-400)",
          600: "var(--c-purple-600)",
          700: "var(--c-purple-700)",
          900: "var(--c-purple-900)",
        },
        lime: "var(--c-lime)",
      },
      fontFamily: { sans: "var(--font-sans)" },
      fontSize: {
        hero: "var(--fs-hero)",
        "hero-sub": "var(--fs-hero-sub)",
        h1: "var(--fs-h1)",
        h2: "var(--fs-h2)",
        h3: "var(--fs-h3)",
        body: "var(--fs-body)",
        lead: "var(--fs-lead)",
        ui: "var(--fs-ui)",
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        glass: "var(--radius-glass)",
        capsule: "var(--radius-capsule)",
        stage: "var(--radius-stage)",
        pill: "var(--radius-pill)",
      },
      boxShadow: { card: "var(--shadow-card)", float: "var(--shadow-float)" },
      maxWidth: { measure: "var(--measure)", container: "var(--container)" },
      minHeight: { tap: "var(--tap-target)" },
    },
  },
  corePlugins: { preflight: true },
  plugins: [],
};
