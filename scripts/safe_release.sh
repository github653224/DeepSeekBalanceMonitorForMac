#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXPECTED_VERSION="${1:-}"

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

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "检测到工作区或暂存区还有未提交变更，请先整理后再发布。"
  git status --short
  exit 1
fi

if git diff --name-only HEAD -- README.local.md 'docs/*.md' | grep . >/dev/null 2>&1; then
  echo "检测到私有文件变更，已阻止发布："
  git diff --name-only HEAD -- README.local.md 'docs/*.md'
  exit 1
fi

CURRENT_VERSION="$(python3 - <<'PY'
from pathlib import Path
import re

text = Path("pyproject.toml").read_text(encoding="utf-8")
match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
print(match.group(1) if match else "")
PY
)"

if [ -z "$CURRENT_VERSION" ]; then
  echo "未能从 pyproject.toml 解析到版本号。"
  exit 1
fi

if [ -n "$EXPECTED_VERSION" ] && [ "$CURRENT_VERSION" != "$EXPECTED_VERSION" ]; then
  echo "版本号不一致：pyproject.toml 当前是 $CURRENT_VERSION，但你期望的是 $EXPECTED_VERSION"
  exit 1
fi

if ! grep -q "^## $CURRENT_VERSION$" CHANGELOG.md; then
  echo "CHANGELOG.md 中未找到版本标题：## $CURRENT_VERSION"
  exit 1
fi

if git rev-parse --verify "v$CURRENT_VERSION" >/dev/null 2>&1; then
  echo "标签 v$CURRENT_VERSION 已存在，请确认是否要复用版本号。"
  exit 1
fi

echo "公开发布前检查通过。"
echo "分支: $CURRENT_BRANCH"
echo "版本: $CURRENT_VERSION"
echo "CHANGELOG: 已检测到 ## $CURRENT_VERSION"
echo
echo "建议继续执行："
echo "  git add ."
echo "  git commit -m \"chore: release v$CURRENT_VERSION\""
echo "  git push origin main"
echo "  git tag v$CURRENT_VERSION"
echo "  git push origin v$CURRENT_VERSION"
