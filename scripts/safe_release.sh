#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "未检测到 .git 目录，请在仓库根目录运行。"
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "请先切换到公开分支 main，再执行发布。"
  exit 1
fi

if git diff --name-only HEAD -- README.local.md 'docs/*.md' | grep . >/dev/null 2>&1; then
  echo "检测到私有文件变更，已阻止发布："
  git diff --name-only HEAD -- README.local.md 'docs/*.md'
  exit 1
fi

echo "公开发布前检查通过。"
echo "接下来可以继续："
echo "  1. 更新版本号"
echo "  2. 更新 CHANGELOG"
echo "  3. 提交 main"
echo "  4. 打 tag 并推送"
