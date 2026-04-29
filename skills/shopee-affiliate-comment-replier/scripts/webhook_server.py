#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from typing import Any, Dict, List

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from facebook_api import load_selected_page_config, FacebookApiError, GRAPH_BASE
from reply_builder import build_and_send_reply

VERIFY_TOKEN = os.getenv('META_WEBHOOK_VERIFY_TOKEN', '')
PAGE_CONFIG = load_selected_page_config()
APP = FastAPI(title='Shopee Affiliate Comment Replier Webhook')


def log_event(event: str, **kwargs):
    payload = {'event': event, **kwargs}
    print(json.dumps(payload, ensure_ascii=False))


def fetch_post_content(post_id: str) -> str:
    mock_post_content = os.getenv('MOCK_POST_CONTENT', '').strip()
    if mock_post_content:
        return mock_post_content

    page = load_selected_page_config()
    resp = requests.get(
        f"{GRAPH_BASE}/{post_id}",
        params={
            'fields': 'message',
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
            f"Meta API {resp.status_code} | fetch_post_content post_id={post_id} | "
            f"message={err.get('message')} | type={err.get('type')} | code={err.get('code')} | "
            f"subcode={err.get('error_subcode')}"
        )

    return str(data.get('message') or '')


def is_page_authored_comment(change_value: Dict[str, Any]) -> bool:
    from_info = change_value.get('from', {}) or {}
    sender_id = str(from_info.get('id') or '')
    return sender_id == str(PAGE_CONFIG.get('page_id') or '')


def extract_comment_tasks(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    tasks: List[Dict[str, str]] = []
    for entry in payload.get('entry', []) or []:
        for change in entry.get('changes', []) or []:
            if change.get('field') != 'feed':
                continue
            value = change.get('value', {}) or {}
            if value.get('item') != 'comment':
                continue
            if value.get('verb') != 'add':
                continue
            if is_page_authored_comment(value):
                continue

            comment_id = str(value.get('comment_id') or value.get('post_id') or '')
            post_id = str(value.get('post_id') or '')
            customer_id = str((value.get('from') or {}).get('id') or '')
            customer_comment = str(value.get('message') or '')
            if not comment_id or not post_id or not customer_id:
                continue
            tasks.append({
                'comment_id': comment_id,
                'post_id': post_id,
                'customer_id': customer_id,
                'customer_comment': customer_comment,
            })
    return tasks


def process_comment_event(task: Dict[str, str]):
    comment_id = task['comment_id']
    post_id = task['post_id']
    customer_id = task['customer_id']
    customer_comment = task['customer_comment']

    try:
        post_content = fetch_post_content(post_id)
        result = build_and_send_reply(
            post_content=post_content,
            customer_comment=customer_comment,
            comment_id=comment_id,
            post_id=post_id,
            customer_id=customer_id,
            send_live=os.getenv('MOCK_SEND_SUCCESS', '').strip() != '1',
        )
        log_event('comment_processed', comment_id=comment_id, post_id=post_id, customer_id=customer_id, result=result)
    except Exception as e:
        log_event('comment_process_error', comment_id=comment_id, post_id=post_id, customer_id=customer_id, error=str(e))


@APP.get('/webhook')
def verify_webhook(hub_mode: str = '', hub_verify_token: str = '', hub_challenge: str = ''):
    if hub_mode == 'subscribe' and VERIFY_TOKEN and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail='Invalid verify token')


@APP.post('/webhook')
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    tasks = extract_comment_tasks(payload)

    for task in tasks:
        background_tasks.add_task(process_comment_event, task)

    log_event('webhook_received', task_count=len(tasks))
    return JSONResponse({'ok': True, 'accepted': len(tasks)})


app = APP
