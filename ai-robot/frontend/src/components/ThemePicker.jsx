import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { ACCENTS, useTheme } from "../theme.jsx";

export default function ThemePicker() {
  const { mode, accent, setMode, setAccent } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="theme-picker" ref={ref}>
      <button className="icon-btn" onClick={() => setOpen((o) => !o)} aria-label="Theme" title="Theme">
        <Icon name="palette" size={18} />
      </button>
      {open ? (
        <div className="popover">
          <div className="sub">Mode</div>
          <div className="segmented">
            <button className={mode === "dark" ? "on" : ""} onClick={() => setMode("dark")}><Icon name="moon" size={14} /> Dark</button>
            <button className={mode === "light" ? "on" : ""} onClick={() => setMode("light")}><Icon name="sun" size={14} /> Light</button>
          </div>
          <div className="sub" style={{ marginTop: 14 }}>Accent colour</div>
          <div className="swatches">
            {Object.entries(ACCENTS).map(([key, c]) => (
              <button
                key={key}
                className={"swatch " + (accent === key ? "on" : "")}
                style={{ background: "linear-gradient(135deg, " + c.a + ", " + c.b + ")" }}
                onClick={() => setAccent(key)}
                title={c.label}
                aria-label={c.label}
              >
                {accent === key ? <Icon name="check" size={14} stroke={3} /> : null}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
