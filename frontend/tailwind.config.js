/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#fafaf7",
          100: "#f3f2ec",
          200: "#e6e3d8",
          300: "#cfcabb",
          400: "#9a9485",
          500: "#6b6759",
          600: "#4a473d",
          700: "#33312a",
          800: "#22211c",
          900: "#13120f",
        },
        accent: {
          DEFAULT: "#b45309",
          soft: "#fef3c7",
        },
        good: {
          DEFAULT: "#047857",
          soft: "#d1fae5",
        },
        bad: {
          DEFAULT: "#b91c1c",
          soft: "#fee2e2",
        },
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
