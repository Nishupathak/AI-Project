import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const ACCENTS = {
  cyan: { label: "Cyan", a: "#22d3ee", b: "#6366f1" },
  violet: { label: "Violet", a: "#a78bfa", b: "#ec4899" },
  emerald: { label: "Emerald", a: "#34d399", b: "#22d3ee" },
  amber: { label: "Amber", a: "#fbbf24", b: "#f97316" },
  rose: { label: "Rose", a: "#fb7185", b: "#a78bfa" },
  ocean: { label: "Ocean", a: "#60a5fa", b: "#34d399" },
};

const hexToRgb = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return ((n >> 16) & 255) + ", " + ((n >> 8) & 255) + ", " + (n & 255);
};

function load(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}
function save(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* private mode: ignore */
  }
}

const ThemeContext = createContext({
  mode: "dark", accent: "cyan", setMode: () => {}, setAccent: () => {}, toggleMode: () => {},
});

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    if (typeof window === "undefined") return "dark";
    const saved = load("robot-mode", "");
    if (saved) return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });
  const [accent, setAccent] = useState(() => (typeof window === "undefined" ? "cyan" : load("robot-accent", "cyan")));

  useEffect(() => {
    const root = document.documentElement;
    const c = ACCENTS[accent] || ACCENTS.cyan;
    root.dataset.theme = mode;
    root.style.setProperty("--accent", c.a);
    root.style.setProperty("--accent2", c.b);
    root.style.setProperty("--accent-rgb", hexToRgb(c.a));
    save("robot-mode", mode);
    save("robot-accent", accent);
  }, [mode, accent]);

  const value = useMemo(
    () => ({ mode, accent, setMode, setAccent, toggleMode: () => setMode((m) => (m === "dark" ? "light" : "dark")) }),
    [mode, accent]
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
