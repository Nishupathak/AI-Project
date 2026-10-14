import Icon from "./Icon.jsx";
import { Meter } from "./charts.jsx";
import { useRobot } from "../robot.js";
import { exprInfo } from "../utils.js";

// The expression label comes from these facial-muscle scores (MediaPipe blendshapes) and simple rules.
const SIGNALS = [
  { key: "smile", label: "Smile", mark: 0.4 },
  { key: "jawOpen", label: "Jaw open", mark: 0.4 },
  { key: "browRaise", label: "Brow raise", mark: 0.3 },
  { key: "eyesWide", label: "Eyes wide", mark: 0.3 },
  { key: "browDown", label: "Brow down", mark: 0.45 },
  { key: "frown", label: "Frown", mark: 0.25 },
  { key: "blink", label: "Blink" },
];

export default function SignalsPanel() {
  const { status } = useRobot();
  const sig = status.signals || {};
  const ex = exprInfo(status.expression);
  const live = status.faces > 0;

  return (
    <section className="card">
      <div className="card-title-row">
        <h3 className="card-title"><Icon name="smile" size={14} /> Emotion signals</h3>
        <span className="tag" style={{ color: ex.color, borderColor: ex.color }}>{ex.emoji} {status.expression}</span>
      </div>
      {SIGNALS.map((s) => (
        <Meter
          key={s.key}
          label={s.label}
          value={live ? sig[s.key] || 0 : 0}
          max={1}
          mark={s.mark}
          right={(live ? sig[s.key] || 0 : 0).toFixed(2)}
          tone={live && s.mark != null && (sig[s.key] || 0) >= s.mark ? "ok" : "accent"}
        />
      ))}
      <p className="note">
        Rule-based: <b>Surprised</b> = jaw &gt; 0.4 with raised brows or wide eyes · <b>Happy</b> = smile &gt; 0.4 ·
        <b> Angry</b> = brow down &gt; 0.45 · <b>Sad</b> = frown &gt; 0.25. Marker = threshold.
      </p>
    </section>
  );
}
