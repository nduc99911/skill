#!/usr/bin/env python3
from __future__ import annotations
import csv
import io
from pathlib import Path
from typing import List, Dict
import requests


def _repair_mojibake(s: str) -> str:
    if not isinstance(s, str):
        return s
    out = s
    for _ in range(3):
        if 'Ã' not in out and 'Â' not in out and 'Ä' not in out and 'áº' not in out:
            break
        try:
            out = out.encode('latin1').decode('utf-8')
        except Exception:
            break
    return out


def _norm_key(k: str) -> str:
    return _repair_mojibake((k or '').strip()).lower()


def _normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    # Map VN headers -> canonical keys used by pipeline
    mapped = {}
    for k, v in row.items():
        nk = _norm_key(k)
        vv = _repair_mojibake((v or '').strip())
        mapped[nk] = vv

    def pick(*keys):
        for kk in keys:
            if kk in mapped and mapped[kk] != '':
                return mapped[kk]
        return ''

    out = dict(mapped)
    out['stt'] = pick('stt', 'index', 'no')
    out['page_id'] = pick('id page', 'page id', 'page_id', 'id fanpage', 'fanpage id')
    out['title'] = pick('tên sách', 'ten sach', 'title')
    out['affiliate_link'] = pick('link aff', 'link affiliate', 'affiliate_link', 'link')
    out['post_type'] = pick('loại bài', 'loai bai', 'post_type', 'type')
    out['publish_date'] = pick('ngày đăng', 'ngay dang', 'publish_date', 'date')
    out['publish_time'] = pick('giờ đăng', 'gio dang', 'publish_time', 'time')
    out['core_idea'] = pick('ý chính', 'y chinh', 'core_idea', 'idea')
    return out


def _load_books_from_text(csv_text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [_normalize_row(r) for r in reader]


def _normalize_google_sheet_csv_url(url: str) -> str:
    # Accept either publish CSV URL or normal /edit URL from Google Sheets.
    if 'docs.google.com/spreadsheets/d/' not in url:
        return url
    if '/export?' in url and 'format=csv' in url:
        return url
    try:
        sid = url.split('/spreadsheets/d/')[1].split('/')[0]
    except Exception:
        return url
    gid = '0'
    if 'gid=' in url:
        gid = url.split('gid=')[-1].split('&')[0].split('#')[0]
    return f'https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}'


def load_books(csv_path: str, csv_url: str = '') -> List[Dict[str, str]]:
    if csv_url:
        fetch_url = _normalize_google_sheet_csv_url(csv_url)
        r = requests.get(fetch_url, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f'Failed to fetch BOOKS_CSV_URL: {r.status_code}')
        books = _load_books_from_text(r.text)
        if not books:
            raise RuntimeError('BOOKS_CSV_URL returned empty CSV data')
        return books

    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f'Books source not found: {csv_path}')
    with p.open('r', encoding='utf-8') as f:
        books = [_normalize_row(r) for r in csv.DictReader(f)]
    if not books:
        raise RuntimeError(f'Books CSV is empty: {csv_path}')
    return books
