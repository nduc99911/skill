#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace

if [ -f /root/.openclaw/workspace/.env ]; then
  set -a
  source /root/.openclaw/workspace/.env
  set +a
fi

export DRY_RUN="${DRY_RUN:-1}"
export PIPELINE_MODE="${PIPELINE_MODE:-schedule_day}"
export BOOKS_CSV_PATH="${BOOKS_CSV_PATH:-/root/.openclaw/workspace/data/books_today.sample.csv}"

/root/.openclaw/workspace/.venv_aff/bin/python /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/run_morning_pipeline.py >> /root/.openclaw/workspace/state/affiliate_marketing_cron.log 2>&1
