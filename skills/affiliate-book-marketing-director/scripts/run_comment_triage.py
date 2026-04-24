#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

from config import get_settings
from logger import log, log_error
from meta_api import MetaClient, MetaApiError

ROOT = Path('/root/.openclaw/workspace')
TRACK_FILE = ROOT / 'state' / 'comment_triage_state.json'
POSTS_FILE = ROOT / 'state' / 'recent_posts.json'  # expected to store recent fb post ids

BUY_INTENTS = ['mua', 'xin link', 'giá', 'gia', 'đặt', 'đặt mua', 'chốt', 'ib', 'inbox']


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def classify(text: str) -> str:
    t = (text or '').lower()
    if any(k in t for k in BUY_INTENTS):
        return 'buy_intent'
    if len(t.strip()) == 0:
        return 'empty'
    return 'casual'


def main():
    cfg = get_settings()
    meta = MetaClient(cfg.meta_access_token)

    posts = load_json(POSTS_FILE, {'post_ids': []}).get('post_ids', [])
    state = load_json(TRACK_FILE, {'seen_comment_ids': []})
    seen = set(state.get('seen_comment_ids', []))

    affiliate_link = ''
    # Optional single link fallback for triage reply
    books_f = Path(cfg.books_csv_path)
    if books_f.exists():
        import csv
        with books_f.open('r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            if rows:
                affiliate_link = rows[0].get('affiliate_link', '').strip()

    for post_id in posts:
        try:
            comments = meta.get_post_comments(post_id, limit=100).get('data', [])
        except MetaApiError as e:
            log_error('triage_comments_fetch_failed', str(e), post_id=post_id)
            continue

        for c in comments:
            cid = c.get('id', '')
            msg = c.get('message', '')
            if not cid or cid in seen:
                continue

            intent = classify(msg)
            try:
                if intent == 'buy_intent' and affiliate_link:
                    # Private reply (if page has capability)
                    try:
                        meta.private_reply_to_comment(cid, f"Chào bạn, link đặt mua ưu đãi mình gửi bạn ở đây nhé: {affiliate_link}")
                        private_ok = True
                    except Exception:
                        private_ok = False

                    public_text = 'Mình đã inbox link ưu đãi cho bạn rồi nhé, bạn check tin nhắn chờ nha!'
                    meta.create_comment(post_id, public_text)
                    log('triage_buy_intent_handled', comment_id=cid, post_id=post_id, private_reply=private_ok)

                elif intent == 'casual':
                    meta.create_comment(post_id, 'Cảm ơn bạn đã ghé đọc và để lại bình luận nhé ❤️')
                    log('triage_casual_handled', comment_id=cid, post_id=post_id)

                else:
                    log('triage_skipped', comment_id=cid, post_id=post_id, reason=intent)

            except Exception as e:
                log_error('triage_comment_handle_failed', str(e), comment_id=cid, post_id=post_id)

            seen.add(cid)

    save_json(TRACK_FILE, {'seen_comment_ids': list(seen)})
    log('triage_done', tracked_comments=len(seen))


if __name__ == '__main__':
    main()
