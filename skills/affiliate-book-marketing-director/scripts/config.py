#!/usr/bin/env python3
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class Settings:
    timezone: str = os.getenv('AFF_TIMEZONE', 'Asia/Ho_Chi_Minh')

    # Tokens are session/runtime only. Do not persist.
    meta_access_token: str = os.getenv('META_ACCESS_TOKEN', '')
    meta_ad_account_id: str = os.getenv('META_AD_ACCOUNT_ID', '')

    fb_page_id: str = os.getenv('FB_PAGE_ID', '')  # optional single-page override
    ig_business_id: str = os.getenv('IG_BUSINESS_ID', '')  # optional global IG account id
    page_ig_map_path: str = os.getenv('PAGE_IG_MAP_PATH', '/root/.openclaw/workspace/data/page_ig_map.json')

    cf_account_id: str = os.getenv('CF_ACCOUNT_ID', '')
    cf_api_token: str = os.getenv('CF_API_TOKEN', '')

    # Data source
    books_csv_path: str = os.getenv('BOOKS_CSV_PATH', '/root/.openclaw/workspace/data/books_today.sample.csv')
    books_csv_url: str = os.getenv('BOOKS_CSV_URL', '')
    test_page_id: str = os.getenv('TEST_PAGE_ID', '')
    dry_run: bool = os.getenv('DRY_RUN', '1') == '1'

    # Operational rules
    min_publish_interval_minutes: int = int(os.getenv('MIN_PUBLISH_INTERVAL_MINUTES', '60'))

    # Telegram notifier (optional)
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')


def get_settings() -> Settings:
    return Settings()
