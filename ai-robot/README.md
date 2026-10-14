# AI Robot — voice + vision assistant

Talk to it, show it things, and it answers out loud.

- **Vision:** MediaPipe face + hand landmarks, expression rules, SFace face recognition, age CNN
- **Voice:** adaptive VAD, Google speech-to-text, Windows text-to-speech
- **Brain:** local skills (open apps, search, photos) + LLM fallback (Gemini free tier or Claude)
- **Backend:** FastAPI, MJPEG video stream, SQLite
- **Frontend:** React 19 + Vite (themes, charts, command palette, API explorer)

## Run
```
pip install -r requirements.txt
python server.py                 # backend on http://localhost:8000

cd frontend
npm install
npm run dev                      # UI on http://localhost:5173
```
Production: `npm run build` in `frontend`, then open http://localhost:8000.

Put your LLM key in `api_key.txt` (never commit it).
