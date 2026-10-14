import { useEffect, useState } from "react";

// Small fetch helpers. Everything goes through the Vite proxy (dev) or the same origin (production).
export async function request(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok && data === null) throw new Error("HTTP " + res.status);
  return data;
}

export const api = {
  get: (url) => request(url),
  post: (url, body) =>
    request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};

// Like request(), but also reports status code and round-trip time (used by the API explorer).
export async function timed(url, options) {
  const t0 = performance.now();
  const res = await fetch(url, options);
  const text = await res.text();
  const ms = Math.round(performance.now() - t0);
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }
  return { status: res.status, ok: res.ok, ms, data };
}

// Re-fetches `url` every `ms` milliseconds. Returns [data, serverOnline].
export function usePoll(url, ms, initial) {
  const [data, setData] = useState(initial);
  const [online, setOnline] = useState(true);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const d = await api.get(url);
        if (alive && d !== null) {
          setData(d);
          setOnline(true);
        }
      } catch {
        if (alive) setOnline(false);
      }
    };
    tick();
    const id = setInterval(tick, ms);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [url, ms]);
  return [data, online];
}

// Send a text command to the robot (same as saying it out loud).
export const run = (text) => api.post("/command", { text });
