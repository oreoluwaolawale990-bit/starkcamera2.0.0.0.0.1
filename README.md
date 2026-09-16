# STARK OS — Vision Interface

A browser-based, Iron-Man-style HUD that watches your webcam, tracks your hands
and face entirely on-device (MediaPipe, runs in-browser — nothing is uploaded
except a single frame when you trigger a scan), and asks Google Gemini to
describe what it sees.

## Features

- Live hand + face tracking overlay, running client-side via WebAssembly
- Make a **fist** to send one frame to Gemini for a vision scan
- Hold a **palm** for ~0.6s (or press PAUSE) to pause detection
- Voice input via your browser's speech recognition (Chrome/Edge)
- Spoken responses, with a mute toggle
- Visible on-screen error reporting — if the camera or AI models fail to
  load, you see exactly why instead of a dead screen
- `/health` endpoint so Render can monitor the service
- Works without a Gemini key too — both AI endpoints fall back to a clearly
  labeled mock response so the UI is testable immediately

## Deploy to Render (free tier)

1. Push this folder to a new GitHub repo. Include `main.py`, `index.html`,
   `requirements.txt`, and `render.yaml` — don't push a real `.env` file.
2. Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).
3. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** →
   **Blueprint**, and connect your repo. Render reads `render.yaml` and
   configures the build/start commands automatically.
4. When prompted, paste your key into the `GEMINI_API_KEY` environment
   variable (Render keeps this out of your repo).
5. Deploy. First build takes 1–3 minutes — watch the Logs tab for
   "Application startup complete."
6. Open the URL Render gives you (something like
   `https://stark-ai-gemini.onrender.com`).

Render's free plan spins the app down after ~15 minutes idle; the next visit
takes 30–60 seconds to wake back up. That's expected, not a bug.

## Local development

```
cp .env.example .env   # then fill in your real GEMINI_API_KEY
uvicorn main:app --reload
```

Open http://localhost:8000 — camera access works over plain `localhost`
without HTTPS.

## How it works

- The browser downloads MediaPipe's hand and face landmark models once, then
  tracks both entirely client-side via WebAssembly — no per-frame server cost.
- A fist gesture captures one JPEG frame and POSTs it to `/api/analyze`,
  which calls `gemini-flash-latest` (Google's alias for their current
  recommended Flash model) with your frame and a JARVIS-style prompt.
- Text chat goes to `/api/jarvis`, which includes the last scan's description
  as context so you can ask follow-up questions about what Gemini saw.
- If `GEMINI_API_KEY` isn't set, both endpoints return a clearly labeled mock
  response instead of failing outright.

## Notes

- `GEMINI_MODEL` env var lets you pin a specific model (e.g.
  `gemini-2.5-flash`) instead of tracking Google's `-latest` alias, if you
  want fixed behavior over automatic updates.
- CORS is wide open (`allow_origins=["*"]`) since the frontend and backend
  are served from the same origin here; tighten it if you split them apart.
