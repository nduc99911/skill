#!/usr/bin/env python3
from __future__ import annotations
import csv
import io
from pathlib import Path
from typing import List, Dict
import requests


def _load_books_from_text(csv_text: str) -> List[Dict[str, str]]:
    return list(csv.DictReader(io.StringIO(csv_text)))


def load_books(csv_path: str, csv_url: str = '') -> List[Dict[str, str]]:
    if csv_url:
        r = requests.get(csv_url, timeout=30)
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
        books = list(csv.DictReader(f))
    if not books:
        raise RuntimeError(f'Books CSV is empty: {csv_path}')
    return books
