#!/bin/bash
# Builds the standalone "Ledger Shield.app" (no Docker, no internet) and a .dmg installer.
# Usage: ./macapp/build_shield.sh        (from the repo root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/gateway/static/shield"
OUT="$ROOT/dist/Ledger Shield.app"
DMG="$ROOT/dist/Ledger-Shield.dmg"

[ -f "$WEB/models/Xenova/bert-base-NER/onnx/model_quantized.onnx" ] || "$WEB/download_model.sh"

rm -rf "$OUT"
mkdir -p "$OUT/Contents/MacOS" "$OUT/Contents/Resources/web"
swiftc -O -parse-as-library -o "$OUT/Contents/MacOS/LedgerShield" "$ROOT/macapp/LedgerShield.swift" -framework Cocoa -framework WebKit -framework Network
rsync -a --exclude 'download_model.sh' --exclude '.DS_Store' "$WEB/" "$OUT/Contents/Resources/web/"
cp "$ROOT/macapp/AppIcon.icns" "$OUT/Contents/Resources/"

cat > "$OUT/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Ledger Shield</string>
  <key>CFBundleDisplayName</key><string>Ledger Shield</string>
  <key>CFBundleIdentifier</key><string>dev.ledgercheck.shield</string>
  <key>CFBundleExecutable</key><string>LedgerShield</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.finance</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key><string>Ledger Shield · encrypts bank data on this Mac before any AI sees it</string>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST

codesign --force --deep --sign - "$OUT" >/dev/null

# Installer disk image: drag the app onto Applications.
STAGE="$(mktemp -d)"
cp -R "$OUT" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "Ledger Shield" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

rm -rf "/Applications/Ledger Shield.app" && cp -R "$OUT" /Applications/
echo "Built $DMG ($(du -h "$DMG" | cut -f1)) and installed /Applications/Ledger Shield.app"
