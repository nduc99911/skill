#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
python3 /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/run_weekly_report.py >> /root/.openclaw/workspace/state/affiliate_marketing_cron.log 2>&1
