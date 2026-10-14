export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const EXPR = {
  Happy: { color: "#34d399", emoji: "😊" },
  Sad: { color: "#60a5fa", emoji: "😢" },
  Angry: { color: "#fb7185", emoji: "😠" },
  Surprised: { color: "#fbbf24", emoji: "😲" },
  Neutral: { color: "#94a3b8", emoji: "😐" },
};
export const exprInfo = (name) => EXPR[name] || { color: "#94a3b8", emoji: "·" };

export function fmtUptime(s) {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h) return h + "h " + m + "m";
  if (m) return m + "m " + sec + "s";
  return sec + "s";
}

export const EMPTY_STATUS = {
  faces: 0, fingers: 0, expression: "-", person: "-", mic: true, mic_error: "", llm: "",
  history: [], signals: {}, fps: 0, mic_level: 0, mic_threshold: 300, voice_state: "listening",
  voice_on: true, enroll: null,
};

export const EMPTY_SYSTEM = {
  uptime_s: 0, fps: 0, voice_on: true, mic: true, models: [], latencies: [],
  db: { commands: 0, detections: 0, people: 0, top_expression: "" },
};
