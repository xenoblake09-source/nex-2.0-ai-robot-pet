# NEX — the AI robot pet

**NEX** is an expressive AI robot pet for Android. The screen is pure black with
two big glowing eyes. You talk to it, it listens, thinks and answers out loud —
with real Google Gemini behind it, real animal sounds, and a personality.

Built by **Arnav, Divya and Aryan**.

```
┌───────────────┐        HTTPS         ┌────────────────────┐
│  Android app  │  ──────────────────►  │  FastAPI backend   │
│  (Capacitor)  │  ◄──────────────────  │  (Render deploy)   │
│               │   reply + expression  │                    │
│  · eyes only  │                      │  · Google Gemini   │
│  · mic + TTS  │                      │  · Gemini Vision   │
│  · 20 animals │                      │  · school + weather│
└───────────────┘                      └────────────────────┘
```

---

## 1. What NEX can do

| Feature | Status |
| --- | --- |
| Eyes-only black interface, 18 expressions | ✅ implemented · engine tested (26/26) |
| Real Google Gemini chat (no demo mode) | ✅ implemented · **live call not run — API key not configured** |
| Hindi / Hinglish / English + other languages | ✅ implemented |
| Exact creator identity (Arnav, Divya, Aryan) | ✅ enforced server-side, asserted byte-exact by tests |
| 20 animal voices (dog → bee) | ✅ 23 WAV assets generated & verified |
| Dance mode, jokes, riddles, games, facts | ✅ implemented |
| Live time & date | ✅ implemented |
| Live weather (Open-Meteo) | ✅ tested live |
| Montfort Bagaha school knowledge (grounded) | ✅ tested live (15 pages crawled) |
| Front camera + Gemini Vision ("what is this?") | ✅ implemented · needs a physical phone to confirm |
| On-device face detection (ML Kit) | ✅ implemented · needs a physical phone to confirm |
| Hands-free listening with "Hey NEX" wake word | ✅ implemented (foreground — see limitations) |
| Text-to-speech with exact completion events | ✅ implemented · needs a physical phone to confirm |

> Honest note: the automated suites (backend + eye engine) pass, and the APKs
> build and are verified. Anything that needs real hardware or a real Gemini
> key is marked as such instead of being claimed as working.

---

## 2. Repository layout

```
nex/
├── app/                     # Android app (React + TypeScript + Capacitor)
│   ├── src/
│   │   ├── eyes/            # eye engine + 18 expression definitions
│   │   ├── hooks/useNex.ts  # the conversation orchestrator
│   │   ├── lib/             # api, speech, sounds, native bridge, config
│   │   └── components/      # hidden setup panel
│   ├── public/sounds/       # 23 generated audio assets
│   ├── android/             # native Android project (+ NexDevicePlugin.kt)
│   └── capacitor.config.ts
├── backend/                 # FastAPI + Google Gemini
│   ├── app/
│   │   ├── main.py          # HTTP API
│   │   ├── chat_service.py  # persona, intents, live facts
│   │   ├── gemini_client.py # Google Gen AI SDK wrapper
│   │   ├── school.py        # montfortbagaha.org crawler
│   │   ├── vision_service.py# Gemini Vision
│   │   └── weather.py       # Open-Meteo
│   ├── tests/test_backend.py
│   └── render.yaml
├── tools/
│   ├── setup_android.sh     # (re)creates + customises the native project
│   ├── android-overlay/     # the hand-written native files
│   ├── generate_animal_sounds.py   # synthesises all animal voices
│   ├── generate_icon.py            # draws the launcher icon
│   ├── create_keystore.sh          # demo release signing key
│   ├── test_eye_engine.mjs         # headless tests for the eye engine
│   ├── render_face.mjs             # renders the face from the real engine
│   └── package_source.sh           # builds the release ZIP
├── apk/                     # built APKs (debug + release)
└── docs/                    # installation, deployment, testing, exhibition guide
```

---

## 3. Quick start

### 3.1 Backend (2 minutes)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# put your Gemini key in .env:
#   GEMINI_API_KEY=your-key-here

uvicorn app.main:app --reload --port 8000
```

Check it:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok", ..., "gemini_configured": true}
```

Get a free Gemini key: <https://aistudio.google.com/apikey>

The key lives **only** in `backend/.env` (git-ignored) or in the Render
dashboard. It is never compiled into the APK and never appears in the frontend.

### 3.2 Android app

```bash
cd app
npm install
npm run build          # web build -> app/dist
npx cap sync android   # copy the build into the native project
cd android && ./gradlew assembleDebug
# -> app/android/app/build/outputs/apk/debug/app-debug.apk
```

Or, from a clean checkout, one command that also restores the hand-written
native plugin, the icons and the demo keystore:

```bash
bash tools/setup_android.sh
```

Install on a phone (USB debugging on):

```bash
adb install -r app/android/app/build/outputs/apk/debug/app-debug.apk
```

Full details — including pointing the app at your server — are in
[docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## 4. How the app finds the server

The APK talks to **your** deployed backend. Two ways to set it:

1. **At build time** — create `app/.env`:
   ```
   VITE_NEX_API_BASE=https://nex-ai-robot-pet-api.onrender.com
   ```
   then `npm run build && npx cap sync android`.

2. **At runtime** — long-press the eyes for ~1 second to open the hidden setup
   panel, type the server address and press **Test & save**. The value is stored
   on the device, so you can rebuild the APK without touching the server URL.

> The main face screen never shows text or buttons — the setup panel is the only
> way in, keeping the "eyes only" promise intact.

---

## 5. API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | liveness + Gemini configuration status |
| `GET` | `/api/config` | public app configuration (no secrets) |
| `GET` | `/api/animals` | list of animal voices |
| `POST` | `/api/chat` | main conversation endpoint |
| `POST` | `/api/vision` | Gemini Vision description of a base64 image |
| `GET` | `/api/school` | status of the crawled school knowledge |
| `POST` | `/api/school/ask` | grounded school question |
| `GET` | `/api/weather?city=` | live weather |

`POST /api/chat` request:

```json
{
  "message": "NEX, ek joke sunao!",
  "language": "auto",
  "history": [{ "role": "user", "content": "hi" }],
  "user_name": null,
  "session_id": "nex-session"
}
```

Response:

```json
{
  "reply": "Ek robot ke paas dil nahi hota, lekin uska processor garam ho jaata hai!",
  "expression": "laugh",
  "action": { "type": "none", "animal": null },
  "language": "hinglish",
  "source": "gemini",
  "model": "gemini-3.6-flash",
  "latency_ms": 820,
  "school_used": false,
  "creator_intro": false
}
```

Errors always use the same shape, and the `code` tells the app what to show:

```json
{ "error": { "code": "gemini_timeout", "message": "...", "detail": "..." } }
```

`config_error` · `gemini_error` · `gemini_timeout` · `gemini_blocked` ·
`upstream_error` · `validation_error` · `network_error` (client side)

---

## 6. The NEX personality

* Cute, curious, playful, slightly mischievous.
* Replies in **the language you used** — Hindi, Hinglish, English and beyond.
* Always 1–3 short sentences, because the answer is spoken out loud.
* Never repeats itself (recent replies are fed back to the model).
* Mentions the school **only** when you ask about it, and never invents
  principal names, fees, dates or events.

### Creator identity

The server guarantees the exact required sentence:

> **Mujhe Arnav, Divya aur Aryan ne banaya hai! Main hoon NEX — tumhara smart aur masti karne wala AI robot pet!**

---

## 7. Animal voices

All 20 voices are **synthesised from scratch** by
`tools/generate_animal_sounds.py` (numpy) — original audio, no third-party
recordings, no licensing issues, ~1.9 MB for the whole set.

`dog · cat · cow · lion · tiger · monkey · elephant · duck · chicken · horse ·
sheep · goat · wolf · frog · bird · pig · donkey · rooster · owl · bee`

Regenerate them with:

```bash
python3 tools/generate_animal_sounds.py
```

If a file is ever missing, the player falls back to a short synthesised chirp
and says so — NEX never pretends to play a sound that is not there.

---

## 8. Deployment (Render)

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). In short: push to GitHub, create a
Web Service from `backend/render.yaml`, add `GEMINI_API_KEY` as a secret
environment variable, and copy the resulting URL into the app.

---

## 9. Testing

```bash
# backend (needs the server running)
cd backend && python3 tests/test_backend.py
# -> PASSED: 24   FAILED: 0   (Gemini groups SKIP without a key)

# eye engine (headless, uses the real engine)
cd app && node ../tools/test_eye_engine.mjs
# -> PASSED: 26   FAILED: 0
```

The backend suite hits the real backend: health, config, animals, validation,
live school retrieval, live weather, and — when `GEMINI_API_KEY` is set — real
Gemini chat, the exact creator sentence and animal-sound routing. Tests are
skipped, never faked, when the key is missing.

See [docs/TESTING.md](docs/TESTING.md) for the full tested/incomplete matrix.

---

## 10. Built APKs

| File | Size | Notes |
| --- | --- | --- |
| `apk/nex-2.0-debug.apk` | ~44 MB | debuggable build, `adb install` friendly |
| `apk/nex-2.0-release.apk` | ~40 MB | R8-minified, signed with the demo key |

Both are `ai.nexcompanion.virtualpet`, minSdk 24, targetSdk 36, and bundle all
23 sound assets. Rebuild them with:

```bash
cd app/android && ./gradlew assembleDebug     # debug
cd app/android && ./gradlew assembleRelease   # release (demo keystore)
```

The demo signing key lives in `app/android/nex-release.keystore`
(alias `nex`, password `nexdemo123`) so anyone can rebuild an identical APK.
Generate your own key before publishing anything real.

---

## 11. Known limitations (honest list)

1. **Background wake word.** Android's `SpeechRecognizer` only works while the
   app is in the foreground and is killed by the system after a pause. NEX
   therefore stays hands-free *while the app is open*; it cannot listen from the
   lock screen. This is an OS limitation, not a missing feature.
2. **Network required.** Gemini, weather and school knowledge all need
   internet. Offline, NEX still animates and plays sounds but cannot answer.
3. **Free-tier cold start.** A Render free instance sleeps; the first request
   after a long pause can take up to ~50 s. The app shows a thinking face while
   it waits.
4. **Wake word recognition** depends on the device's speech engine. Phrase it
   clearly ("Hey NEX") and speak a little louder than the room.
5. The **school knowledge** is limited to what montfortbagaha.org actually
   publishes; NEX says so when a fact is missing instead of guessing.
6. **Live Gemini calls are unverified** until `GEMINI_API_KEY` is configured.
   The code path, error handling and prompt are implemented and unit-tested,
   but no real model response has been observed yet.
7. **Face tracking is off by default** — it keeps the camera open and costs
   battery, so it is opt-in from the native plugin.

---

## 12. Credits

Created by **Arnav, Divya and Aryan**.
Built with Capacitor, React, TypeScript, FastAPI, the official Google Gen AI
SDK, CameraX and ML Kit.
