#!/usr/bin/env bash
# Run on the Pi (usually over SSH) to update and restart the display.
#   ./deploy/deploy.sh [branch-or-tag]     e.g. development, main, v1.0
# With no argument it uses the last one you deployed (default: development).
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET_NAME="${1:-$(cat .deploy-branch 2>/dev/null || echo development)}"
COMPOSE="docker compose -f docker-compose.pi.yml"

git fetch --quiet --tags --force origin "+refs/heads/*:refs/remotes/origin/*"
TARGET=$(git rev-parse -q --verify "refs/remotes/origin/$TARGET_NAME" \
      || git rev-parse -q --verify "refs/tags/$TARGET_NAME^{commit}" \
      || { echo "unknown branch or tag: $TARGET_NAME" >&2; exit 1; })

git checkout --quiet --force --detach "$TARGET"
echo "$TARGET_NAME" > .deploy-branch
$COMPOSE up -d --build
echo "deployed $TARGET_NAME @ $(git rev-parse --short HEAD)"
