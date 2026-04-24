#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Dict


def load_books(csv_path: str) -> List[Dict[str, str]]:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f'Books source not found: {csv_path}')
    with p.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))
