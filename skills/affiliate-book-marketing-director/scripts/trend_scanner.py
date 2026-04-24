#!/usr/bin/env python3
from __future__ import annotations
import requests
from typing import List


def scan_trends(max_items: int = 10) -> List[str]:
    # Lightweight RSS scan (replace/extend later with richer sources)
    feeds = [
        'https://vnexpress.net/rss/tin-moi-nhat.rss',
        'https://dantri.com.vn/rss/home.rss',
    ]
    out = []
    for feed in feeds:
        try:
            r = requests.get(feed, timeout=20)
            if r.status_code == 200:
                txt = r.text
                parts = txt.split('<title>')
                for part in parts[1:]:
                    title = part.split('</title>')[0].strip()
                    if title and title.lower() not in ('tin mới nhất', 'dan tri'):
                        out.append(title)
        except Exception:
            continue
    # de-dup
    uniq = []
    seen = set()
    for t in out:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq[:max_items]
