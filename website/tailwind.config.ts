import type { Config } from "tailwindcss";

/**
 * nf-claw design system.
 * Derived from the brand logo: white line-art on black, a vivid apple-green
 * primary accent and a warm cream secondary (the apple's bite).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces — a deep, near-black scale with subtle elevation.
        ink: {
          DEFAULT: "#07080A",
          950: "#050608",
          900: "#0A0B0E",
          800: "#101216",
          700: "#16191F",
          600: "#1E222A",
          500: "#2A2F39",
        },
        // Brand apple-green.
        claw: {
          50: "#E9FBEF",
          100: "#C9F5D6",
          200: "#94EBB0",
          300: "#5FDD86",
          400: "#39D353",
          500: "#28BA47",
          600: "#1E9A3A",
          700: "#1A7A30",
          800: "#175E29",
          900: "#124B22",
        },
        // Warm cream (the apple bite) — secondary accent.
        cream: {
          DEFAULT: "#EFE6B8",
          soft: "#F4EECB",
          deep: "#D8C98A",
        },
        // Neutral text scale.
        fog: {
          DEFAULT: "#F4F5F6",
          muted: "#9AA0AA",
          dim: "#7C838E", // ≥ 4.5:1 on every surface the site uses (WCAG AA for small text)
          faint: "#3A404A",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.045em",
        tighter: "-0.03em",
      },
      maxWidth: {
        site: "1240px",
        prose: "72ch",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(57,211,83,0.12), 0 24px 80px -32px rgba(57,211,83,0.25)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(to right, rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.025) 1px, transparent 1px)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.9)", opacity: "0.7" },
          "100%": { transform: "scale(2.4)", opacity: "0" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "pulse-ring": "pulse-ring 3s cubic-bezier(0.16,1,0.3,1) infinite",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16,1,0.3,1)",
      },
    },
  },
  plugins: [],
};

export default config;
