import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the React app runs on :5173 and forwards every API call to the
// Python backend on :8000, so the browser only ever talks to one origin.
const BACKEND = "http://127.0.0.1:8000";
const ROUTES = [
  "/status", "/video", "/command", "/speak", "/mic", "/voice", "/history", "/stats",
  "/people", "/detections", "/llm", "/faces", "/fingers", "/system", "/identify",
  "/photos", "/docs", "/openapi.json", "/classic",
];

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(ROUTES.map((r) => [r, { target: BACKEND, changeOrigin: true }])),
  },
  build: { outDir: "dist", emptyOutDir: true },
});
