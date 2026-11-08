#!/usr/bin/env bash
# Re-creates / customises the NEX Android project.
#
#   bash tools/setup_android.sh
#
# It is safe to run more than once. Steps:
#   1. `npx cap add android` (only if the android folder is missing)
#   2. copy the hand-written native overrides into the generated project
#   3. regenerate the NEX launcher icons
#   4. create the demo release keystore (if it does not exist)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/app"
ANDROID_DIR="$APP/android"
OVERLAY="$ROOT/tools/android-overlay"
PKG_PATH="app/src/main/java/ai/nexcompanion/virtualpet"

export JAVA_HOME="${JAVA_HOME:-/usr/local/nex/jdk}"
export ANDROID_HOME="${ANDROID_HOME:-/usr/local/nex/android-sdk}"

echo "==> 1/4 Android project"
if [ ! -d "$ANDROID_DIR" ]; then
  (cd "$APP" && npx cap add android)
else
  echo "    android/ already exists — keeping it"
fi

echo "==> 2/4 native overrides"
mkdir -p "$ANDROID_DIR/$PKG_PATH"
mkdir -p "$ANDROID_DIR/app/src/main/res/xml"
mkdir -p "$ANDROID_DIR/app/src/main/res/values"

cp "$OVERLAY/root-build.gradle"       "$ANDROID_DIR/build.gradle"
cp "$OVERLAY/variables.gradle"        "$ANDROID_DIR/variables.gradle"
cp "$OVERLAY/gradle.properties"       "$ANDROID_DIR/gradle.properties"
cp "$OVERLAY/app-build.gradle"        "$ANDROID_DIR/app/build.gradle"
cp "$OVERLAY/AndroidManifest.xml"     "$ANDROID_DIR/app/src/main/AndroidManifest.xml"
cp "$OVERLAY/network_security_config.xml" "$ANDROID_DIR/app/src/main/res/xml/network_security_config.xml"
cp "$OVERLAY/styles.xml"              "$ANDROID_DIR/app/src/main/res/values/styles.xml"
cp "$OVERLAY/MainActivity.java"       "$ANDROID_DIR/$PKG_PATH/MainActivity.java"
cp "$OVERLAY/NexDevicePlugin.kt"      "$ANDROID_DIR/$PKG_PATH/NexDevicePlugin.kt"

echo "==> 3/4 icons"
python3 "$ROOT/tools/generate_icon.py"

echo "==> 4/4 release keystore"
if [ ! -f "$ANDROID_DIR/nex-release.keystore" ]; then
  bash "$ROOT/tools/create_keystore.sh"
else
  echo "    nex-release.keystore already exists"
fi

echo
echo "Android project is ready."
echo "  build debug : (cd $ANDROID_DIR && ./gradlew assembleDebug)"
echo "  build release: (cd $ANDROID_DIR && ./gradlew assembleRelease)"
