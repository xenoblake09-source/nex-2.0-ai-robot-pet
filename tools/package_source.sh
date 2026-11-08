#!/usr/bin/env bash
# Packages the NEX source code into a clean, GitHub-ready ZIP.
#
#   bash tools/package_source.sh
#
# Output: dist/nex-source-<timestamp>.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist"
STAMP="$(date +%Y%m%d-%H%M%S)"
ZIP="$OUT_DIR/nex-source-$STAMP.zip"

mkdir -p "$OUT_DIR"
rm -f "$ZIP"

cd "$ROOT"

# Everything except build output, dependencies and local secrets.
zip -r -q "$ZIP" . \
  -x "*/node_modules/*" \
  -x "*/.git/*" \
  -x "*/.gradle/*" \
  -x "*/build/*" \
  -x "*/dist/*" \
  -x "dist/*" \
  -x "*.zip" \
  -x "*/.venv/*" \
  -x "*/__pycache__/*" \
  -x "*/.env" \
  -x "*/local.properties" \
  -x "*/.pytest_cache/*" \
  -x "*.apk" \
  -x "*.aab" \
  -x "*/.DS_Store" \
  -x "*/.idea/*" \
  -x "*/.vscode/*" \
  -x "*.pyc"

echo "Created $ZIP"
ls -la "$ZIP"
