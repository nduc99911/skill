#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import requests
from pathlib import Path
from typing import Dict

from config import get_settings
from logger import log, log_error
from meta_api import MetaClient, MetaApiError

ROOT = Path('/root/.openclaw/workspace')
TRACK_FILE = ROOT / 'state' / 'comment_triage_state.json'
POSTS_FILE = ROOT / 'state' / 'recent_posts.json'  # expected to store recent fb post ids
QUEUE_FILE = ROOT / 'state' / 'affiliate_publish_queue.json'

BUY_INTENTS = ['mua', 'xin link', 'giá', 'gia', 'đặt', 'đặt mua', 'chốt', 'ib', 'inbox', 'link shop', 'link mua']
NEGATIVE_INTENTS = ['lừa', 'xạo', 'rác', 'spam', 'đểu', 'ngu', 'dở', 'tệ', 'nhảm', 'xàm', 'chửi', 'khốn nạn', 'óc chó']
NEGATIVE_REGEX = [r'(^|\s)đm($|\s)', r'(^|\s)dm($|\s)']
SPAM_PATTERNS = [r'https?://', r'www\.', r't\.me/', r'bit\.ly/']


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _classify_heuristic(text: str) -> str:
    t = (text or '').lower().strip()
    if any(k in t for k in BUY_INTENTS):
        return 'buy_intent'
    if any(k in t for k in NEGATIVE_INTENTS + ['chán', 'chan', 'phí tiền', 'phi tien', 'tốn tiền', 'ton tien']):
        return 'negative_or_spam'
    if any(re.search(p, t) for p in NEGATIVE_REGEX):
        return 'negative_or_spam'
    if any(re.search(p, t) for p in SPAM_PATTERNS):
        return 'negative_or_spam'
    if len(t.strip()) == 0:
        return 'empty'
    return 'casual'


def _classify_llm(text: str) -> str | None:
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None
    try:
        prompt = (
            'Phân loại bình luận tiếng Việt vào đúng 1 nhãn: buy_intent | casual | negative_or_spam | empty. '
            'Quy tắc: hỏi thêm thông tin/nội dung sách (ví dụ sinh viên có đọc được không) => casual. '
            'Chê bai gay gắt/chửi bới/tiêu cực/link rác => negative_or_spam. '
            'Xin link/mua/chốt/giá => buy_intent. Chỉ trả về đúng 1 nhãn, không giải thích.'
        )
        r = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': f'Bình luận: "{text}"'},
                ],
                'max_tokens': 16,
                'temperature': 0,
            },
            timeout=20,
        )
        if r.status_code >= 400:
            return None
        label = (r.json().get('choices', [{}])[0].get('message', {}).get('content', '') or '').strip().lower()
        if label in {'buy_intent', 'casual', 'negative_or_spam', 'empty'}:
            return label
        return None
    except Exception:
        return None


def classify(text: str) -> str:
    llm_label = _classify_llm(text)
    if llm_label:
        return llm_label
    return _classify_heuristic(text)


def _dynamic_reply_heuristic(comment_text: str) -> str:
    t = (comment_text or '').lower()
    if '@' in t or 'tag' in t:
        return 'Chào cả nhà, cảm ơn mọi người đã quan tâm. Nếu cần mình gửi thêm gợi ý sách phù hợp theo mục tiêu luôn nhé 📚'
    if any(k in t for k in ['hay', 'tuyệt', 'xịn', 'ok', 'hữu ích', 'đỉnh']):
        return 'Cảm ơn bạn nhiều nha, rất vui vì nội dung này hữu ích với bạn. Mình sẽ tiếp tục chia sẻ thêm các góc nhìn thực tế từ sách nhé ✨'
    if '?' in t or any(k in t for k in ['nội dung', 'review', 'có gì', 'phù hợp', 'nên đọc']):
        return 'Câu hỏi hay quá bạn. Cuốn này nổi bật ở phần ứng dụng thực tế, đọc xong có thể áp dụng ngay vào giao tiếp và công việc hằng ngày.'
    return 'Cảm ơn bạn đã tương tác nè. Mình sẽ tiếp tục cập nhật thêm nhiều nội dung sách hữu ích để cả nhà cùng tham khảo nhé ❤️'


def _dynamic_reply_llm(comment_text: str) -> str | None:
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None
    try:
        r = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Bạn là admin fanpage sách. Viết 1-2 câu trả lời bình luận tự nhiên, thân thiện, tiếng Việt, không dùng markdown, không dùng dấu sao, không quá 45 từ.'
                    },
                    {
                        'role': 'user',
                        'content': f'Bình luận của khách: "{comment_text}". Hãy trả lời phù hợp ngữ cảnh.'
                    }
                ],
                'max_tokens': 120,
                'temperature': 0.7,
            },
            timeout=20,
        )
        if r.status_code >= 400:
            return None
        data = r.json()
        return (data.get('choices', [{}])[0].get('message', {}).get('content', '') or '').strip() or None
    except Exception:
        return None


def dynamic_reply(comment_text: str) -> str:
    llm = _dynamic_reply_llm(comment_text)
    if llm:
        return llm
    return _dynamic_reply_heuristic(comment_text)


def is_blank_link(link: str) -> bool:
    x = (link or '').strip()
    if not x:
        return True
    return x.lower() == 'none'


def resolve_affiliate_link_for_post(post_id: str, fallback_link: str) -> str:
    """Prefer per-post link from queue history; fallback to default link if valid."""
    q = load_json(QUEUE_FILE, {'items': []})
    for item in q.get('items', []):
        if str(item.get('fb_post_id', '')).strip() == str(post_id).strip():
            b = item.get('book', {}) or {}
            link = (b.get('affiliate_link') or b.get('Link Aff') or b.get('link aff') or '').strip()
            if not is_blank_link(link):
                return link
            return ''
    if not is_blank_link(fallback_link):
        return fallback_link.strip()
    return ''


def main():
    cfg = get_settings()
    meta = MetaClient(cfg.meta_access_token) if cfg.meta_access_token else None

    state = load_json(TRACK_FILE, {'seen_comment_ids': []})
    seen = set(state.get('seen_comment_ids', []))

    affiliate_link = ''
    # Optional fallback link (legacy behavior). Per-post link from queue is preferred.
    books_f = Path(cfg.books_csv_path)
    if books_f.exists():
        import csv
        with books_f.open('r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            if rows:
                r0 = rows[0]
                affiliate_link = (r0.get('affiliate_link') or r0.get('Link Aff') or r0.get('link aff') or '').strip()

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
                    resolved_link = resolve_affiliate_link_for_post(post_id, affiliate_link)

                    if intent == 'buy_intent' and resolved_link:
                        public_text = f'Dạ sách đang có ưu đãi, bạn đặt mua chính hãng tại link này nhé: {resolved_link}'
                        if not cfg.dry_run:
                            meta.create_comment(cid, page_token, public_text)
                        log('triage_buy_intent_handled', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, private_reply=False, mode='dry_run' if cfg.dry_run else 'live', strategy='public_reply_only_threaded')

                    elif intent == 'buy_intent' and not resolved_link:
                        # Link trống/NONE -> tuyệt đối không chốt đơn bằng link lỗi; chuyển sang tư vấn casual.
                        reply_text = 'Cảm ơn bạn quan tâm nha. Bài này mình đang cập nhật link đặt mua, mình sẽ gửi thông tin phù hợp sớm cho bạn nhé 🙏'
                        if not cfg.dry_run:
                            meta.create_comment(cid, page_token, reply_text)
                        log('triage_buy_intent_downgraded_to_casual', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, mode='dry_run' if cfg.dry_run else 'live', reason='blank_or_none_affiliate_link')

                    elif intent == 'casual':
                        reply_text = dynamic_reply(msg)
                        if not cfg.dry_run:
                            meta.create_comment(cid, page_token, reply_text)
                        log('triage_casual_handled', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, mode='dry_run' if cfg.dry_run else 'live', reply_preview=reply_text[:180], strategy='threaded_reply')

                    elif intent == 'negative_or_spam':
                        log('triage_skipped', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, reason='negative_or_spam')

                    else:
                        log('triage_skipped', page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id, reason=intent)

                except Exception as e:
                    log_error('triage_comment_handle_failed', str(e), page_id=page_id, page_name=page_name, comment_id=cid, post_id=post_id)

                seen.add(cid)

    save_json(TRACK_FILE, {'seen_comment_ids': list(seen)})
    log('triage_done', tracked_comments=len(seen))


if __name__ == '__main__':
    main()
