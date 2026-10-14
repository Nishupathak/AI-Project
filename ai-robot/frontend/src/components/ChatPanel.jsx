import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { api, run } from "../api.js";
import { useRobot } from "../robot.js";
import { useToast } from "../toasts.jsx";

const QUICK = ["Count my fingers", "How do I look", "What do you see", "Who am I", "Take a photo", "Tell me a joke"];

export default function ChatPanel() {
  const { status } = useRobot();
  const toast = useToast();
  const [text, setText] = useState("");
  const boxRef = useRef(null);
  const history = status.history || [];
  const last = history.length ? history[history.length - 1].robot : "";

  useEffect(() => {
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history.length, last]);

  const send = async (t) => {
    const v = t.trim();
    if (!v) return;
    setText("");
    try {
      await run(v);
    } catch {
      toast("Could not reach the robot", "bad");
    }
  };

  return (
    <section className="card chat">
      <div className="card-title-row">
        <h3 className="card-title"><Icon name="zap" size={14} /> Conversation</h3>
        <button className="btn ghost small" onClick={() => api.post("/history/clear")}>
          <Icon name="trash" size={14} /> Clear
        </button>
      </div>
      <div className="messages" ref={boxRef}>
        {history.length === 0 ? <div className="empty">Say something, or type a command below.</div> : null}
        {history.map((h, i) => (
          <div key={i} className="exchange">
            <div className="bubble you">{h.you}</div>
            <div className="bubble bot">{h.robot}</div>
          </div>
        ))}
        {status.voice_state === "thinking" ? <div className="bubble bot typing"><i /><i /><i /></div> : null}
      </div>
      <div className="chips">
        {QUICK.map((c) => (
          <button key={c} className="chip" onClick={() => send(c)}>{c}</button>
        ))}
      </div>
      <div className="inputrow">
        <input
          value={text}
          placeholder="Type a command, e.g. open telegram"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") send(text); }}
        />
        <button className="btn" onClick={() => send(text)} aria-label="Send"><Icon name="send" size={16} /></button>
      </div>
    </section>
  );
}
