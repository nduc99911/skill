#!/usr/bin/env python3
from __future__ import annotations
import contextlib
import io
import os
import sys
from pathlib import Path

os.environ['MOCK_POST_CONTENT'] = 'Deal sốc hôm nay https://s.shopee.vn/7fXYZabc123 freeship tuỳ thời điểm'
os.environ['MOCK_SEND_SUCCESS'] = '1'
os.environ.setdefault('META_WEBHOOK_VERIFY_TOKEN', 'test_verify_token')

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from fastapi.testclient import TestClient
from webhook_server import app
from simulate_webhook import build_payload


def run_case(message: str, post_id: str, comment_id: str, customer_id: str):
    client = TestClient(app)
    payload = build_payload(message)
    payload['entry'][0]['changes'][0]['value']['post_id'] = post_id
    payload['entry'][0]['changes'][0]['value']['comment_id'] = comment_id
    payload['entry'][0]['changes'][0]['value']['from']['id'] = customer_id

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        resp = client.post('/webhook', json=payload)
    print(f'=== TEST_MESSAGE: {message} ===')
    print(f'HTTP {resp.status_code} {resp.text}')
    print(buf.getvalue().strip())
    print()


if __name__ == '__main__':
    run_case('cho mình xin link', '1055755737627000_122000000000000101', '122999999999999101', '700000000000101')
    run_case('giá bao nhiêu vậy shop', '1055755737627000_122000000000000102', '122999999999999102', '700000000000102')
    run_case('sđt mình 0912345678 chốt nha', '1055755737627000_122000000000000103', '122999999999999103', '700000000000103')
