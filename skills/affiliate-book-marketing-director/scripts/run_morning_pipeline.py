#!/usr/bin/env python3
from __future__ import annotations
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import get_settings
from logger import log, log_error
from books_source import load_books
from trend_scanner import scan_trends
from content_engine import pick_trend_for_book, build_caption, build_image_text, build_image_prompt
from cloudflare_api import CloudflareClient, CloudflareApiError
from meta_api import MetaClient, MetaApiError

ROOT = Path('/root/.openclaw/workspace')
STATE_FILE = ROOT / 'state' / 'affiliate_pipeline_state.json'
TMP_IMG_DIR = ROOT / 'data' / 'cloudflare_generated'
TMP_IMG_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    if not STATE_FILE.exists():
        return {'last_publish_ts': 0}
    return json.loads(STATE_FILE.read_text(encoding='utf-8'))


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    cfg = get_settings()
    tz = ZoneInfo(cfg.timezone)
    now = datetime.now(tz)

    weekday = now.weekday()  # Monday=0 ... Sunday=6
    is_friday = weekday == 4

    books = load_books(cfg.books_csv_path)
    trends = scan_trends(max_items=20)
    log('morning_pipeline_start', books=len(books), trends=len(trends), is_friday=is_friday, dry_run=cfg.dry_run)

    meta = None
    cf = None
    if cfg.meta_access_token:
        meta = MetaClient(cfg.meta_access_token)
    if cfg.cf_account_id and cfg.cf_api_token:
        cf = CloudflareClient(cfg.cf_account_id, cfg.cf_api_token)

    if meta:
        pages = meta.list_pages()
        if cfg.fb_page_id:
            pages = [p for p in pages if str(p.get('id')) == str(cfg.fb_page_id)]
    elif cfg.dry_run:
        pages = [{'id': 'dryrun_page_1', 'name': 'Dry Run Page 1', 'access_token': 'dryrun_page_token'}]
    else:
        raise SystemExit('META_ACCESS_TOKEN missing for live mode')

    if not pages:
        raise SystemExit('No page available from /me/accounts with current token')

    # Optional mapping: {"<page_id>": "<ig_business_id>"}
    page_ig_map = {}
    map_path = Path(cfg.page_ig_map_path)
    if map_path.exists():
        page_ig_map = json.loads(map_path.read_text(encoding='utf-8'))

    state = load_state()
    min_gap = cfg.min_publish_interval_minutes * 60

    for page in pages:
        page_id = str(page.get('id'))
        page_name = page.get('name', '')
        page_token = (page.get('access_token') or '').strip()
        if not page_token:
            log_error('morning_pipeline_page_skip', 'missing_page_access_token', page_id=page_id, page_name=page_name)
            continue

        for i, book in enumerate(books, 1):
            try:
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

                if cfg.dry_run and not cf:
                    image_bytes = b'dryrun-image-bytes'
                    tmp_file = TMP_IMG_DIR / f"{page_id}_{book.get('id','book')}_{int(time.time())}.png"
                    tmp_file.write_bytes(image_bytes)
                    image_url = 'https://example.com/dryrun-image.png'
                else:
                    image_bytes = cf.render_image(prompt)
                    tmp_file = TMP_IMG_DIR / f"{page_id}_{book.get('id','book')}_{int(time.time())}.png"
                    tmp_file.write_bytes(image_bytes)

                    upload = cf.upload_image_public(image_bytes)
                    variants = upload.get('variants', [])
                    image_url = variants[0] if variants else ''
                    if not image_url:
                        raise CloudflareApiError('Cloudflare image upload returned no public variants URL')

                now_ts = time.time()
                wait_sec = (state.get('last_publish_ts', 0) + min_gap) - now_ts
                if wait_sec > 0:
                    time.sleep(wait_sec)

                affiliate_link = (book.get('affiliate_link') or '').strip()

                if cfg.dry_run:
                    fb_post_id = f"dryrun_{page_id}_{book.get('id','book')}"
                    ig_id = f"dryrun_ig_{page_id}_{book.get('id','book')}"
                    private_note = 'dry_run_no_api_publish'
                else:
                    fb_resp = meta.create_photo_post(page_id, page_token, caption, image_url)
                    fb_post_id = fb_resp.get('post_id') or fb_resp.get('id', '')
                    if (not is_friday) and affiliate_link and fb_post_id:
                        meta.create_comment(fb_post_id, page_token, f"Link ưu đãi mình để bên dưới 👇\n{affiliate_link}")

                    ig_id = ''
                    ig_business_id = page_ig_map.get(page_id) or cfg.ig_business_id
                    if ig_business_id:
                        ig_resp = meta.publish_instagram_media(ig_business_id, image_url, caption)
                        ig_id = ig_resp.get('id', '')
                    private_note = 'published'

                state['last_publish_ts'] = time.time()
                save_state(state)

                log(
                    'morning_pipeline_posted',
                    seq=i,
                    page_id=page_id,
                    page_name=page_name,
                    book_id=book.get('id', ''),
                    title=book.get('title', ''),
                    image_text=image_text,
                    image_url=image_url,
                    fb_post_id=fb_post_id,
                    ig_media_id=ig_id,
                    friday_mode=is_friday,
                    mode=private_note,
                )

            except (MetaApiError, CloudflareApiError, Exception) as e:
                log_error('morning_pipeline_failed', str(e), page_id=page_id, page_name=page_name, seq=i, book=book)
                continue

    log('morning_pipeline_done', pages=len(pages), dry_run=cfg.dry_run)


if __name__ == '__main__':
    main()
