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
    log('morning_pipeline_start', books=len(books), trends=len(trends), is_friday=is_friday)

    meta = MetaClient(cfg.meta_access_token)
    cf = CloudflareClient(cfg.cf_account_id, cfg.cf_api_token)

    state = load_state()
    min_gap = cfg.min_publish_interval_minutes * 60

    for i, book in enumerate(books, 1):
        try:
            if is_friday:
                # Friday minigame mode
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

            # Render Cloudflare
            image_bytes = cf.render_image(prompt)
            tmp_file = TMP_IMG_DIR / f"{book.get('id','book')}_{int(time.time())}.png"
            tmp_file.write_bytes(image_bytes)

            # Try public URL upload (preferred for cross-platform)
            upload = cf.upload_image_public(image_bytes)
            variants = upload.get('variants', [])
            image_url = variants[0] if variants else ''
            if not image_url:
                raise CloudflareApiError('Cloudflare image upload returned no public variants URL')

            # enforce min publish gap
            now_ts = time.time()
            wait_sec = (state.get('last_publish_ts', 0) + min_gap) - now_ts
            if wait_sec > 0:
                time.sleep(wait_sec)

            # FB
            fb_resp = meta.create_photo_post(cfg.fb_page_id, caption, image_url)
            fb_post_id = fb_resp.get('post_id') or fb_resp.get('id', '')

            # Affiliate link via first comment for non-friday and if link exists
            affiliate_link = (book.get('affiliate_link') or '').strip()
            if (not is_friday) and affiliate_link and fb_post_id:
                meta.create_comment(fb_post_id, f"Link ưu đãi mình để bên dưới 👇\n{affiliate_link}")

            # IG
            ig_resp = meta.publish_instagram_media(cfg.ig_business_id, image_url, caption)
            ig_id = ig_resp.get('id', '')

            state['last_publish_ts'] = time.time()
            save_state(state)

            log(
                'morning_pipeline_posted',
                seq=i,
                book_id=book.get('id', ''),
                title=book.get('title', ''),
                image_text=image_text,
                image_url=image_url,
                fb_post_id=fb_post_id,
                ig_media_id=ig_id,
                friday_mode=is_friday,
            )

        except (MetaApiError, CloudflareApiError, Exception) as e:
            log_error('morning_pipeline_failed', str(e), seq=i, book=book)
            continue

    log('morning_pipeline_done')


if __name__ == '__main__':
    main()
