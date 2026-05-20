#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_SRC="$ROOT_DIR/scripts/hooks/pre-push"
HOOK_DST="$ROOT_DIR/.git/hooks/pre-push"

if [ ! -d "$ROOT_DIR/.git" ]; then
  echo "未检测到 .git 目录，请在仓库根目录运行。"
  exit 1
fi

mkdir -p "$(dirname "$HOOK_DST")"
cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

echo "已安装 Git pre-push hook:"
echo "  $HOOK_DST"
echo
echo "作用："
echo "  - 阻止向公开 origin 推送 README.local.md 和 docs/*.md"
echo "  - 允许向 private 远程推送私有资料"
