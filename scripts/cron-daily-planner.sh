#!/bin/bash

# Configuration
WORKSPACE="/root/.openclaw/workspace"
PLANNER_SCRIPT="$WORKSPACE/scripts/planner.py"
OUTPUT_PLAN="$WORKSPACE/output/daily-plan.json"
ERROR_LOG="$WORKSPACE/state/error.log"
TELEGRAM_SESSION_KEY="telegram:8051440849"

# Ensure directories exist
mkdir -p "$WORKSPACE/state"
mkdir -p "$WORKSPACE/output"

echo "[$(date)] Starting daily planner..." >> "$WORKSPACE/state/planner_cron.log"

# Run the planner
/usr/bin/python3 "$PLANNER_SCRIPT" >> "$WORKSPACE/state/planner_cron.log" 2>> "$ERROR_LOG"

if [ $? -eq 0 ]; then
    # Planner success: generate summary for the user
    SUMMARY=$(/usr/bin/python3 - <<'PY'
import json, os
p='/root/.openclaw/workspace/output/daily-plan.json'
if not os.path.exists(p):
    print("Error: daily-plan.json not found.")
    exit(0)
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f"✅ LẬP PLAN THÀNH CÔNG ({d.get('date')})")
print(f"Tổng số bài: {len(d.get('posts', []))}")
print("-" * 20)
for post in d.get('posts', []):
    print(f"Page: {post['page_name']}")
    print(f"Giờ: {post['scheduled_time']}")
    print(f"Loại: {post['post_type']}")
    print(f"Sách: {post['product_title']}")
    print("-" * 10)
print("Trạng thái: Đang chờ duyệt (approved-plan.json chưa cập nhật)")
PY
)
    # Send summary to user via sessions_send (requires openclaw CLI or tool use)
    # Since this runs in cron, we use the openclaw messenger bridge if available, 
    # but here we'll just log it and rely on the agent heartbeat to report.
    echo "$SUMMARY" >> "$WORKSPACE/state/planner_summary.txt"
    echo "[$(date)] Planner finished successfully." >> "$WORKSPACE/state/planner_cron.log"
else
    echo "[$(date)] Planner failed. Check $ERROR_LOG" >> "$WORKSPACE/state/planner_cron.log"
fi
