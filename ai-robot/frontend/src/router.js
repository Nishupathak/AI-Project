import { useEffect, useState } from "react";

export const PAGES = ["dashboard", "analytics", "console", "gallery", "about"];

const read = () => {
  if (typeof window === "undefined") return "dashboard";
  const h = window.location.hash.replace(/^#\/?/, "");
  return PAGES.includes(h) ? h : "dashboard";
};

// Tiny hash router: #/analytics, #/console ... (no extra dependency needed)
export function useRoute() {
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const go = (page) => {
    window.location.hash = "/" + page;
  };
  return [route, go];
}
