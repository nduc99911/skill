#!/bin/bash
# Daily scheduler: 07:00 Asia/Ho_Chi_Minh
# Reads all jobs for today from Google Sheet and schedules exact-time posts via `at`.
set -euo pipefail

SHEET_ID="1fCY0TLJnNDoTyfitNkiGHS44AwEHY2e4Rtnx7Gz4IBg"
SHEET_CSV="https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv"
POST_SCRIPT="/root/.openclaw/workspace/scripts/thuc-thi-dang-bai.sh"
STATE_DIR="/root/.openclaw/workspace/state"
LOG_FILE="$STATE_DIR/scheduler.log"

mkdir -p "$STATE_DIR"

python3 - <<'PY'
import csv
import io
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import urllib.request

sheet_csv = os.environ.get('SHEET_CSV', 'https://docs.google.com/spreadsheets/d/1fCY0TLJnNDoTyfitNkiGHS44AwEHY2e4Rtnx7Gz4IBg/export?format=csv')
post_script = os.environ.get('POST_SCRIPT', '/root/.openclaw/workspace/scripts/thuc-thi-dang-bai.sh')
log_file = os.environ.get('LOG_FILE', '/root/.openclaw/workspace/state/scheduler.log')

TZ_HN = ZoneInfo('Asia/Ho_Chi_Minh')
now_hn = datetime.now(TZ_HN)
today = now_hn.date().isoformat()


def log(msg: str):
    ts = datetime.now(TZ_HN).strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {msg}\n')

log(f'Quét lịch đăng cho ngày: {today}')

with urllib.request.urlopen(sheet_csv, timeout=30) as r:
    raw = r.read().decode('utf-8', errors='ignore')

reader = csv.DictReader(io.StringIO(raw))
count = 0
for row in reader:
    ngay = (row.get('ngay') or '').strip()
    gio = (row.get('gio') or '').strip()
    page = (row.get('page') or '').strip()
    mode = (row.get('mode') or '').strip()
    topic = (row.get('ten_sach_hoac_chu_de') or '').strip()
    link = (row.get('link_aff') or '').strip()
    notes = (row.get('ghi_chu') or '').strip()
    status = (row.get('trang_thai') or '').strip().lower()

    if ngay != today:
        continue
    if status == 'posted':
        continue
    if not gio or not page or not mode:
        continue

    # Schedule by Hanoi wall-clock time directly
    try:
        dt_hn = datetime.strptime(f'{ngay} {gio}', '%Y-%m-%d %H:%M').replace(tzinfo=TZ_HN)
    except ValueError:
        log(f'WARN bỏ qua dòng sai định dạng: ngay={ngay} gio={gio}')
        continue

    # Skip times already passed to avoid late or duplicate posts
    if dt_hn <= now_hn:
        log(f'SKIP quá giờ: {gio} HN | page={page} | mode={mode}')
        continue

    at_time = dt_hn.strftime('%Y%m%d%H%M')

    cmd = f'TZ=Asia/Ho_Chi_Minh {post_script} "{page}" "{mode}" "{topic}" "{link}" "{notes}"'
    proc = subprocess.run(['at', '-t', at_time], input=(cmd + '\n').encode('utf-8'), capture_output=True)

    if proc.returncode == 0:
        log(f"Lên lịch OK: {gio} HN | page={page} | mode={mode}")
        count += 1
    else:
        err = (proc.stderr or b'').decode('utf-8', errors='ignore').strip()
        log(f"ERROR lên lịch thất bại {gio} HN: {err}")

log(f'Đã đưa {count} task hôm nay vào hàng chờ at.')
PY
