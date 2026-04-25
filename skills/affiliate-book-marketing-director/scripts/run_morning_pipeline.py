#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import time
import fcntl
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import get_settings
from logger import log, log_error
from books_source import load_books
from trend_scanner import scan_trends
from content_engine import pick_trend_for_book, build_caption, build_image_text, build_image_prompt, build_image_negative_prompt
from cloudflare_api import CloudflareClient, CloudflareApiError
from meta_api import MetaClient, MetaApiError
from notifier import TelegramNotifier, format_post_success, format_post_error

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
except Exception:
    BlockingScheduler = None

ROOT = Path('/root/.openclaw/workspace')
STATE_FILE = ROOT / 'state' / 'affiliate_pipeline_state.json'
QUEUE_FILE = ROOT / 'state' / 'affiliate_publish_queue.json'
TMP_IMG_DIR = ROOT / 'data' / 'cloudflare_generated'
TMP_IMG_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_LOCK_FILE = ROOT / 'state' / 'affiliate_publish_queue.lock'


# PIPELINE_MODE:
# - build_queue: build queue only
# - dispatch_due: publish due queue items now (manual/one-shot)
# - schedule_day: build queue then run APScheduler triggers for today's items
PIPELINE_MODE = os.getenv('PIPELINE_MODE', 'build_queue').strip().lower()


def is_blank_link(link: str) -> bool:
    x = (link or '').strip()
    return (not x) or (x.lower() == 'none')


def load_state():
    if not STATE_FILE.exists():
        return {'last_publish_ts': 0}
    return json.loads(STATE_FILE.read_text(encoding='utf-8'))


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')


def load_queue():
    if not QUEUE_FILE.exists():
        return {'date': '', 'items': []}
    return json.loads(QUEUE_FILE.read_text(encoding='utf-8'))


def save_queue(q):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding='utf-8')


@contextmanager
def queue_file_lock():
    QUEUE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_LOCK_FILE.open('w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def reserve_due_item(now: datetime, test_page_id: str = '') -> dict | None:
    """Atomically pick one due queued item and mark it as processing."""
    with queue_file_lock():
        q = load_queue()
        items = q.get('items', [])
        for item in sorted(items, key=lambda x: x.get('publish_at', '')):
            if item.get('status') != 'queued':
                continue
            due_at = parse_queue_datetime(item.get('publish_at', ''), now)
            if due_at > now:
                continue
            if test_page_id and str(item.get('page_id', '')) != str(test_page_id):
                continue
            item['status'] = 'processing'
            item['processing_started_at'] = now.isoformat()
            save_queue(q)
            return item
    return None


def finalize_item(queue_id: str, status: str, payload: dict):
    """Atomically finalize an item from processing -> published/failed."""
    with queue_file_lock():
        q = load_queue()
        for item in q.get('items', []):
            if item.get('queue_id') == queue_id:
                item['status'] = status
                item.pop('processing_started_at', None)
                for k, v in payload.items():
                    item[k] = v
                break
        save_queue(q)


def resolve_pages(meta: MetaClient | None, cfg, dryrun=False):
    if meta:
        pages = meta.list_pages()
        if cfg.test_page_id:
            pages = [p for p in pages if str(p.get('id')) == str(cfg.test_page_id)]
        elif cfg.fb_page_id:
            pages = [p for p in pages if str(p.get('id')) == str(cfg.fb_page_id)]
    elif dryrun:
        pages = [{'id': 'dryrun_page_1', 'name': 'Dry Run Page 1', 'access_token': 'dryrun_page_token'}]
    else:
        raise SystemExit('META_ACCESS_TOKEN missing for live mode')

    if not pages:
        raise SystemExit('No page available from /me/accounts with current token/filter')
    return pages


def parse_publish_hhmm(book: dict, now: datetime) -> datetime:
    # Respect both publish_date and publish_time from sheet and always return full datetime.
    raw_date = (book.get('Ngày đăng') or book.get('ngày đăng') or book.get('publish_date') or '').strip()
    raw_time = (book.get('Giờ đăng') or book.get('gio_dang') or book.get('publish_time') or '').strip()

    target = now
    if raw_date:
        try:
            yyyy, mm, dd = raw_date.split('-', 2)
            target = target.replace(year=int(yyyy), month=int(mm), day=int(dd))
        except Exception:
            pass

    if not raw_time:
        return target.replace(second=0, microsecond=0)

    try:
        hh, mm = raw_time.split(':', 1)
        hh_i = int(hh)
        mm_i = int(mm)
        return target.replace(hour=hh_i, minute=mm_i, second=0, microsecond=0)
    except Exception:
        return target.replace(second=0, microsecond=0)


def parse_queue_datetime(value: str, fallback: datetime) -> datetime:
    """Parse queue publish_at into a timezone-aware full datetime object."""
    try:
        dt = datetime.fromisoformat((value or '').strip())
        if dt.tzinfo is None and fallback.tzinfo is not None:
            dt = dt.replace(tzinfo=fallback.tzinfo)
        return dt.replace(microsecond=0)
    except Exception:
        return fallback.replace(microsecond=0)


def build_daily_queue(cfg):
    tz = ZoneInfo(cfg.timezone)
    now = datetime.now(tz)
    day_key = now.strftime('%Y-%m-%d')
    weekday = now.weekday()
    # Temporarily disable Friday minigame by default; enable only when explicitly turned on.
    is_friday = (weekday == 4) and (os.getenv('ENABLE_FRIDAY_SPECIAL', '0') == '1')

    books = load_books(cfg.books_csv_path, cfg.books_csv_url)
    trends = scan_trends(max_items=20)

    meta = MetaClient(cfg.meta_access_token) if cfg.meta_access_token else None
    pages = resolve_pages(meta, cfg, dryrun=cfg.dry_run)

    page_map = {str(p.get('id')): p for p in pages}

    items = []
    seq = 0
    for book in books:
        row_page_id = str((book.get('page_id') or '').strip())

        if row_page_id:
            if row_page_id not in page_map:
                log_error('queue_row_skipped', 'sheet_page_id_not_accessible_or_filtered', row_page_id=row_page_id, row=book)
                continue
            target_pages = [page_map[row_page_id]]
        else:
            target_pages = pages

        for page in target_pages:
            page_id = str(page.get('id'))
            page_name = page.get('name', '')
            seq += 1
            publish_at = parse_publish_hhmm(book, now)
            if is_friday:
                caption = (
                    f"Minigame Thứ Sáu: Trích câu này, bạn đoán thuộc cuốn nào nhé?\n\n"
                    f"\"{book.get('quote', 'Hạnh phúc là hành trình, không phải đích đến.')}\"\n\n"
                    "Tag 2 người bạn và comment đáp án đúng để nhận quà bí mật 🎁"
                )
            else:
                trend = pick_trend_for_book(book, trends)
                caption = build_caption(book, trend)

            image_text = build_image_text(book)
            prompt = build_image_prompt(book, image_text)

            row_id = (book.get('stt') or book.get('id') or 'book').strip() if isinstance(book.get('stt') or book.get('id') or 'book', str) else str(book.get('stt') or book.get('id') or 'book')
            items.append({
                'queue_id': f"{day_key}_{page_id}_{row_id}_{seq}",
                'status': 'queued',
                'created_at': now.isoformat(),
                'publish_at': publish_at.isoformat(),
                'page_id': page_id,
                'page_name': page_name,
                'book': book,
                'caption': caption,
                'image_text': image_text,
                'image_prompt': prompt,
                'friday_mode': is_friday,
            })

    queue_doc = {'date': day_key, 'items': items}
    save_queue(queue_doc)
    log('morning_pipeline_queue_built', date=day_key, total_items=len(items), pages=len(pages), books=len(books), dry_run=cfg.dry_run)


def dispatch_due(cfg):
    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
    tz = ZoneInfo(cfg.timezone)

    queue_doc = load_queue()
    if not queue_doc.get('items'):
        log('morning_pipeline_dispatch_skip', reason='empty_queue')
        return

    meta = MetaClient(cfg.meta_access_token) if cfg.meta_access_token else None
    cf = CloudflareClient(cfg.cf_account_id, cfg.cf_api_token) if (cfg.cf_account_id and cfg.cf_api_token) else None

    pages = resolve_pages(meta, cfg, dryrun=cfg.dry_run)
    page_token_map = {str(p.get('id')): (p.get('access_token') or '').strip() for p in pages}

    page_ig_map = {}
    map_path = Path(cfg.page_ig_map_path)
    if map_path.exists():
        page_ig_map = json.loads(map_path.read_text(encoding='utf-8'))

    state = load_state()
    min_gap = cfg.min_publish_interval_minutes * 60

    while True:
        now = datetime.now(tz).replace(microsecond=0)

        # Log future queued items for observability
        for x in load_queue().get('items', []):
            if x.get('status') != 'queued':
                continue
            due_at = parse_queue_datetime(x.get('publish_at', ''), now)
            if due_at > now:
                log('morning_pipeline_skip_future_item', queue_id=x.get('queue_id'), page_id=x.get('page_id'), publish_at=due_at.isoformat(), current_time=now.isoformat())

        item = reserve_due_item(now, test_page_id=str(cfg.test_page_id) if cfg.test_page_id else '')
        if not item:
            break

        queue_id = item.get('queue_id', '')
        page_id = str(item.get('page_id', ''))
        page_name = item.get('page_name', '')

        page_token = page_token_map.get(page_id, '')
        if not cfg.dry_run and not page_token:
            finalize_item(queue_id, 'failed', {'error': 'missing_page_access_token'})
            log_error('morning_pipeline_dispatch_failed', 'missing_page_access_token', queue_id=queue_id, page_id=page_id, page_name=page_name)
            continue

        try:
            now_ts = time.time()
            wait_sec = (state.get('last_publish_ts', 0) + min_gap) - now_ts
            if wait_sec > 0:
                time.sleep(wait_sec)

            book = item.get('book', {})
            caption = item.get('caption', '')
            image_text = item.get('image_text', '')
            prompt = item.get('image_prompt', '')
            is_friday = bool(item.get('friday_mode'))

            tmp_file = TMP_IMG_DIR / f"{page_id}_{book.get('id','book')}_{int(time.time())}.png"
            image_url = ''
            image_disabled = False
            if cfg.dry_run and not cf:
                tmp_file.write_bytes(b'dryrun-image-bytes')
                image_url = 'https://example.com/dryrun-image.png'
            else:
                if not cf:
                    image_disabled = True
                else:
                    bg_bytes = cf.render_image(prompt, negative_prompt=build_image_negative_prompt())
                    image_bytes = cf.render_text_overlay(bg_bytes, image_text)
                    tmp_file.write_bytes(image_bytes)
                    try:
                        upload = cf.upload_image_public(image_bytes)
                        variants = upload.get('variants', [])
                        image_url = variants[0] if variants else ''
                    except Exception:
                        image_url = ''

            affiliate_link = (book.get('affiliate_link') or '').strip()

            if cfg.dry_run:
                fb_post_id = f"dryrun_{page_id}_{book.get('id','book')}"
                ig_id = f"dryrun_ig_{page_id}_{book.get('id','book')}"
                mode_note = 'dry_run_no_api_publish'
            else:
                if not meta:
                    raise MetaApiError('META_ACCESS_TOKEN missing for live publish')

                if image_disabled:
                    fb_resp = meta.create_feed_post(page_id, page_token, caption)
                    publish_path = 'fb_feed_text_fallback_no_cf_credentials'
                elif image_url:
                    fb_resp = meta.create_photo_post(page_id, page_token, caption, image_url)
                    publish_path = 'fb_photo_by_url'
                else:
                    fb_resp = meta.create_photo_post_from_file(page_id, page_token, caption, str(tmp_file))
                    publish_path = 'fb_photo_by_file_fallback'

                fb_post_id = fb_resp.get('post_id') or fb_resp.get('id', '')

                if (not is_friday) and (not is_blank_link(affiliate_link)) and fb_post_id:
                    meta.create_comment(fb_post_id, page_token, f"Link ưu đãi mình để bên dưới 👇\n{affiliate_link}")

                ig_id = ''
                ig_business_id = page_ig_map.get(page_id) or cfg.ig_business_id
                if ig_business_id and image_url:
                    ig_resp = meta.publish_instagram_media(ig_business_id, image_url, caption)
                    ig_id = ig_resp.get('id', '')
                mode_note = f'published:{publish_path}'

            finalize_item(queue_id, 'published', {
                'published_at': datetime.now(tz).isoformat(),
                'fb_post_id': fb_post_id,
                'ig_media_id': ig_id,
                'image_url': image_url,
            })

            state['last_publish_ts'] = time.time()
            save_state(state)

            log('morning_pipeline_posted', queue_id=queue_id, page_id=page_id, page_name=page_name,
                book_id=book.get('id', ''), title=book.get('title', ''), image_text=image_text,
                image_url=image_url, fb_post_id=fb_post_id, ig_media_id=ig_id,
                friday_mode=is_friday, mode=mode_note)

            if not cfg.dry_run and fb_post_id:
                try:
                    notifier.send(format_post_success(book.get('title', ''), page_name, fb_post_id))
                except Exception as ne:
                    log_error('telegram_notify_failed', str(ne), queue_id=queue_id, page_id=page_id, page_name=page_name)

        except (MetaApiError, CloudflareApiError, Exception) as e:
            finalize_item(queue_id, 'failed', {'error': str(e)})
            log_error('morning_pipeline_dispatch_failed', str(e), queue_id=queue_id, page_id=page_id, page_name=page_name)
            try:
                notifier.send(format_post_error((item.get('book', {}) or {}).get('title', ''), page_name, str(e)))
            except Exception as ne:
                log_error('telegram_notify_failed', str(ne), queue_id=queue_id, page_id=page_id, page_name=page_name)
            continue

    items = load_queue().get('items', [])
    queued_left = sum(1 for x in items if x.get('status') == 'queued')
    processing = sum(1 for x in items if x.get('status') == 'processing')
    published = sum(1 for x in items if x.get('status') == 'published')
    failed = sum(1 for x in items if x.get('status') == 'failed')
    log('morning_pipeline_dispatch_done', queued_left=queued_left, processing=processing, published=published, failed=failed, dry_run=cfg.dry_run)


def schedule_day(cfg):
    """Build queue once in the morning, then schedule exact-time post jobs for that day."""
    if BlockingScheduler is None:
        raise SystemExit('APScheduler not installed. Please install apscheduler in .venv_aff')

    build_daily_queue(cfg)

    tz = ZoneInfo(cfg.timezone)
    now = datetime.now(tz).replace(microsecond=0)
    q = load_queue()
    items = q.get('items', [])

    scheduler = BlockingScheduler(timezone=cfg.timezone)
    scheduled = 0
    for item in items:
        if item.get('status') != 'queued':
            continue
        due_at = parse_queue_datetime(item.get('publish_at', ''), now)
        # Schedule only today's jobs that are still upcoming.
        if due_at.date() != now.date() or due_at <= now:
            continue
        scheduler.add_job(
            dispatch_due,
            'date',
            run_date=due_at,
            kwargs={'cfg': cfg},
            id=f"dispatch_{item.get('queue_id')}",
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
        )
        scheduled += 1

    log('morning_pipeline_scheduler_started', mode='schedule_day', today=now.strftime('%Y-%m-%d'), scheduled_jobs=scheduled)
    if scheduled == 0:
        log('morning_pipeline_scheduler_no_jobs', reason='no_upcoming_items_today')
        return

    scheduler.start()


def main():
    cfg = get_settings()
    if PIPELINE_MODE == 'dispatch_due':
        dispatch_due(cfg)
    elif PIPELINE_MODE == 'schedule_day':
        schedule_day(cfg)
    else:
        build_daily_queue(cfg)


if __name__ == '__main__':
    main()
