import Icon from "../components/Icon.jsx";
import { AreaChart, BarChart, Donut } from "../components/charts.jsx";
import { usePoll } from "../api.js";
import { useRobot } from "../robot.js";
import { EMPTY_SYSTEM, exprInfo, fmtUptime } from "../utils.js";

function Kpi({ icon, label, value, sub }) {
  return (
    <div className="card kpi">
      <div className="kpi-icon"><Icon name={icon} size={18} /></div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {sub ? <div className="kpi-sub">{sub}</div> : null}
    </div>
  );
}

export default function Analytics() {
  const { status } = useRobot();
  const [system] = usePoll("/system", 3000, EMPTY_SYSTEM);
  const [summary] = usePoll("/detections/summary", 4000, { expressions: [], recent: [] });
  const [timeline] = usePoll("/detections/timeline?minutes=60", 6000, { points: [] });

  const lat = system.latencies || [];
  const avg = lat.length ? Math.round(lat.reduce((s, l) => s + l.ms, 0) / lat.length) : 0;
  const slowest = lat.length ? Math.max(...lat.map((l) => l.ms)) : 0;
  const totalExpr = summary.expressions.reduce((s, e) => s + e.count, 0);
  const pts = (timeline.points || []).map((p) => ({ x: p.t, y: p.count }));
  const donut = summary.expressions.map((e) => ({ name: e.name, value: e.count, color: exprInfo(e.name).color }));

  return (
    <div className="page">
      <div className="kpis">
        <Kpi icon="zap" label="Messages saved" value={system.db.commands} />
        <Kpi icon="eye" label="Detections logged" value={system.db.detections} />
        <Kpi icon="users" label="People known" value={system.db.people} />
        <Kpi icon="activity" label="Avg reply time" value={avg + " ms"} sub={"slowest " + slowest + " ms"} />
        <Kpi icon="cpu" label="Camera FPS" value={status.fps || 0} sub={"uptime " + fmtUptime(system.uptime_s)} />
      </div>

      <div className="grid-2">
        <section className="card">
          <h3 className="card-title"><Icon name="smile" size={14} /> Mood distribution</h3>
          <div className="donut-row">
            <Donut
              data={donut}
              center={
                <g>
                  <text x="84" y="82" textAnchor="middle" className="donut-num">{totalExpr}</text>
                  <text x="84" y="102" textAnchor="middle" className="donut-cap">detections</text>
                </g>
              }
            />
            <div className="legend">
              {summary.expressions.length === 0 ? <span className="muted small">Nothing logged yet.</span> : null}
              {summary.expressions.map((e) => (
                <div key={e.name} className="legend-row">
                  <span className="swatch-dot" style={{ background: exprInfo(e.name).color }} />
                  <span>{exprInfo(e.name).emoji} {e.name}</span>
                  <span className="mono">{totalExpr ? Math.round((e.count / totalExpr) * 100) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card">
          <h3 className="card-title"><Icon name="activity" size={14} /> Activity (last 60 min)</h3>
          <AreaChart
            points={pts}
            labels={pts.length ? [pts[0].x.slice(11), pts[pts.length - 1].x.slice(11)] : null}
          />
          <p className="note">One detection is saved every 5 seconds while a face or hand is in view.</p>
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3 className="card-title"><Icon name="zap" size={14} /> Command latency</h3>
          <BarChart items={lat.slice(-30).map((l) => ({ label: l.cmd, value: l.ms }))} />
          <p className="note">Each bar is one command. Local skills answer in milliseconds; LLM answers take longer.</p>
        </section>

        <section className="card">
          <h3 className="card-title"><Icon name="database" size={14} /> Recent detections</h3>
          <div className="table">
            {summary.recent.length === 0 ? <div className="muted small">Nothing logged yet.</div> : null}
            {summary.recent.map((r, i) => (
              <div className="trow" key={i}>
                <span className="mono">{r.ts.slice(11, 19)}</span>
                <span>{r.person || "unknown"}</span>
                <span style={{ color: exprInfo(r.expression).color }}>{exprInfo(r.expression).emoji} {r.expression}</span>
                <span className="muted">{r.fingers} fingers</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
