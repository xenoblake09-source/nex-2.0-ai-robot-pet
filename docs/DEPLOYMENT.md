# Deployment guide (Render + alternatives)

The Android app is useless without a reachable backend, so deploy the FastAPI
service first and then point the app at it.

---

## 1. Render (recommended — free tier)

### 1.1 Push the code

```bash
cd nex
git init
git add .
git commit -m "NEX — AI robot pet"
git remote add origin https://github.com/<your-user>/nex.git
git push -u origin main
```

> `.gitignore` already excludes `.env`, `node_modules`, `local.properties`,
> build output and `*.apk`, so no secret can leak into the repository.

### 1.2 Create the service

1. Go to <https://render.com> → **New +** → **Web Service** → connect your repo.
2. Render detects `render.yaml` automatically. If not, fill in manually:
   - **Root directory:** `backend`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:**
     `uvicorn app.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 60`
   - **Health check path:** `/health`
3. **Environment variables** → add:
   | Key | Value |
   | --- | --- |
   | `GEMINI_API_KEY` | *(your key — set it in the dashboard, never in code)* |
   | `GEMINI_MODEL` | `gemini-3.6-flash` |
   | `GEMINI_FALLBACK_MODELS` | `gemini-3.5-flash-lite,gemini-3.8-flash` |
   | `CORS_ORIGINS` | `*` |
4. **Create Web Service** and wait for the deploy to go green.

You get a URL like:

```
https://nex-ai-robot-pet-api.onrender.com
```

### 1.3 Verify

```bash
curl https://nex-ai-robot-pet-api.onrender.com/health
```

```json
{ "status": "ok", "version": "1.0.0", "gemini_configured": true, "model": "gemini-3.6-flash", "uptime_seconds": 12.3 }
```

### 1.4 Point the app at it

Build with the URL baked in:

```bash
cd app
echo "VITE_NEX_API_BASE=https://nex-ai-robot-pet-api.onrender.com" > .env
npm run build && npx cap sync android
cd android && ./gradlew assembleDebug
```

…or set it on the device with the long-press setup panel (no rebuild needed).

---

## 2. Free-tier cold starts

Render's free tier sleeps after ~15 minutes of inactivity. The first request
after a sleep takes 30–60 seconds while the container boots.

* NEX shows a **thinking** face during that time — it is not frozen.
* For a smoother demo, open the app and say something a minute before you start
  the presentation, or use a paid Render instance.
* The health check hits `/health`, which does not call Gemini, so it stays fast.

---

## 3. Other hosts

The backend is a plain ASGI app — any of these work:

* **Railway** — `railway init`, `railway up`; start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; add `GEMINI_API_KEY`.
* **Fly.io** — `fly launch` with
  `uvicorn app.main:app --host 0.0.0.0 --port 8080`; `fly secrets set GEMINI_API_KEY=...`.
* **Google Cloud Run** — `gcloud run deploy --set-env-vars GEMINI_API_KEY=...`.
* **Your own laptop** — `uvicorn app.main:app --host 0.0.0.0 --port 8000`, then
  use the LAN IP or a tunnel (ngrok / cloudflared).

Python 3.11 or newer is required (3.11 recommended, matching `render.yaml`).

---

## 4. Security checklist

* ✅ The Gemini key lives **only** in the server environment.
* ✅ `GEMINI_API_KEY` is never sent to the app — `/api/config` exposes only
  public values.
* ✅ `.env` is git-ignored; `.env.example` documents every variable.
* ✅ Logs never print the key — the SDK wrapper masks it.
* ✅ The app talks to the backend over HTTPS (cleartext is limited to local
  development hosts in `network_security_config.xml`).
* ⚠️ `/api/chat` is unauthenticated. For a public deployment, add a simple
  shared-token header or rate limiting (the free tier will throttle abuse
  anyway).

---

## 5. Environment variables reference

| Variable | Default | Meaning |
| --- | --- | --- |
| `GEMINI_API_KEY` | *(empty)* | **Required.** Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Primary chat model |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.5-flash-lite,gemini-3.8-flash` | Tried in order if the primary fails |
| `GEMINI_TIMEOUT` | `45` | Seconds before a Gemini call is aborted |
| `GEMINI_TEMPERATURE` | `0.9` | Personality/creativity |
| `GEMINI_MAX_OUTPUT_TOKENS` | `512` | Reply length cap |
| `CORS_ORIGINS` | `*` | Comma separated allowed origins |
| `SCHOOL_URL` | `https://montfortbagaha.org/` | School knowledge source |
| `SCHOOL_CACHE_TTL` | `3600` | Seconds the crawled school page is cached |
| `WEATHER_ENABLED` | `1` | Set to `0` to disable weather lookups |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `HISTORY_TURNS` | `8` | Conversation turns kept in context |
