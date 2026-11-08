#!/usr/bin/env bash
# Creates the demo signing keystore used for the NEX release APK.
#
# This is a DEMO keystore with published credentials so anyone can rebuild an
# identical, installable APK. For a real app, generate your own keystore and
# keep it secret:
#
#   keytool -genkeypair -v -keystore my-release.keystore -alias myapp \
#           -keyalg RSA -keysize 2048 -validity 10000
#
set -euo pipefail

KEYSTORE="$(dirname "$0")/../app/android/nex-release.keystore"
ALIAS="nex"
STOREPASS="nexdemo123"
KEYPASS="nexdemo123"

# keytool ships with the JDK — make sure it is on the PATH.
if ! command -v keytool >/dev/null 2>&1; then
  for candidate in "${JAVA_HOME:-}/bin" /usr/lib/jvm/*/bin /usr/local/*/bin; do
    if [ -x "$candidate/keytool" ]; then
      PATH="$candidate:$PATH"
      export PATH
      break
    fi
  done
fi

if ! command -v keytool >/dev/null 2>&1; then
  echo "keytool not found. Install a JDK (17+) or set JAVA_HOME." >&2
  exit 1
fi

if [ -f "$KEYSTORE" ]; then
  echo "Keystore already exists: $KEYSTORE"
  exit 0
fi

keytool -genkeypair -v \
  -keystore "$KEYSTORE" \
  -alias "$ALIAS" \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10950 \
  -storepass "$STOREPASS" \
  -keypass "$KEYPASS" \
  -dname "CN=NEX AI Robot Pet, OU=Arnav Divya Aryan, O=NEX, L=Patna, S=Bihar, C=IN"

echo "Created $KEYSTORE"
echo "  alias=$ALIAS storepass=$STOREPASS keypass=$KEYPASS"
