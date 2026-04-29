#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from typing import Any, Dict, List

import requests

from facebook_api import load_selected_page_config, FacebookApiError, GRAPH_BASE
from reply_builder import build_and_send_reply


def log_event(event: str, **kwargs):
    print(json.dumps({'event': event, **kwargs}, ensure_ascii=False))


def fetch_recent_posts_with_comments(limit_posts: int = 10, limit_comments: int = 20) -> List[Dict[str, Any]]:
    page = load_selected_page_config()
    fields = f"id,message,comments.limit({limit_comments}){{id,message,from}}"
    resp = requests.get(
        f"{GRAPH_BASE}/{page['page_id']}/posts",
        params={
            'fields': fields,
            'limit': limit_posts,
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
            f"Meta API {resp.status_code} | fetch_recent_posts_with_comments | "
            f"message={err.get('message')} | type={err.get('type')} | code={err.get('code')} | "
            f"subcode={err.get('error_subcode')}"
        )

    return data.get('data', []) if isinstance(data, dict) else []


def process_posts(posts: List[Dict[str, Any]]):
    page = load_selected_page_config()
    for post in posts:
        try:
            post_id = str(post.get('id') or '')
            post_content = str(post.get('message') or '')
            comments = ((post.get('comments') or {}).get('data') or [])
            log_event('scan_post', page_id=page['page_id'], post_id=post_id, comment_count=len(comments))

            for comment in comments:
                try:
                    comment_id = str(comment.get('id') or '')
                    customer_comment = str(comment.get('message') or '')
                    from_info = comment.get('from') or {}
                    customer_id = str(from_info.get('id') or '')

                    if not comment_id or not customer_id:
                        log_event('skip_comment_missing_fields', post_id=post_id, comment_id=comment_id, customer_id=customer_id)
                        continue

                    if customer_id == str(page['page_id']):
                        log_event('skip_page_authored_comment', post_id=post_id, comment_id=comment_id)
                        continue

                    result = build_and_send_reply(
                        post_content=post_content,
                        customer_comment=customer_comment,
                        comment_id=comment_id,
                        post_id=post_id,
                        customer_id=customer_id,
                    )
                    log_event(
                        'comment_processed',
                        post_id=post_id,
                        comment_id=comment_id,
                        customer_id=customer_id,
                        customer_comment=customer_comment,
                        result=result,
                    )
                except Exception as comment_err:
                    log_event('comment_process_error', post_id=post_id, error=str(comment_err), comment=comment)
        except Exception as post_err:
            log_event('post_process_error', error=str(post_err), post=post)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit-posts', type=int, default=10)
    ap.add_argument('--limit-comments', type=int, default=20)
    args = ap.parse_args()

    try:
        posts = fetch_recent_posts_with_comments(
            limit_posts=max(1, args.limit_posts),
            limit_comments=max(1, args.limit_comments),
        )
        log_event('scan_started', post_count=len(posts), limit_posts=args.limit_posts, limit_comments=args.limit_comments)
        process_posts(posts)
        log_event('scan_finished', post_count=len(posts))
    except Exception as e:
        log_event('scan_failed', error=str(e))
        raise


if __name__ == '__main__':
    main()
