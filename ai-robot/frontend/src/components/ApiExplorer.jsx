import { useState } from "react";
import Icon from "./Icon.jsx";
import { timed } from "../api.js";

const ENDPOINTS = [
  { method: "GET", path: "/status", desc: "Live robot state: faces, fingers, voice state, emotion signals" },
  { method: "GET", path: "/system", desc: "Model readiness, FPS, uptime, command latencies" },
  { method: "GET", path: "/identify", desc: "Face embedding and cosine similarity to each saved person" },
  { method: "GET", path: "/people", desc: "Names of saved faces" },
  { method: "GET", path: "/stats", desc: "Database counters" },
  { method: "GET", path: "/history?limit=5", desc: "Last messages from SQLite" },
  { method: "GET", path: "/detections/summary", desc: "Expression counts + recent detections" },
  { method: "GET", path: "/detections/timeline?minutes=30", desc: "Detections per minute" },
  { method: "GET", path: "/photos", desc: "Saved snapshots" },
  { method: "GET", path: "/llm/test", desc: "Self-test of the LLM connection" },
  { method: "POST", path: "/command", desc: "Run a command exactly as if spoken", body: '{"text":"what time is it"}' },
];

export default function ApiExplorer() {
  const [sel, setSel] = useState(0);
  const [body, setBody] = useState(ENDPOINTS[10].body);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const ep = ENDPOINTS[sel];
  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";

  const choose = (i) => {
    setSel(i);
    setRes(null);
    if (ENDPOINTS[i].body) setBody(ENDPOINTS[i].body);
  };

  const send = async () => {
    setBusy(true);
    try {
      const opts = ep.method === "POST"
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body }
        : undefined;
      setRes(await timed(ep.path, opts));
    } catch (e) {
      setRes({ status: 0, ok: false, ms: 0, data: String(e) });
    }
    setBusy(false);
  };

  const curl = ep.method === "POST"
    ? "curl -X POST " + origin + ep.path + " -H \"Content-Type: application/json\" -d '" + body + "'"
    : "curl " + origin + ep.path;
  const pretty = res ? (typeof res.data === "string" ? res.data : JSON.stringify(res.data, null, 2)) : "";

  return (
    <section className="card">
      <h3 className="card-title"><Icon name="terminal" size={14} /> API explorer</h3>
      <div className="api">
        <div className="api-list">
          {ENDPOINTS.map((e, i) => (
            <button key={e.path} className={"api-item " + (i === sel ? "on" : "")} onClick={() => choose(i)}>
              <span className={"method " + e.method}>{e.method}</span>
              <span className="mono path">{e.path}</span>
            </button>
          ))}
        </div>
        <div className="api-detail">
          <div className="api-desc">{ep.desc}</div>
          {ep.method === "POST" ? (
            <textarea className="mono" value={body} onChange={(e) => setBody(e.target.value)} rows={3} spellCheck="false" />
          ) : null}
          <div className="btn-row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={send} disabled={busy}><Icon name="play" size={14} /> {busy ? "Sending…" : "Send request"}</button>
            {res ? (
              <span className={"tag " + (res.ok ? "ok" : "bad")}>{res.status || "ERR"} · {res.ms} ms</span>
            ) : null}
          </div>
          <pre className="code curl">{curl}</pre>
          {res ? <pre className="code response">{pretty}</pre> : null}
        </div>
      </div>
    </section>
  );
}
