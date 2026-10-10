#!/bin/bash
# Builds "Ledger Check.app" and installs it in /Applications.
# Usage: ./macapp/build.sh            (from the repo root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist/Ledger Check.app"
rm -rf "$OUT"
mkdir -p "$OUT/Contents/MacOS" "$OUT/Contents/Resources/project"

swiftc -O -parse-as-library -o "$OUT/Contents/MacOS/LedgerCheck" "$ROOT/macapp/LedgerCheck.swift" -framework Cocoa -framework WebKit

# Bundle the containers' source (never the .env with the API key).
cp "$ROOT/docker-compose.yml" "$OUT/Contents/Resources/project/"
for d in egress sandbox gateway; do rsync -a --exclude '__pycache__' "$ROOT/$d" "$OUT/Contents/Resources/project/"; done
[ -f "$ROOT/macapp/AppIcon.icns" ] && cp "$ROOT/macapp/AppIcon.icns" "$OUT/Contents/Resources/"

cat > "$OUT/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Ledger Check</string>
  <key>CFBundleDisplayName</key><string>Ledger Check</string>
  <key>CFBundleIdentifier</key><string>dev.ledgercheck.mac</string>
  <key>CFBundleExecutable</key><string>LedgerCheck</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST

codesign --force --deep --sign - "$OUT" >/dev/null

# On this Mac, reuse an existing key so the app doesn't ask (the key stays out of the app bundle).
SUPPORT="$HOME/Library/Application Support/LedgerCheck/project"
if [ -f "$ROOT/.env" ] && [ ! -f "$SUPPORT/.env" ]; then
  mkdir -p "$SUPPORT" && cp "$ROOT/.env" "$SUPPORT/.env" && chmod 600 "$SUPPORT/.env"
fi

rm -rf "/Applications/Ledger Check.app"
cp -R "$OUT" /Applications/
echo "Installed /Applications/Ledger Check.app"
