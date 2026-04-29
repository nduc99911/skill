#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/root/.openclaw/workspace"
SCRIPT_DIR="$WORKDIR/skills/shopee-affiliate-comment-replier/scripts"
LOG_FILE="$WORKDIR/skills/shopee-affiliate-comment-replier/scanner.log"
PY_BIN="python3"

cd "$WORKDIR"

"$PY_BIN" "$SCRIPT_DIR/cron_scanner.py" --limit-posts 10 --limit-comments 20 >> "$LOG_FILE" 2>&1
