/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class", // dark mode activé via une classe .dark sur <html>
  theme: {
    extend: {
      colors: {
        // Palette turquoise — la couleur de marque
        brand: {
          50: "#effcfb",
          100: "#d7f5f3",
          200: "#b0eae8",
          300: "#7ad9d7",
          400: "#3fbfbf",
          500: "#1fa3a6", // couleur principale
          600: "#16828a",
          700: "#166970",
          800: "#17545b",
          900: "#17464d",
          950: "#082b31",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      keyframes: {
        orbPulse: {
          "0%, 100%": { opacity: "0.15", transform: "scale(1)" },
          "50%": { opacity: "0.3", transform: "scale(1.15)" },
        },
        widgetIn: {
          "0%": { opacity: "0", transform: "scale(0.92) translateY(8px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        robotIdle: {
          "0%": { transform: "rotateY(0deg)" },
          "100%": { transform: "rotateY(360deg)" },
        },
        bubbleIn: {
          "0%": { opacity: "0", transform: "translateY(6px) scale(0.9)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
      },
      animation: {
        "orb-pulse": "orbPulse 2.4s ease-in-out infinite",
        "widget-in": "widgetIn 0.25s ease-out",
        "robot-idle": "robotIdle 4s linear infinite",
        "bubble-in": "bubbleIn 0.4s ease-out 0.8s both",
      },
    },
  },
  plugins: [],
};