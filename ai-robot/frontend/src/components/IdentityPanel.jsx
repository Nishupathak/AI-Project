import { useState } from "react";
import Icon from "./Icon.jsx";
import { EmbeddingStrip, Meter } from "./charts.jsx";
import { run, usePoll } from "../api.js";
import { useRobot } from "../robot.js";
import { useToast } from "../toasts.jsx";

const EMPTY_ID = { face: false, embedding: [], similarities: [], threshold: 0.363, best: "" };

export default function IdentityPanel() {
  const { status } = useRobot();
  const toast = useToast();
  const [idt] = usePoll("/identify", 800, EMPTY_ID);
  const [pp] = usePoll("/people", 4000, { people: [] });
  const [name, setName] = useState("");
  const enroll = status.enroll;

  const teach = async () => {
    const n = name.trim();
    if (!n) return;
    setName("");
    try {
      await run("remember me as " + n);
      toast("Look at the camera and turn your head slightly", "info");
    } catch {
      toast("Could not reach the robot", "bad");
    }
  };

  return (
    <section className="card">
      <div className="card-title-row">
        <h3 className="card-title"><Icon name="fingerprint" size={14} /> Face identity</h3>
        {idt.face ? (
          <span className={"tag " + (idt.best && idt.best !== "Unknown" ? "ok" : "")}>{idt.best || "Unknown"}</span>
        ) : (
          <span className="tag">no face</span>
        )}
      </div>

      <div className="sub">128-d SFace embedding (L2-normalised)</div>
      <EmbeddingStrip values={idt.embedding} />

      <div className="sub" style={{ marginTop: 14 }}>Cosine similarity to saved people</div>
      {idt.similarities.length === 0 ? (
        <div className="muted small">{pp.people.length ? "Show your face to compare." : "Nobody saved yet. Teach your face below."}</div>
      ) : null}
      {idt.similarities.map((s) => (
        <Meter
          key={s.name}
          label={s.name}
          value={Math.max(0, s.similarity)}
          max={1}
          mark={idt.threshold}
          right={s.similarity.toFixed(2)}
          tone={s.similarity >= idt.threshold ? "ok" : "bad"}
        />
      ))}
      <div className="muted small">Marker = match threshold ({idt.threshold}).</div>

      {enroll ? (
        <div style={{ marginTop: 12 }}>
          <Meter
            label={"Learning " + enroll.name + "… keep looking at the camera"}
            value={enroll.progress}
            max={enroll.total}
            right={enroll.progress + "/" + enroll.total}
          />
        </div>
      ) : null}

      <div className="chips" style={{ marginTop: 12 }}>
        {pp.people.length === 0 ? <span className="muted small">No saved people</span> : null}
        {pp.people.map((p) => (
          <span key={p} className="chip person">
            <Icon name="user" size={12} /> {p}
            <button className="x" title={"Forget " + p} onClick={() => run("forget " + p.toLowerCase())}>
              <Icon name="x" size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="inputrow">
        <input
          value={name}
          placeholder="Your name"
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") teach(); }}
        />
        <button className="btn" onClick={teach}>Teach my face</button>
      </div>
    </section>
  );
}
