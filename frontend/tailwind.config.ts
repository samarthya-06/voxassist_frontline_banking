import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#faf9fe",
        surface: "#faf9fe",
        "surface-bright": "#faf9fe",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f4f3f8",
        "surface-container": "#eeedf2",
        "surface-container-high": "#e8e7ed",
        "surface-container-highest": "#e3e2e7",
        "surface-variant": "#e3e2e7",
        "surface-dim": "#dad9df",
        "on-surface": "#1a1b1f",
        "on-surface-variant": "#43474f",
        outline: "#747781",
        "outline-variant": "#c4c6d1",
        primary: "#00193c",
        "primary-container": "#002d62",
        "on-primary": "#ffffff",
        "on-primary-container": "#7796d1",
        "primary-fixed": "#d7e2ff",
        "primary-fixed-dim": "#abc7ff",
        "on-primary-fixed": "#001b3f",
        "on-primary-fixed-variant": "#24467c",
        secondary: "#505f76",
        "secondary-container": "#d0e1fb",
        "on-secondary": "#ffffff",
        "on-secondary-container": "#54647a",
        "secondary-fixed": "#d3e4fe",
        "secondary-fixed-dim": "#b7c8e1",
        "on-secondary-fixed": "#0b1c30",
        "on-secondary-fixed-variant": "#38485d",
        error: "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a"
      },
      borderRadius: {
        sm: "0.125rem",
        DEFAULT: "0.25rem",
        md: "0.375rem",
        lg: "0.5rem",
        xl: "0.75rem"
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"]
      },
      fontSize: {
        h1: ["24px", { lineHeight: "32px", fontWeight: "600" }],
        h2: ["18px", { lineHeight: "24px", fontWeight: "600" }],
        h3: ["16px", { lineHeight: "20px", fontWeight: "600" }],
        base: ["14px", { lineHeight: "20px" }],
        sm: ["13px", { lineHeight: "18px" }],
        caps: ["11px", { lineHeight: "16px", fontWeight: "700", letterSpacing: "0.05em" }]
      }
    }
  },
  plugins: []
};

export default config;
