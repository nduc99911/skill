#!/bin/bash

# Configuration
WORKSPACE="/root/.openclaw/workspace"
PLANNER_SCRIPT="$WORKSPACE/scripts/planner.py"
OUTPUT_PLAN="$WORKSPACE/output/daily-plan.json"
ERROR_LOG="$WORKSPACE/state/error.log"
TELEGRAM_TARGET="8051440849"

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
print(f"--- PLAN SUMMARY: {d.get('date')} ---")
for post in d.get('posts', []):
    # Short one-liner per post
    label_map = {
        'soft_content': 'soft',
        'direct_sell': 'direct',
        'listicle': 'listicle'
    }
    post_type = label_map.get(post['post_type'], post['post_type'])
    placement = post.get('link_placement', 'caption')
    line = f"- {post['page_name']} | {post['scheduled_time'].split()[-1]} | {post['product_title']} | {post_type} | {placement}"
    print(line)
errs = d.get('errors', [])
if errs:
    print("\n[ERRORS]")
    for e in errs:
        print(f"! {e.get('page_id') or e.get('product_id')}: {e.get('error')}")
PY
)
    # Write source-of-truth summary snapshot for this run
    echo "$SUMMARY" > "$WORKSPACE/state/planner_summary.txt"

    # Try to deliver directly to Telegram
    SEND_OUTPUT=$(openclaw message send --channel telegram --target "$TELEGRAM_TARGET" --message "$SUMMARY" 2>&1)
    SEND_CODE=$?

    if [ $SEND_CODE -eq 0 ]; then
        echo "[$(date)] Planner finished successfully and Telegram summary sent." >> "$WORKSPACE/state/planner_cron.log"
    else
        echo "[$(date)] Planner finished, but Telegram send failed." >> "$WORKSPACE/state/planner_cron.log"
        echo "[$(date)] SEND_ERROR: $SEND_OUTPUT" >> "$WORKSPACE/state/planner_cron.log"
        echo "[$(date)] Fallback command available: Xem planner hôm nay" >> "$WORKSPACE/state/planner_cron.log"
    fi
else
    echo "[$(date)] Planner failed. Check $ERROR_LOG" >> "$WORKSPACE/state/planner_cron.log"
fi
