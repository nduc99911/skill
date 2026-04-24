#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace')
STATE_DIR = ROOT / 'state'
STATE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = STATE_DIR / 'affiliate_marketing.log'
ERR_FILE = STATE_DIR / 'affiliate_marketing_error.log'


def _ts() -> str:
    return datetime.now().isoformat(timespec='seconds')


def log(event: str, **data):
    payload = {'ts': _ts(), 'event': event, **data}
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def log_error(event: str, error: str, **data):
    payload = {'ts': _ts(), 'event': event, 'error': error, **data}
    with ERR_FILE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
