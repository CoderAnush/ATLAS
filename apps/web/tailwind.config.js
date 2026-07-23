/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        atlas: {
          bg: "var(--atlas-bg)",
          panel: "var(--atlas-panel)",
          ink: "var(--atlas-ink)",
          muted: "var(--atlas-muted)",
          accent: "var(--atlas-accent)",
          line: "var(--atlas-line)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
