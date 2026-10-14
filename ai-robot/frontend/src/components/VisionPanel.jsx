import { useState } from "react";
import Icon from "./Icon.jsx";
import { useRobot } from "../robot.js";
import { exprInfo } from "../utils.js";

function Chip({ icon, label, value, color }) {
  return (
    <div className="chip-stat">
      <span className="chip-icon" style={{ color }}><Icon name={icon} size={16} /></span>
      <div>
        <div className="chip-value">{value}</div>
        <div className="chip-label">{label}</div>
      </div>
    </div>
  );
}

export default function VisionPanel() {
  const { status } = useRobot();
  const [nonce, setNonce] = useState(0);
  const [failed, setFailed] = useState(false);
  const ex = exprInfo(status.expression);

  return (
    <section className="card vision">
      <div className="vision-frame">
        {!failed ? (
          <img
            src={"/video?n=" + nonce}
            alt="Live camera feed"
            onError={() => setFailed(true)}
            onLoad={() => setFailed(false)}
          />
        ) : (
          <div className="vision-fallback">
            <Icon name="camera" size={34} />
            <p>Waiting for the camera stream…</p>
            <button className="btn ghost" onClick={() => { setFailed(false); setNonce((n) => n + 1); }}>
              <Icon name="refresh" size={15} /> Retry
            </button>
          </div>
        )}
        <span className="corner tl" /><span className="corner tr" /><span className="corner bl" /><span className="corner br" />
        <div className="scan" />
        <div className="badge live"><span className="dot" /> LIVE{status.fps ? " · " + status.fps + " FPS" : ""}</div>
        <div className="badge expr" style={{ borderColor: ex.color }}>{ex.emoji} {status.expression}</div>
      </div>
      <div className="chip-row">
        <Chip icon="eye" label="Faces" value={status.faces} color="var(--ok)" />
        <Chip icon="hand" label="Fingers" value={status.fingers} color="var(--accent)" />
        <Chip icon="smile" label="Expression" value={status.expression} color={ex.color} />
        <Chip icon="user" label="Person" value={status.person} color="var(--warn)" />
      </div>
    </section>
  );
}
