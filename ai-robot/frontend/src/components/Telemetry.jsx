import Icon from "./Icon.jsx";
import { fmtUptime } from "../utils.js";

export default function Telemetry({ system }) {
  return (
    <section className="card">
      <div className="card-title-row">
        <h3 className="card-title"><Icon name="cpu" size={14} /> AI pipeline &amp; telemetry</h3>
        <span className="tag">{system.fps || 0} FPS · up {fmtUptime(system.uptime_s)}</span>
      </div>
      <div className="models">
        {(system.models || []).map((m) => (
          <div className="model" key={m.name}>
            <span className={"status-dot " + (m.ready ? "ok" : "bad")} />
            <div>
              <div className="model-name">{m.name}</div>
              <div className="model-detail">{m.detail}</div>
            </div>
            <span className={"tag " + (m.ready ? "ok" : "bad")}>{m.ready ? "ready" : "not ready"}</span>
          </div>
        ))}
        {(system.models || []).length === 0 ? <div className="muted small">Waiting for the backend…</div> : null}
      </div>
    </section>
  );
}
