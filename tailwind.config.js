/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./apps/**/*.py",
    "./static/src/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        brand: "var(--brand)",
        "brand-soft": "var(--brand-soft)",
        info: "var(--info)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      fontFamily: { sans: "var(--font-sans)" },
      maxWidth: { measure: "var(--measure)", container: "var(--container)" },
      minHeight: { tap: "var(--tap-target)" },
    },
  },
  corePlugins: { preflight: true },
  plugins: [],
};
