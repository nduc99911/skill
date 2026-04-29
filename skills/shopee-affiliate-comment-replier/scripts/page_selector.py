#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import requests

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'config.json'
ENV_PATH = Path('/root/.openclaw/workspace/.env')
GRAPH_BASE = 'https://graph.facebook.com/v23.0'


def load_meta_token(cli_token: str) -> str:
    if cli_token:
        return cli_token.strip()
    token = (os.getenv('META_ACCESS_TOKEN') or '').strip()
    if token:
        return token
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
            if line.startswith('META_ACCESS_TOKEN='):
                return line.split('=', 1)[1].strip()
    return ''


def fetch_pages(user_token: str) -> list[dict]:
    resp = requests.get(
        f'{GRAPH_BASE}/me/accounts',
        params={
            'access_token': user_token,
            'fields': 'id,name,access_token,category',
            'limit': 200,
        },
        timeout=30,
    )
    data = resp.json()
    if resp.status_code >= 400:
        err = data.get('error', {}) if isinstance(data, dict) else {}
        raise RuntimeError(f"Meta API error {resp.status_code}: {err.get('message') or data}")
    return data.get('data', [])


def save_config(selected: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'selected_page': {
            'page_id': selected.get('id', ''),
            'page_name': selected.get('name', ''),
            'page_access_token': selected.get('access_token', ''),
            'category': selected.get('category', ''),
        }
    }
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def choose_page_interactive(pages: list[dict]) -> dict:
    if not pages:
        raise RuntimeError('Không tìm thấy Fanpage nào từ token này.')

    print('\n=== DANH SÁCH FANPAGE KHẢ DỤNG ===')
    for idx, page in enumerate(pages, 1):
        print(f"{idx}. {page.get('name','(no name)')} - {page.get('id','')}")

    while True:
        raw = input('\nNhập số để chọn Page muốn chạy skill: ').strip()
        if not raw.isdigit():
            print('Vui lòng nhập số hợp lệ.')
            continue
        chosen = int(raw)
        if 1 <= chosen <= len(pages):
            return pages[chosen - 1]
        print('Số vượt ngoài danh sách, bạn chọn lại giúp mình.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meta-token', default='')
    args = ap.parse_args()

    token = load_meta_token(args.meta_token)
    if not token:
        raise SystemExit('Không tìm thấy META_ACCESS_TOKEN. Hãy truyền --meta-token hoặc lưu trong .env')

    pages = fetch_pages(token)
    selected = choose_page_interactive(pages)
    save_config(selected)

    print('\n=== ĐÃ LƯU CẤU HÌNH PAGE ===')
    print(f"Tên Page : {selected.get('name','')}")
    print(f"ID Page  : {selected.get('id','')}")
    print(f"Config   : {CONFIG_PATH}")
    print('Đã lưu page_access_token vào config.json để webhook/reply dùng lại.')


if __name__ == '__main__':
    main()
