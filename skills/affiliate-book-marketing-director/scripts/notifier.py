#!/usr/bin/env python3
from __future__ import annotations
import requests


class NotifyError(RuntimeError):
    pass


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = (bot_token or '').strip()
        self.chat_id = str(chat_id or '').strip()

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, text: str) -> dict:
        if not self.enabled:
            return {'ok': False, 'skipped': True, 'reason': 'telegram_not_configured'}
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        r = requests.post(
            url,
            json={
                'chat_id': self.chat_id,
                'text': text,
                'disable_web_page_preview': True,
            },
            timeout=20,
        )
        try:
            data = r.json()
        except Exception:
            data = {'raw': r.text}
        if r.status_code >= 400 or not data.get('ok', False):
            raise NotifyError(f'Telegram send failed {r.status_code}: {data}')
        return data


def format_post_success(title: str, page_name: str, fb_post_id: str) -> str:
    post_link = f'https://fb.com/{fb_post_id}' if fb_post_id else 'N/A'
    return (
        '📢 [THÔNG BÁO ĐĂNG BÀI]\n\n'
        f'📖 Sách: {title or "(không rõ tên)"}\n\n'
        f'🚩 Page: {page_name or "(không rõ page)"}\n\n'
        f'🔗 Link bài: {post_link}\n\n'
        '✅ Trạng thái: Thành công'
    )


def format_post_error(title: str, page_name: str, error: str) -> str:
    return (
        '📢 [THÔNG BÁO ĐĂNG BÀI]\n\n'
        f'📖 Sách: {title or "(không rõ tên)"}\n\n'
        f'🚩 Page: {page_name or "(không rõ page)"}\n\n'
        '❌ Trạng thái: Lỗi\n\n'
        f'🧯 Error: {error}'
    )
