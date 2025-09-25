/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html","./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#1f6feb", dark: "#0d419d" }
      },
      boxShadow: { card: "0 8px 24px rgba(31,111,235,0.08)" },
      borderRadius: { xl2: "1rem" }
    },
  },
  plugins: [ require('@tailwindcss/typography') ],
}
