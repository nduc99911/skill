#!/usr/bin/env bash
set -euo pipefail
set -a
source /root/.openclaw/workspace/.env
set +a
python3 /root/.openclaw/workspace/skills/affiliate-book-marketing-director/scripts/run_comment_triage.py
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.openclaw/workspace/state/affiliate_marketing.log')
for line in p.read_text(encoding='utf-8').splitlines()[-200:]:
    if 'triage_read_only_preview' in line or 'triage_skipped' in line or 'triage_done' in line:
        print(line)
PY
