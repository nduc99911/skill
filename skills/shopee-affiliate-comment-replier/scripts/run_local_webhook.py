#!/usr/bin/env python3
from __future__ import annotations
import os
import uvicorn

os.environ.setdefault('MOCK_POST_CONTENT', 'Deal sốc hôm nay https://s.shopee.vn/7fXYZabc123 freeship tuỳ thời điểm')
os.environ.setdefault('MOCK_SEND_SUCCESS', '1')
os.environ.setdefault('META_WEBHOOK_VERIFY_TOKEN', 'test_verify_token')

if __name__ == '__main__':
    uvicorn.run('webhook_server:app', host='127.0.0.1', port=8000, reload=False)
