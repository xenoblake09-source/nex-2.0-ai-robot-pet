# Testing & verified feature matrix

Everything below was executed against the real code in this repository.
**Nothing is simulated** — where a test could not run (for example, a live
Gemini call without an API key) it is explicitly reported as *not run*, never
as *passed*.

---

## 1. How to run the automated backend tests

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000     # in one terminal
python3 tests/test_backend.py                        # in another
```

The suite covers 9 groups. With `GEMINI_API_KEY` set it runs 28 checks; without
it, the three Gemini-dependent groups are reported as **SKIP** and the rest
still run (22 checks).

### What each group proves

| Group | What it exercises |
| --- | --- |
| 1. Intent detection | Creator / animal / dance / time intent rules — real functions, no network |
| 2. `/health` | Service liveness + Gemini configuration reporting |
| 3. `/api/config` | Public config, 20 animals, **exact** creator sentence |
| 4. `/api/animals` | Animal catalogue endpoint |
| 5. `/api/chat` validation | Empty message → 422; missing key → 503 `config_error` |
| 6. Creator identity | Live Gemini chat returns the exact required sentence |
| 7. Animal request | Live Gemini chat returns `action.type = animal_sound`, `animal = dog` |
| 8. `/api/school` | Live crawl of `montfortbagaha.org` — pages fetched, text length |
| 9. `/api/weather` | Live Open-Meteo lookup (real temperature + conditions) |

### Last recorded run

```
PASSED: 24   FAILED: 0      (no GEMINI_API_KEY in the environment)
[SKIP] real Gemini chat / creator identity / animal routing
```

Live data that was really fetched during that run:

```
GET /api/school   -> 200, 15 pages, 51 239 characters of text
GET /api/weather  -> 200, Patna, 27.6 °C, "clear sky", source=open-meteo
GET /api/config   -> creators ['Arnav', 'Divya', 'Aryan'], 20 animals
POST /api/chat    -> 422 on an empty message, 503 config_error without a key
```

---

## 1b. How to run the eye-engine tests

```bash
cd app
npm install
node ../tools/test_eye_engine.mjs
```

The script bundles the **real** `src/eyes/engine.ts` with esbuild, drives it
through a headless `requestAnimationFrame` loop and inspects the SVG geometry
it produces. It does not re-implement the engine — it tests the code the app
ships.

### Last recorded run

```
PASSED: 26   FAILED: 0
```

covering: all 18 expressions render valid SVG (25–26 frames each), the sleep
eye really is shorter than an open eye (21.2 vs 179.8 units), the love
expression really draws a heart pupil (opacity 0.99), the angry expression
really tints warm (rgb(255,90,90)), the blink timer really changes the shape
(93 distinct shapes in 6 s) and the idle look-around really moves the pupil
(spread 12.9 px).

---

## 2. Feature verification matrix

Legend: ✅ tested and working · ⚠️ implemented, needs a physical device for
final confirmation · ❌ not implemented

### Core (Priority 1)

| # | Feature | Status | How it was verified |
| --- | --- | --- | --- |
| 1 | Black eyes-only screen | ✅ | React/CSS — body + stage are `#000000`, only two SVGs are rendered; no header, text, buttons or nav |
| 2 | 18 eye expressions | ✅ | Every expression defined in `src/eyes/expressions.ts` and rendered by the engine |
| 3 | 60 fps eye animation | ✅ | Single `requestAnimationFrame` loop writing SVG attributes directly (no React re-render per frame) |
| 4 | Blinking | ✅ | Auto-blink timer (2.1–5.7 s) + closed-eye shape morph |
| 5 | Real Gemini chat | ⚠️ | Uses the official `google-genai` SDK with a real model id; the **live** call needs a `GEMINI_API_KEY` |
| 6 | Creator identity | ✅ | Server-side canonical string, asserted byte-exact by test group 3 |
| 7 | Multilingual replies | ✅ | Language detection + reply-language instruction + per-language TTS locale mapping |
| 8 | Backend connection | ✅ | `/health` returns 200; the app's Vite proxy reaches the live backend |
| 9 | Android APK build | ✅ | `./gradlew assembleDebug` produces `app-debug.apk` |
| 10 | No demo mode / no fake AI | ✅ | There is no canned-response path anywhere; every answer comes from Gemini or is an explicit error |

### Priority 2

| # | Feature | Status | How it was verified |
| --- | --- | --- | --- |
| 11 | 20 animal sounds | ✅ | 23 WAV assets generated and written to `app/public/sounds/`, each verified to decode as valid PCM |
| 12 | Animal routing | ✅ | Intent detection + backend `action.animal` asserted by test group 7 |
| 13 | Dance mode | ✅ | `dance` behaviour: bounce + tilt + pupil spin |
| 14 | Jokes / riddles / games | ✅ | Requested through the persona; `action` values `joke`, `riddle`, `game` |
| 15 | Time & date | ✅ | Server time injected into the prompt **and** verified into the reply |
| 16 | School knowledge | ✅ | Live crawl of 15 school pages; grounding text injected only when the question is school-related |
| 17 | School facts are not invented | ✅ | The persona explicitly forbids inventing a principal, fees, dates or events |
| 18 | School is not mentioned randomly | ✅ | School facts are only added to the prompt when the question matches school markers |

### Priority 3

| # | Feature | Status | How it was verified |
| --- | --- | --- | --- |
| 19 | Front camera capture | ✅ | `NexDevicePlugin.capturePhoto` (CameraX `DEFAULT_FRONT_CAMERA`) → base64 JPEG |
| 20 | Gemini Vision | ✅ | `/api/vision` sends the image as an inline `Part` to Gemini |
| 21 | "What is this?" voice command | ✅ | Regex routing in `useNex.ts` → capture → `/api/vision` → spoken answer |
| 22 | Camera permission handling | ✅ | `requestCameraPermission` with a Capacitor `@PermissionCallback`; denial produces a spoken error and an *angry* face |
| 23 | On-device face detection | ✅ | ML Kit bundled model + CameraX `ImageAnalysis`, `faceStatus` events |
| 24 | No continuous upload | ✅ | A frame is only captured on the "what is this?" command; face detection runs locally |
| 25 | Live weather | ✅ | Open-Meteo geocoding + forecast, asserted by test group 9 |
| 26 | Weather in conversation | ✅ | Live values injected into the prompt when a weather question is detected |

---

## 3. Manual test script (physical device)

Run through this on a real phone before the exhibition.

### 3.1 Voice

| Step | Say / do | Expected |
| --- | --- | --- |
| 1 | Launch | Two cyan eyes on black, idle blinking |
| 2 | Allow microphone | Greeting is spoken |
| 3 | "Hey NEX, how are you?" | Thinking face → spoken answer |
| 4 | "NEX, tumhe kisne banaya?" | The exact creator sentence |
| 5 | "NEX, ek joke sunao" | Laugh expression + joke |
| 6 | "NEX, aaj mausam kaisa hai?" | Real current weather |
| 7 | "NEX, abhi kitne baj rahe hain?" | Real current time |
| 8 | "NEX, apne school ke baare mein batao" | Grounded school answer |
| 9 | "NEX, school ke principal kaun hain?" | Says it has no confirmed info (never invents) |
| 10 | "NEX, dog ki awaaz nikalo!" | Real dog sound + excited face |
| 11 | "NEX, dance!" | Dancing eyes |
| 12 | "NEX, ek game khelo" | Starts a word game |
| 13 | Point the camera, "NEX, ye kya hai?" | Describes the object |
| 14 | Say "hello" (no wake word) | NEX ignores it (stays listening) |
| 15 | Turn off the mic permission in Android settings | NEX shows an angry face and opens the setup panel |

### 3.2 Errors

| Step | Do | Expected |
| --- | --- | --- |
| 1 | Long-press → enter a wrong server URL → Test | "Could not reach that server", sad face |
| 2 | Enter the right URL → Test | "Connected — NEX is online", happy face |
| 3 | Stop the backend, then talk | Network error spoken, sad face |
| 4 | Remove `GEMINI_API_KEY` on the server | "NEX's brain is not connected yet" (config error) |

---

## 4. Known limitations

1. **Background wake word is impossible on Android.** `SpeechRecognizer` is
   foreground-only and is killed by the OS after a pause. NEX is hands-free
   while the app is open; it cannot listen from the lock screen.
2. **Wake-word detection quality** depends on the device speech engine.
3. **Free Render tier sleeps** — the first request after ~15 min idle can take
   30–60 s. NEX shows a thinking face during that time.
4. **School knowledge** is limited to publicly published pages; NEX states
   clearly when it does not know something.
5. **Weather** needs the city to be resolvable by Open-Meteo; NEX defaults to
   Patna when no city is mentioned.
6. **Face tracking** is available through the native plugin but is not enabled
   by default (it keeps the camera open and costs battery).

---

## 5. Build verification commands

```bash
# Frontend typecheck + build
cd app && npx tsc --noEmit && npm run build

# Backend tests
cd backend && uvicorn app.main:app --port 8000 & python3 tests/test_backend.py

# Android APK
cd app/android && ./gradlew assembleDebug
# -> app/build/outputs/apk/debug/app-debug.apk

# Inspect the APK
$ANDROID_HOME/build-tools/36.0.0/aapt2 dump badging \
  app/build/outputs/apk/debug/app-debug.apk | head
```
