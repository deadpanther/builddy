/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Bento warm palette
        bento: {
          peach: "#FAD4C0",
          sky: "#80A1C1",
          sand: "#FFF5E6",
          cream: "#FEF7EC",
          shell: "#F5EDE3",
          ink: "#1C1917",
          charcoal: "#292524",
          slate: "#57534E",
          mist: "#D6D3D1",
        },
        brand: {
          50: "#FFF1EB",
          100: "#FFE0D1",
          200: "#FFC2A3",
          300: "#FFA375",
          400: "#FF8547",
          500: "#F06225",
          600: "#D94E1A",
          700: "#B33D14",
          800: "#8C2F0F",
          900: "#66220A",
          950: "#401506",
        },
        surface: {
          DEFAULT: "#09090b",
          50: "#18181b",
          100: "#1c1c1f",
          200: "#232326",
          300: "#2a2a2e",
          400: "#323236",
        },
        panel: {
          DEFAULT: "rgba(24, 24, 27, 0.6)",
          hover: "rgba(34, 34, 39, 0.7)",
          active: "rgba(42, 42, 46, 0.8)",
        },
        stroke: {
          DEFAULT: "rgba(63, 63, 70, 0.5)",
          hover: "rgba(82, 82, 91, 0.6)",
          active: "rgba(113, 113, 122, 0.5)",
        },
        success: {
          DEFAULT: "#16A34A",
          dim: "rgba(22, 163, 74, 0.15)",
          border: "rgba(22, 163, 74, 0.3)",
        },
        warning: {
          DEFAULT: "#D97706",
          dim: "rgba(217, 119, 6, 0.15)",
          border: "rgba(217, 119, 6, 0.3)",
        },
        danger: {
          DEFAULT: "#DC2626",
          dim: "rgba(220, 38, 38, 0.15)",
          border: "rgba(220, 38, 38, 0.3)",
        },
        info: {
          DEFAULT: "#80A1C1",
          dim: "rgba(128, 161, 193, 0.15)",
          border: "rgba(128, 161, 193, 0.3)",
        },
        // Legacy autopsy/terminal colors (preserved)
        autopsy: {
          bg: "#09090b",
          surface: "#0d1117",
          panel: "#111111",
          border: "#21262d",
          "border-light": "#30363d",
        },
        terminal: {
          green: "#00ff41",
          "green-dim": "#00b330",
          amber: "#d29922",
          red: "#f85149",
        },
        evidence: { blue: "#58a6ff" },
        revival: { green: "#00ff41", emerald: "#10b981", purple: "#a78bfa" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "-apple-system", "sans-serif"],
        display: ['"Fraunces"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
        typewriter: ['"Courier Prime"', "Courier", "monospace"],
      },
      borderRadius: {
        bento: "16px",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        bento: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.06)",
        "bento-hover": "0 2px 8px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.1)",
        "bento-dark": "0 1px 3px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.4)",
        "bento-dark-hover": "0 2px 8px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.5)",
        glass: "0 0 0 1px rgba(63, 63, 70, 0.3), 0 1px 3px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.2)",
        "glass-hover": "0 0 0 1px rgba(82, 82, 91, 0.4), 0 2px 8px rgba(0, 0, 0, 0.4), 0 12px 32px rgba(0, 0, 0, 0.25)",
        "inner-glow": "inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 0 0 1px rgba(63, 63, 70, 0.3), 0 1px 3px rgba(0, 0, 0, 0.3)",
        glow: "0 0 20px rgba(240, 98, 37, 0.15), 0 0 0 1px rgba(240, 98, 37, 0.2)",
      },
      backgroundImage: {
        "grid-pattern": "linear-gradient(rgba(63, 63, 70, 0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(63, 63, 70, 0.15) 1px, transparent 1px)",
        "grid-pattern-light": "linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px)",
        "radial-fade": "radial-gradient(ellipse at top, rgba(240, 98, 37, 0.06) 0%, transparent 60%)",
        "radial-fade-light": "radial-gradient(ellipse at top, rgba(240, 98, 37, 0.08) 0%, transparent 60%)",
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out forwards",
        "fade-in": "fade-in 0.3s ease-out forwards",
        "scale-in": "scale-in 0.2s ease-out forwards",
        "slide-up": "slide-up 0.3s ease-out forwards",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
