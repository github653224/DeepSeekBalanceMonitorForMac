#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_NAME="DeepSeek Balance Monitor.app"
DMG_NAME="DeepSeek-Balance-Monitor-mac.dmg"
APP_PATH="$DIST_DIR/$APP_NAME"
DMG_PATH="$DIST_DIR/$DMG_NAME"
STAGE_DIR="$DIST_DIR/.dmg-stage"

if [ ! -d "$APP_PATH" ]; then
  echo "App bundle not found: $APP_PATH"
  echo "Run bash scripts/build_mac.sh first."
  exit 1
fi

rm -rf "$STAGE_DIR" "$DMG_PATH"
mkdir -p "$STAGE_DIR"
cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

hdiutil create \
  -volname "DeepSeek Balance Monitor" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$STAGE_DIR"
echo "DMG created: $DMG_PATH"
