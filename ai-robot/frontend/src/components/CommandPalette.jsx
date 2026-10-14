import { useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { run } from "../api.js";
import { useToast } from "../toasts.jsx";

const COMMANDS = [
  { label: "Count my fingers", cmd: "count my fingers", icon: "hand" },
  { label: "How do I look?", cmd: "how do i look", icon: "smile" },
  { label: "What do you see?", cmd: "what do you see", icon: "eye" },
  { label: "Who am I?", cmd: "who am i", icon: "fingerprint" },
  { label: "How old am I?", cmd: "how old am i", icon: "user" },
  { label: "Take a photo", cmd: "take a photo", icon: "camera" },
  { label: "What time is it?", cmd: "what time is it", icon: "zap" },
  { label: "Tell me a joke", cmd: "tell me a joke", icon: "smile" },
  { label: "Open Telegram", cmd: "open telegram", icon: "play" },
  { label: "Search Google for…", prefill: "search ", icon: "search" },
  { label: "Remember me as…", prefill: "remember me as ", icon: "users" },
  { label: "Forget everyone", cmd: "forget everyone", icon: "trash" },
];

export default function CommandPalette({ open, onClose }) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const inputRef = useRef(null);
  const toast = useToast();

  const items = useMemo(() => {
    const list = COMMANDS.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()));
    if (q.trim()) list.push({ label: "Send: “" + q.trim() + "”", cmd: q.trim(), icon: "send" });
    return list;
  }, [q]);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setIdx(0);
    const t = setTimeout(() => { if (inputRef.current) inputRef.current.focus(); }, 30);
    return () => clearTimeout(t);
  }, [open]);

  const choose = async (item) => {
    if (!item) return;
    if (item.prefill) {
      setQ(item.prefill);
      setIdx(0);
      if (inputRef.current) inputRef.current.focus();
      return;
    }
    onClose();
    try {
      await run(item.cmd);
      toast("Sent to robot: " + item.cmd);
    } catch {
      toast("Could not reach the robot", "bad");
    }
  };

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(items.length - 1, i + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(items[idx]); }
    else if (e.key === "Escape") onClose();
  };

  if (!open) return null;
  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <div className="palette" onMouseDown={(e) => e.stopPropagation()}>
        <div className="palette-input">
          <Icon name="search" size={18} />
          <input
            ref={inputRef}
            value={q}
            placeholder="Type a command or pick one…"
            onChange={(e) => { setQ(e.target.value); setIdx(0); }}
            onKeyDown={onKey}
          />
          <kbd>Esc</kbd>
        </div>
        <div className="palette-list">
          {items.map((it, i) => (
            <button key={it.label} className={"palette-item " + (i === idx ? "on" : "")} onMouseEnter={() => setIdx(i)} onClick={() => choose(it)}>
              <Icon name={it.icon} size={16} /> <span>{it.label}</span>
            </button>
          ))}
          {items.length === 0 ? <div className="muted small" style={{ padding: 14 }}>Nothing matches.</div> : null}
        </div>
      </div>
    </div>
  );
}
