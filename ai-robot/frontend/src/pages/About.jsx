import Architecture from "../components/Architecture.jsx";
import Icon from "../components/Icon.jsx";

const PARTS = [
  { icon: "eye", title: "Computer vision", text: "MediaPipe Face Landmarker (478 points, 52 blendshapes) drives face detection and the expression rules. Hand Landmarker (21 points per hand) powers finger counting." },
  { icon: "fingerprint", title: "Face recognition", text: "SFace turns each aligned 112×112 face into a 128-dimensional embedding. Matching is cosine similarity against saved people (threshold 0.363). Only embeddings are stored, never photos." },
  { icon: "user", title: "Age estimation", text: "A CNN classifies a face crop into eight age ranges. It is shown as a range on purpose, because a single number would be false precision." },
  { icon: "mic", title: "Speech", text: "An adaptive noise-floor VAD cuts speech out of the mic stream, Google Web Speech transcribes it, and Windows SAPI speaks the reply. The mic is gated while the robot talks so it never hears itself." },
  { icon: "zap", title: "Language brain", text: "Intent rules answer local skills instantly (open apps, web search, photos, time). Everything else goes to an LLM with live camera context and recent turns. “What do you see” sends the current frame, so the request is multimodal." },
  { icon: "database", title: "Backend & data", text: "FastAPI with background worker threads for camera, mic, speech and identity. MJPEG video streaming, REST endpoints, and SQLite for people, conversation history and detection logs." },
  { icon: "cpu", title: "Frontend", text: "React 19 + Vite with no UI library: hand-written SVG charts, a CSS-variable theme system, a command palette, a hash router and an in-app API explorer." },
];

const STACK = ["Python", "FastAPI", "OpenCV", "MediaPipe", "ONNX / OpenCV DNN", "NumPy", "SQLite", "Gemini API", "React 19", "Vite", "SVG charts"];

const LIMITS = [
  "Expression detection is rule-based on facial-muscle scores, not a trained emotion classifier. It is fast and explainable, but coarse.",
  "Age is a coarse bucket and can be off by years. It is a demo, not a measurement.",
  "The free-tier LLM has rate limits and may use inputs to improve models, so camera frames are only sent when you explicitly ask “what do you see”.",
  "Face embeddings are biometric data. They stay on your machine and can be deleted with “forget …”.",
  "Speech-to-text needs an internet connection.",
];

export default function About() {
  return (
    <div className="page">
      <section className="card hero">
        <h1><span className="grad-text">AI Robot</span> — a voice and vision assistant, built end to end</h1>
        <p>
          Talk to it, show it things, and it answers out loud. Computer vision, speech, an LLM, a REST API, a database and
          this React dashboard all run on one laptop. Press <kbd>Ctrl</kbd> + <kbd>K</kbd> anywhere to run a command.
        </p>
        <div className="stack">
          {STACK.map((s) => <span key={s} className="tag">{s}</span>)}
        </div>
      </section>

      <section className="card">
        <h3 className="card-title"><Icon name="grid" size={14} /> Architecture</h3>
        <Architecture />
      </section>

      <div className="parts">
        {PARTS.map((p) => (
          <section className="card part" key={p.title}>
            <div className="kpi-icon"><Icon name={p.icon} size={18} /></div>
            <h4>{p.title}</h4>
            <p>{p.text}</p>
          </section>
        ))}
      </div>

      <div className="grid-2">
        <section className="card">
          <h3 className="card-title"><Icon name="info" size={14} /> Design decisions &amp; honest limits</h3>
          <ul className="limits">
            {LIMITS.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </section>
        <section className="card">
          <h3 className="card-title"><Icon name="terminal" size={14} /> Run it</h3>
          <pre className="code">{"# backend (port 8000)\npython server.py\n\n# frontend, development (port 5173)\ncd frontend\nnpm install\nnpm run dev\n\n# frontend, production build served by FastAPI\nnpm run build"}</pre>
        </section>
      </div>
    </div>
  );
}
