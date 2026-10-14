import { useEffect, useRef, useState } from "react";
import Icon from "./components/Icon.jsx";
import ThemePicker from "./components/ThemePicker.jsx";
import CommandPalette from "./components/CommandPalette.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import Console from "./pages/Console.jsx";
import Gallery from "./pages/Gallery.jsx";
import About from "./pages/About.jsx";
import { api, usePoll } from "./api.js";
import { RobotContext } from "./robot.js";
import { useRoute } from "./router.js";
import { ThemeProvider } from "./theme.jsx";
import { ToastProvider, useToast } from "./toasts.jsx";
import { EMPTY_STATUS } from "./utils.js";

const NAV = [
  { id: "dashboard", label: "Live", icon: "grid" },
  { id: "analytics", label: "Analytics", icon: "chart" },
  { id: "console", label: "Console", icon: "terminal" },
  { id: "gallery", label: "Gallery", icon: "image" },
  { id: "about", label: "About", icon: "info" },
];
const PAGES = { dashboard: Dashboard, analytics: Analytics, console: Console, gallery: Gallery, about: About };

function Shell() {
  const [status, online] = usePoll("/status", 600, EMPTY_STATUS);
  const [route, go] = useRoute();
  const [palette, setPalette] = useState(false);
  const toast = useToast();
  const wasOnline = useRef(true);
  const Page = PAGES[route] || Dashboard;

  // Ctrl/Cmd + K opens the command palette
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // tell the user when the backend disappears or comes back
  useEffect(() => {
    if (wasOnline.current && !online) toast("Lost connection to the robot server", "bad");
    if (!wasOnline.current && online) toast("Reconnected", "ok");
    wasOnline.current = online;
  }, [online, toast]);

  return (
    <RobotContext.Provider value={{ status, online }}>
      <div className="shell">
        <aside className="sidebar">
          <div className="logo">
            <span className="logo-mark">🤖</span>
            <span className="logo-text grad-text">AI Robot</span>
          </div>
          <nav>
            {NAV.map((n) => (
              <button key={n.id} className={"nav-item " + (route === n.id ? "on" : "")} onClick={() => go(n.id)}>
                <Icon name={n.icon} size={19} />
                <span>{n.label}</span>
              </button>
            ))}
          </nav>
          <div className="sidebar-foot">
            <span className={"status-dot " + (online ? "ok" : "bad")} />
            <span>{online ? "Server online" : "Offline"}</span>
          </div>
        </aside>

        <div className="main">
          <header className="topbar">
            <button className="palette-btn" onClick={() => setPalette(true)}>
              <Icon name="search" size={16} />
              <span>Run a command…</span>
              <kbd>Ctrl K</kbd>
            </button>
            <div className="top-actions">
              <span className={"tag " + (status.llm ? "ok" : "")}>
                <Icon name="zap" size={12} /> {status.llm ? "Brain: " + status.llm : "Brain: keywords"}
              </span>
              <button className="icon-btn" onClick={() => api.post("/voice/toggle")} title="Toggle spoken replies" aria-label="Toggle spoken replies">
                <Icon name={status.voice_on ? "volume" : "volumeOff"} size={18} />
              </button>
              <button className="icon-btn" onClick={() => api.post("/mic/toggle")} title="Toggle microphone" aria-label="Toggle microphone">
                <Icon name={status.mic ? "mic" : "micOff"} size={18} />
              </button>
              <ThemePicker />
            </div>
          </header>
          <main className="content" key={route}>
            <Page />
          </main>
        </div>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </RobotContext.Provider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <Shell />
      </ToastProvider>
    </ThemeProvider>
  );
}
