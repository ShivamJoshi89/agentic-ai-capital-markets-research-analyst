/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0a0e1a",
          800: "#0d1224",
          700: "#141929",
          600: "#1e2d4a",
        },
        gold: {
          DEFAULT: "#f0b429",
          light: "#f7d070",
        },
        success: "#00c851",
        danger: "#ff4444",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
