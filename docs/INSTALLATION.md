# Installation guide

Two parts: the **backend** (the brain) and the **Android app** (the face).

---

## Part 1 — Backend

### 1.1 Get a Gemini API key

1. Open <https://aistudio.google.com/apikey>
2. Sign in with a Google account.
3. **Create API key** → copy it. (Google AI Studio is free; no billing card is
   needed for the free tier.)

### 1.2 Run it locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and paste your key:

```
GEMINI_API_KEY=AIzaSy...your-key...
GEMINI_MODEL=gemini-3.6-flash
```

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://127.0.0.1:8000/health
```

You want to see `"gemini_configured": true`.

### 1.3 Try a real conversation

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Tumhe kisne banaya?","session_id":"demo"}'
```

---

## Part 2 — Android app

### 2.0 Fastest path — install the pre-built APK

You do **not** have to build anything if you just want to try NEX:

```bash
adb install -r apk/nex-2.0-debug.apk
```

or copy `apk/nex-2.0-debug.apk` (or `apk/nex-2.0-release.apk`) onto the phone
and open it — allow *install from unknown sources* when asked.

Both APKs are `ai.nexcompanion.virtualpet`, work on Android 7.0 (API 24) and
newer, and bundle every sound asset. You still need the **backend** running
(Part 1) or a deployed one, and you point the app at it in step 2.4.

### 2.1 Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Node.js | 20+ (22 recommended) | `node -v` |
| JDK | 17 or 21 | Capacitor 8 works with both |
| Android SDK | platform 36 + build-tools 36 | Android Studio installs these |

### 2.2 Build the APK

```bash
cd app
npm install
npm run build
npx cap sync android
cd android
./gradlew assembleDebug
```

The APK lands at:

```
app/android/app/build/outputs/apk/debug/app-debug.apk
```

> From a fresh checkout of the ZIP you can run `bash tools/setup_android.sh`
> first — it recreates the native project, restores the hand-written
> `NexDevicePlugin.kt`, redraws the NEX launcher icons and creates the demo
> release keystore.

For the signed, minified build:

```bash
cd app/android && ./gradlew assembleRelease
# -> app/android/app/build/outputs/apk/release/app-release.apk
```

The demo signing key (`app/android/nex-release.keystore`, alias `nex`,
password `nexdemo123`) ships with the source so the release APK can be rebuilt
identically. Generate your own key before publishing anything real — see
`tools/create_keystore.sh`.

### 2.3 Install on a phone

1. On the phone: **Settings → About phone → tap "Build number" 7 times** to
   unlock Developer options.
2. **Settings → Developer options → USB debugging** → on.
3. Connect by USB and accept the debugging prompt.
4. Run:

```bash
adb install -r app/android/app/build/outputs/apk/debug/app-debug.apk
```

Or copy the APK to the phone and open it (allow "install from unknown sources").

### 2.4 Point NEX at your server

**Option A — set it on the phone (no rebuild):**

Long-press the two eyes for about one second → the setup panel opens → enter
your server address (for example `https://nex-ai-robot-pet-api.onrender.com`)
→ **Test & save** → **Close**.

**Option B — bake it into the APK:**

```bash
cd app
cp .env.example .env
# edit .env:
#   VITE_NEX_API_BASE=https://nex-ai-robot-pet-api.onrender.com
npm run build && npx cap sync android
```

### 2.5 Local testing without a public server

If the phone and the computer are on the same Wi-Fi:

1. Run the backend with `--host 0.0.0.0 --port 8000`.
2. Find the computer's LAN IP (`ip addr` / `ipconfig`).
3. In the setup panel enter `http://192.168.1.42:8000`.

> Cleartext HTTP is only allowed for `localhost`, `127.0.0.1` and the emulator
> host `10.0.2.2` (see `network_security_config.xml`). For any other LAN IP use
> HTTPS, or add your IP to that file.

With an Android emulator the host machine is always `http://10.0.2.2:8000`.

---

## Part 3 — First run checklist

| Step | What should happen |
| --- | --- |
| Launch NEX | Black screen, two cyan eyes, a blink now and then |
| Permission dialog | Android asks for the microphone — allow it |
| Greeting | NEX says *"Hi! I am NEX, your AI robot pet. Say 'Hey NEX' and talk to me!"* |
| Say "Hey NEX, how are you?" | Eyes switch to *thinking*, then NEX answers out loud |
| Say "NEX, dog ki awaaz nikalo!" | NEX makes a real dog sound |
| Say "NEX, dance!" | Eyes dance while NEX speaks |
| Say "NEX, tumhe kisne banaya?" | The exact creator sentence |
| Say "NEX, what time is it?" | The real current time, spoken |
| Say "NEX, apne school ke baare mein batao" | Grounded answer from montfortbagaha.org |
| Say "NEX, what is this?" (point the front camera) | NEX describes what it sees |

If NEX's eyes look **sad** on launch, the backend was unreachable — open the
setup panel (long-press) and fix the server address.
