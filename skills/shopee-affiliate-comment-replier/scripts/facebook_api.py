#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
import requests

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'config.json'
GRAPH_BASE = 'https://graph.facebook.com/v23.0'


class FacebookApiError(RuntimeError):
    pass


def load_selected_page_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FacebookApiError(f'Config not found: {CONFIG_PATH}')
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception as e:
        raise FacebookApiError(f'Invalid config JSON: {e}')

    page = data.get('selected_page') if isinstance(data, dict) else None
    if not isinstance(page, dict):
        raise FacebookApiError('selected_page missing in config.json')

    page_id = str(page.get('page_id') or '').strip()
    page_name = str(page.get('page_name') or '').strip()
    page_access_token = str(page.get('page_access_token') or '').strip()
    if not page_id or not page_access_token:
        raise FacebookApiError('page_id/page_access_token missing in config.json')

    return {
        'page_id': page_id,
        'page_name': page_name,
        'page_access_token': page_access_token,
    }


def create_comment_reply(comment_id: str, message: str) -> Dict[str, Any]:
    page = load_selected_page_config()
    resp = requests.post(
        f"{GRAPH_BASE}/{comment_id}/comments",
        data={
            'message': message,
            'access_token': page['page_access_token'],
        },
        timeout=30,
    )

    try:
        data = resp.json()
    except Exception:
        data = {'raw': resp.text}

    if resp.status_code >= 400:
        err = data.get('error', {}) if isinstance(data, dict) else {}
        raise FacebookApiError(
            f"Meta API {resp.status_code} | page={page['page_name']} ({page['page_id']}) | "
            f"message={err.get('message')} | type={err.get('type')} | code={err.get('code')} | "
            f"subcode={err.get('error_subcode')}"
        )

    reply_id = data.get('id', '') if isinstance(data, dict) else ''
    print(f"[OK] Replied to comment_id={comment_id} on page={page['page_name']} ({page['page_id']}) | reply_id={reply_id}")
    return data if isinstance(data, dict) else {'data': data}
