#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PRIVATE_BRANCH="private-docs"
PRIVATE_REMOTE="private"
PRIVATE_REMOTE_BRANCH="main"

cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "未检测到 .git 目录，请在仓库根目录运行。"
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"

cleanup() {
  if [ "$(git branch --show-current)" != "$CURRENT_BRANCH" ]; then
    git switch "$CURRENT_BRANCH" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "当前分支: $CURRENT_BRANCH"
echo "切换到私有分支: $PRIVATE_BRANCH"
git switch "$PRIVATE_BRANCH" >/dev/null

echo "同步本地私有文档到索引..."
git add -f README.local.md docs/*.md

if git diff --cached --quiet; then
  echo "没有检测到新的私有文档变更。"
else
  COMMIT_MSG="${1:-docs: sync private docs}"
  echo "提交私有文档更新: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"
fi

echo "推送到私有远程: $PRIVATE_REMOTE ($PRIVATE_BRANCH -> $PRIVATE_REMOTE_BRANCH)"
git push "$PRIVATE_REMOTE" "$PRIVATE_BRANCH:$PRIVATE_REMOTE_BRANCH"

echo "私有文档同步完成。"
