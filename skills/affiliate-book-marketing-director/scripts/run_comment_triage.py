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
    meta = MetaClient(cfg.meta_access_token) if cfg.meta_access_token else None

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

    if meta:
        pages = meta.list_pages()
        if cfg.test_page_id:
            pages = [p for p in pages if str(p.get('id')) == str(cfg.test_page_id)]
        elif cfg.fb_page_id:
            pages = [p for p in pages if str(p.get('id')) == str(cfg.fb_page_id)]
    elif cfg.dry_run:
        pages = [{'id': 'dryrun_page_1', 'name': 'Dry Run Page 1', 'access_token': 'dryrun_page_token'}]
    else:
        raise SystemExit('META_ACCESS_TOKEN missing for live mode')

    for page in pages:
        page_id = str(page.get('id', ''))
        page_name = page.get('name', '')
        page_token = (page.get('access_token') or '').strip()
        if not page_id or not page_token:
            log_error('triage_page_skip', 'missing_page_id_or_token', page=page)
            continue

        try:
            if cfg.dry_run and not meta:
                posts = [{'id': f'{page_id}_post_1'}]
            else:
                posts = meta.list_page_posts(page_id, page_token, limit=10).get('data', [])
        except MetaApiError as e:
            log_error('triage_posts_fetch_failed', str(e), page_id=page_id, page_name=page_name)
            continue

        for p in posts:
            post_id = p.get('id', '')
            if not post_id:
                continue
            try:
                if cfg.dry_run and not meta:
                    comments = [
                        {'id': f'{post_id}_c1', 'message': 'Xin link giúp mình'},
                        {'id': f'{post_id}_c2', 'message': 'Bài hay quá'},
                    ]
                else:
                    comments = meta.get_post_comments(post_id, page_token, limit=100).get('data', [])
            except MetaApiError as e:
                log_error('triage_comments_fetch_failed', str(e), page_id=page_id, page_name=page_name, post_id=post_id)
                continue

            for c in comments:
                cid = c.get('id', '')
                msg = c.get('message', '')
                if not cid or cid in seen:
                    continue

                intent = classify(msg)
                try:
                    if intent == 'buy_intent' and affiliate_link:
                        public_text = f'Dạ sách đang có ưu đãi, bạn đặt mua chính hãng tại link này nhé: {affiliate_link}'
                        if not cfg.dry_run:
                            meta.create_comment(post_id, page_token, public_text)
                        log('triage_buy_intent_handled', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, private_reply=False, mode='dry_run' if cfg.dry_run else 'live', strategy='public_reply_only')

                    elif intent == 'casual':
                        if not cfg.dry_run:
                            meta.create_comment(post_id, page_token, 'Cảm ơn bạn đã ghé đọc và để lại bình luận nhé ❤️')
                        log('triage_casual_handled', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, mode='dry_run' if cfg.dry_run else 'live')

                    else:
                        log('triage_skipped', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, reason=intent)

                except Exception as e:
                    log_error('triage_comment_handle_failed', str(e), page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id)

                seen.add(cid)

    save_json(TRACK_FILE, {'seen_comment_ids': list(seen)})
    log('triage_done', tracked_comments=len(seen))


if __name__ == '__main__':
    main()
