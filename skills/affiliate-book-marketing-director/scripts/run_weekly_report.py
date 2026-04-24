#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace')
LOG = ROOT / 'state' / 'affiliate_marketing.log'
OUT = ROOT / 'state' / 'weekly_affiliate_report.md'


def main():
    if not LOG.exists():
        OUT.write_text('# Weekly Affiliate Report\n\nKhông có dữ liệu log tuần này.\n', encoding='utf-8')
        return

    rows = []
    for line in LOG.read_text(encoding='utf-8').splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    week_ago = datetime.now() - timedelta(days=7)
    recent = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r.get('ts', ''))
        except Exception:
            continue
        if ts >= week_ago:
            recent.append(r)

    posted = [r for r in recent if r.get('event') == 'morning_pipeline_posted']
    buy_handled = [r for r in recent if r.get('event') == 'triage_buy_intent_handled']
    casual_handled = [r for r in recent if r.get('event') == 'triage_casual_handled']

    lines = [
        '# Weekly Affiliate Report',
        '',
        f'- Tổng bài đã đăng: {len(posted)}',
        f'- Tương tác mua hàng đã xử lý: {len(buy_handled)}',
        f'- Bình luận xã giao đã phản hồi: {len(casual_handled)}',
        '',
        '## Gợi ý tối ưu tuần tới',
        '- Tăng tỷ lệ nội dung trend-jacking ở chủ đề đang có tương tác tốt',
        '- Chuẩn hóa hook 2 dòng đầu để cải thiện CTR vào inbox',
        '- Theo dõi riêng hiệu suất bài minigame Thứ Sáu',
    ]

    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
