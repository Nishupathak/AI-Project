// System architecture drawn as inline SVG so it follows the active theme and accent colour.
function Box({ x, y, w, h, title, sub, accent }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="12" className={"arch-box " + (accent ? "accent" : "")} />
      <text x={x + w / 2} y={y + h / 2 - (sub ? 5 : -5)} textAnchor="middle" className="arch-title">{title}</text>
      {sub ? <text x={x + w / 2} y={y + h / 2 + 13} textAnchor="middle" className="arch-sub">{sub}</text> : null}
    </g>
  );
}

function Arrow({ d, dashed }) {
  return <path d={d} className={"arch-arrow " + (dashed ? "dashed" : "")} markerEnd="url(#arrowhead)" />;
}

export default function Architecture() {
  return (
    <svg viewBox="0 0 1000 350" className="arch" role="img" aria-label="System architecture diagram">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="var(--muted)" />
        </marker>
      </defs>

      <Box x={10} y={30} w={130} h={56} title="Webcam" sub="frames" />
      <Box x={10} y={150} w={130} h={56} title="Microphone" sub="audio stream" />

      <Box x={190} y={14} w={215} h={90} title="Vision pipeline" sub="MediaPipe · SFace · Age CNN" accent />
      <Box x={190} y={134} w={215} h={86} title="Speech pipeline" sub="adaptive VAD → Google STT" accent />

      <Box x={455} y={50} w={170} h={110} title="Command router" sub="intent rules" accent />
      <Box x={455} y={196} w={170} h={52} title="Local skills" sub="apps · search · photos" />
      <Box x={455} y={270} w={170} h={52} title="LLM fallback" sub="Gemini / Claude" />

      <Box x={675} y={30} w={150} h={100} title="FastAPI" sub="REST + MJPEG + threads" accent />
      <Box x={675} y={160} w={150} h={52} title="SQLite" sub="people · history · logs" />
      <Box x={675} y={240} w={150} h={52} title="Text-to-speech" sub="Windows SAPI" />

      <Box x={870} y={50} w={120} h={100} title="React + Vite" sub="this dashboard" accent />

      <Arrow d="M140,58 L190,58" />
      <Arrow d="M140,178 L190,178" />
      <Arrow d="M405,70 L455,90" />
      <Arrow d="M405,176 L455,130" />
      <Arrow d="M540,160 L540,196" />
      <Arrow d="M540,248 L540,270" dashed />
      <Arrow d="M625,90 L675,80" />
      <Arrow d="M750,130 L750,160" />
      <Arrow d="M625,150 C660,150 640,266 675,266" />
      <Arrow d="M825,100 L870,100" />
    </svg>
  );
}
