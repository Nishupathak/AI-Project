import { clamp } from "../utils.js";

// All charts are plain SVG/CSS: no chart library, fully theme-aware through CSS variables.

export function Donut({ data, size = 168, thickness = 20, center }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const mid = size / 2;
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={"0 0 " + size + " " + size} className="donut">
      <circle cx={mid} cy={mid} r={r} fill="none" stroke="var(--track)" strokeWidth={thickness} />
      {total > 0
        ? data.map((d) => {
            const len = (d.value / total) * c;
            const el = (
              <circle
                key={d.name}
                cx={mid}
                cy={mid}
                r={r}
                fill="none"
                stroke={d.color}
                strokeWidth={thickness}
                strokeDasharray={len + " " + (c - len)}
                strokeDashoffset={-offset}
                transform={"rotate(-90 " + mid + " " + mid + ")"}
              />
            );
            offset += len;
            return el;
          })
        : null}
      {center}
    </svg>
  );
}

export function AreaChart({ points, height = 150, labels }) {
  if (!points.length) return <div className="empty-chart" style={{ height }}>No data yet. Stand in front of the camera.</div>;
  const w = 600;
  const max = Math.max(1, ...points.map((p) => p.y));
  const coords = points.map((p, i) => [
    points.length > 1 ? (i * w) / (points.length - 1) : w / 2,
    height - 16 - (p.y / max) * (height - 32),
  ]);
  const line = coords.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1)).join(" ");
  const last = coords[coords.length - 1];
  const area = line + " L" + last[0] + "," + (height - 16) + " L" + coords[0][0] + "," + (height - 16) + " Z";
  return (
    <div>
      <svg viewBox={"0 0 " + w + " " + height} preserveAspectRatio="none" className="area" style={{ height }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.45" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#areaGrad)" />
        <path d={line} fill="none" stroke="var(--accent)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
      </svg>
      {labels ? (
        <div className="axis">
          <span>{labels[0]}</span>
          <span>peak {max}</span>
          <span>{labels[1]}</span>
        </div>
      ) : null}
    </div>
  );
}

export function BarChart({ items, height = 130, unit = "ms" }) {
  if (!items.length) return <div className="empty-chart" style={{ height }}>No commands yet. Try saying something.</div>;
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="bars" style={{ height }}>
      {items.map((it, i) => (
        <div className="bar-col" key={i} title={it.label + ": " + it.value + unit}>
          <div className="bar-fill" style={{ height: Math.max(4, (it.value / max) * 100) + "%" }} />
        </div>
      ))}
    </div>
  );
}

// Horizontal meter with an optional threshold marker.
export function Meter({ label, value, max = 1, mark, tone = "accent", right }) {
  const pct = clamp(value / max, 0, 1) * 100;
  const markPct = mark != null ? clamp(mark / max, 0, 1) * 100 : null;
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <span className="mono">{right != null ? right : value}</span>
      </div>
      <div className="meter-track">
        <div className={"meter-fill " + tone} style={{ width: pct + "%" }} />
        {markPct != null ? <div className="meter-mark" style={{ left: markPct + "%" }} /> : null}
      </div>
    </div>
  );
}

// A 128-number face embedding drawn as a colour barcode (positive = accent, negative = accent 2).
export function EmbeddingStrip({ values }) {
  if (!values || !values.length) return <div className="empty-chart" style={{ height: 56 }}>No face in view</div>;
  return (
    <div className="embed">
      {values.map((v, i) => (
        <span
          key={i}
          title={"dim " + i + ": " + v}
          style={{
            background: v >= 0 ? "var(--accent)" : "var(--accent2)",
            opacity: 0.12 + 0.88 * Math.min(1, Math.abs(v) / 0.22),
          }}
        />
      ))}
    </div>
  );
}
