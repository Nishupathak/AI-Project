import Icon from "./Icon.jsx";
import { Meter } from "./charts.jsx";
import { api } from "../api.js";
import { useRobot } from "../robot.js";
import { clamp } from "../utils.js";

const STATES = {
  listening: { label: "Listening…", hint: "Speak any time" },
  hearing: { label: "Hearing you", hint: "Pause when you are done" },
  thinking: { label: "Thinking…", hint: "Working out your command" },
  speaking: { label: "Speaking", hint: "The mic pauses while I talk" },
  muted: { label: "Mic muted", hint: "Press the mic button to talk" },
};

export default function VoicePanel() {
  const { status } = useRobot();
  const state = status.mic ? (status.voice_state in STATES ? status.voice_state : "listening") : "muted";
  const th = status.mic_threshold || 300;
  const lvl = clamp((status.mic_level || 0) / (th * 5), 0, 1);
  const info = STATES[state];

  return (
    <section className="card">
      <h3 className="card-title"><Icon name="mic" size={14} /> Voice</h3>
      <div className="orb-wrap" data-state={state} style={{ "--lvl": lvl }}>
        <span className="ring r1" /><span className="ring r2" /><span className="ring r3" />
        <div className="orb"><Icon name={state === "muted" ? "micOff" : "mic"} size={30} stroke={1.8} /></div>
      </div>
      <div className="orb-label">{info.label}</div>
      <div className="orb-hint">{status.mic_error ? status.mic_error : info.hint}</div>
      <Meter
        label="Mic level"
        value={status.mic_level || 0}
        max={th * 5}
        mark={th}
        tone={state === "hearing" ? "ok" : "accent"}
        right={Math.round(status.mic_level || 0) + " / threshold " + Math.round(th)}
      />
      <div className="btn-row">
        <button className={"btn " + (status.mic ? "" : "ghost")} onClick={() => api.post("/mic/toggle")}>
          <Icon name={status.mic ? "mic" : "micOff"} size={16} /> {status.mic ? "Mic on" : "Mic off"}
        </button>
        <button className={"btn " + (status.voice_on ? "" : "ghost")} onClick={() => api.post("/voice/toggle")}>
          <Icon name={status.voice_on ? "volume" : "volumeOff"} size={16} /> {status.voice_on ? "Voice on" : "Voice off"}
        </button>
      </div>
    </section>
  );
}
