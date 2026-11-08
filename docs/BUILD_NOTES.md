# Build notes — exact commands that produced the shipped artifacts

This file records how the APKs in `apk/` were actually built and how to
reproduce them. It is written for the build machine used for this project.

---

## 1. Toolchain

| Tool | Version | Location on the build machine |
| --- | --- | --- |
| JDK | Temurin 21.0.8 | `/usr/local/nex/jdk` |
| Node.js | 22.20.0 | `/usr/local/nex/node` |
| Android SDK | platform 36, build-tools 36.0.0 | `/usr/local/nex/android-sdk` |
| Gradle | 8.14.3 (wrapper) | `app/android/gradlew` |
| AGP / Kotlin | 8.13.0 / 2.2.20 | `app/android/build.gradle` |
| Python | 3.13 (3.11 works too) | venv at `/usr/local/nex/venv` |

One-liner environment setup:

```bash
source /usr/local/nex/env.sh
```

`env.sh` exports `JAVA_HOME`, `ANDROID_HOME`, `GRADLE_USER_HOME` and the
`PATH` entries for `node`, `java` and `adb`.

> The toolchain lives **outside** the workspace on purpose — the workspace is
> snapshotted and large directories under it can be wiped by the environment.

---

## 2. Backend

```bash
/usr/local/nex/venv/bin/pip install -r backend/requirements.txt
cd backend
PYTHONPATH=. /usr/local/nex/venv/bin/python -m uvicorn app.main:app \
    --host 127.0.0.1 --port 8000
```

No `GEMINI_API_KEY` was available, so `/health` reports
`"gemini_configured": false` and `/api/chat` answers with a `config_error`.

---

## 3. Web app

```bash
cd app
/usr/local/nex/node/bin/npm install
/usr/local/nex/node/bin/npx tsc --noEmit     # clean
/usr/local/nex/node/bin/npm run build        # -> app/dist
/usr/local/nex/node/bin/npx cap sync android  # copy into the native project
```

Build output: `dist/assets/index-*.js` 262 kB (83 kB gzip) + 23 WAV assets.

---

## 4. Native Android project

```bash
bash tools/setup_android.sh
```

This script is idempotent and does four things:

1. `npx cap add android` — only if `app/android/` is missing.
2. Copies the hand-written files from `tools/android-overlay/` into the
   generated project (manifest, permissions, Gradle files, `NexDevicePlugin.kt`,
   `MainActivity.java`, `network_security_config.xml`, `styles.xml`).
3. Redraws the NEX launcher icon into every mipmap density.
4. Creates the demo release keystore `app/android/nex-release.keystore`
   (alias `nex`, password `nexdemo123`).

---

## 5. APKs

```bash
cd app/android
export GRADLE_USER_HOME=/usr/local/nex/gradle
./gradlew assembleDebug --no-daemon
./gradlew assembleRelease --no-daemon
```

Results on the build machine:

| Build | Output | Size | Time |
| --- | --- | --- | --- |
| debug | `app/build/outputs/apk/debug/app-debug.apk` | 44 368 000 B | 1 m 35 s |
| release | `app/build/outputs/apk/release/app-release.apk` | 40 313 563 B | 35 s |

Both were copied to `apk/nex-2.0-debug.apk` and `apk/nex-2.0-release.apk`.

### Memory settings that matter

`app/android/gradle.properties` keeps the build inside ~1 GB of RAM:

```
org.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m
org.gradle.daemon=false
org.gradle.workers.max=1
kotlin.compiler.execution.strategy=in-process
```

Raising these on a 2 GB machine makes the Kotlin compiler swap and hang.
Lint tasks are disabled in `app/android/build.gradle` because lint model
generation stalls the release build on small machines.

---

## 6. Verification that was actually run

```bash
# backend — 24 checks, 3 Gemini groups skipped (no key)
cd backend && python3 tests/test_backend.py

# eye engine — 26 checks against the real engine
cd app && node ../tools/test_eye_engine.mjs

# APK inspection
$ANDROID_HOME/build-tools/36.0.0/aapt2 dump badging apk/nex-2.0-release.apk
$ANDROID_HOME/build-tools/36.0.0/apksigner verify --print-certs \
    apk/nex-2.0-release.apk
```

Verified on the release APK: package `ai.nexcompanion.virtualpet`, label `NEX`,
minSdk 24, targetSdk 36, permissions `INTERNET`, `ACCESS_NETWORK_STATE`,
`RECORD_AUDIO`, `CAMERA`, launcher activity `ai.nexcompanion.virtualpet.MainActivity`,
23 sound assets bundled, signed with
`CN=NEX AI Robot Pet, OU=Arnav Divya Aryan, O=NEX, L=Patna, ST=Bihar, C=IN`.

---

## 7. What was NOT verified

* No live Gemini request was ever executed — **no API key was available**.
  The three Gemini-dependent test groups report SKIP.
* The APK was not installed on a physical phone, so microphone capture, TTS,
  CameraX capture and ML Kit face detection are **implemented and compiled**
  but not confirmed on real hardware.
* The face-detection and camera code paths compile and are wired into the UI,
  but only the "what is this?" capture path was reasoned through statically.
