#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace

export DRY_RUN="${DRY_RUN:-1}"
export BOOKS_CSV_PATH="${BOOKS_CSV_PATH:-/root/.openclaw/workspace/data/books_today.sample.csv}"

python3 /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/run_morning_pipeline.py >> /root/.openclaw/workspace/state/affiliate_marketing_cron.log 2>&1
