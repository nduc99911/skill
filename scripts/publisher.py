#!/usr/bin/env python3
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ROOT = "/root/.openclaw/workspace"
APPROVED_PLAN_PATH = os.path.join(ROOT, "output/approved-plan.json")
PAGES_CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
PUBLISHER_CONFIG_PATH = os.path.join(ROOT, "config/publisher.json")
TOKENS_PATH = os.path.join(ROOT, "config/page-tokens.json")
PUBLISH_HISTORY_PATH = os.path.join(ROOT, "state/publish-history.json")
PUBLISH_LOG_PATH = os.path.join(ROOT, "state/publish.log")
PUBLISH_ERROR_LOG_PATH = os.path.join(ROOT, "state/publish_error.log")

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_log(path, msg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def parse_scheduled_time(s, tz):
    # expects 'YYYY-MM-DD HH:MM'
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=tz)


def token_audit(page_id, token):
    if not token or not token.strip():
        return False, "missing_token", {"token_valid": False, "token_expiry": "unknown", "permission_ok": False}

    # 1) token validity + mapping
    r = requests.get(
        f"{GRAPH_BASE}/{page_id}",
        params={"fields": "id,name", "access_token": token},
        timeout=20,
    )
    if r.status_code != 200:
        return False, "invalid_or_expired_or_wrong_page_token", {
            "token_valid": False,
            "token_expiry": "unknown",
            "permission_ok": False,
            "raw_error": r.text[:300],
        }

    data = r.json()
    if str(data.get("id")) != str(page_id):
        return False, "token_page_mismatch", {
            "token_valid": True,
            "token_expiry": "unknown",
            "permission_ok": False,
        }

    # 2) permission probe (best-effort): read tasks when available
    p = requests.get(
        f"{GRAPH_BASE}/{page_id}",
        params={"fields": "tasks", "access_token": token},
        timeout=20,
    )
    permission_ok = True
    tasks = []
    if p.status_code == 200:
        tasks = p.json().get("tasks", []) or []
        if tasks and "CREATE_CONTENT" not in tasks:
            permission_ok = False

    if not permission_ok:
        return False, "missing_create_content_permission", {
            "token_valid": True,
            "token_expiry": "unknown",
            "permission_ok": False,
            "tasks": tasks,
        }

    return True, "ok", {
        "token_valid": True,
        "token_expiry": "unknown",
        "permission_ok": True,
        "tasks": tasks,
    }


def publish_post(page_id, token, post):
    message = post.get("caption", "")
    r = requests.post(
        f"{GRAPH_BASE}/{page_id}/feed",
        data={"message": message, "access_token": token},
        timeout=30,
    )
    if r.status_code != 200:
        return False, None, f"post_create_failed:{r.text[:400]}"

    post_id = r.json().get("id")
    if not post_id:
        return False, None, "post_create_no_id"

    if post.get("link_placement") == "comment":
        first_comment = (post.get("first_comment") or "").strip()
        if first_comment:
            c = requests.post(
                f"{GRAPH_BASE}/{post_id}/comments",
                data={"message": first_comment, "access_token": token},
                timeout=30,
            )
            if c.status_code != 200:
                return False, post_id, f"first_comment_failed:{c.text[:400]}"

    return True, post_id, "ok"


def get_test_candidate(approved_posts, page_id, tz, now):
    # only approved posts from one page, sorted by scheduled_time desc
    rows = []
    for post in approved_posts:
        if post.get("status") != "approved":
            continue
        if str(post.get("page_id")) != str(page_id):
            continue
        try:
            st = parse_scheduled_time(post.get("scheduled_time"), tz)
        except Exception:
            continue
        if st <= now:
            post_key = f"{page_id}|{post.get('scheduled_time')}|{post.get('product_id')}"
            rows.append((st, post_key, post))
    rows.sort(key=lambda x: x[0], reverse=True)  # nearest past first
    return rows[0] if rows else None


def main():
    pages_cfg = load_json(PAGES_CONFIG_PATH, {})
    publisher_cfg = load_json(PUBLISHER_CONFIG_PATH, {
        "enabled": False,
        "test_mode": True,
        "test_page_id": "",
        "max_posts_per_run": 1,
    })
    tokens_cfg = load_json(TOKENS_PATH, {"pages": {}})
    approved = load_json(APPROVED_PLAN_PATH, {"posts": []})
    history = load_json(PUBLISH_HISTORY_PATH, {"published": []})

    tz_name = pages_cfg.get("global_rules", {}).get("timezone", "Asia/Ho_Chi_Minh")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    if not publisher_cfg.get("enabled", False):
        append_log(PUBLISH_LOG_PATH, "Publisher disabled in config/publisher.json (enabled=false).")
        return

    if not pages_cfg.get("publish_mode", False):
        append_log(PUBLISH_LOG_PATH, "Global publish_mode=false. Skip publishing.")
        return

    # strict safety gate: in test mode, require explicit confirmation flag
    if publisher_cfg.get("test_mode", True) and not publisher_cfg.get("test_confirmed", False):
        append_log(PUBLISH_LOG_PATH, "Test mode active but test_confirmed=false. Skip publishing.")
        return

    pages_by_id = {}
    for p in pages_cfg.get("pages", []):
        pid = p.get("facebook_page_id") or p.get("page_id")
        if pid:
            pages_by_id[str(pid)] = p

    published_keys = {x.get("post_key") for x in history.get("published", []) if x.get("post_key")}

    eligible = []

    if publisher_cfg.get("test_mode", True):
        # strict mode: only one page, one post
        test_page_id = str(publisher_cfg.get("test_page_id", "")).strip()
        if not test_page_id:
            append_log(PUBLISH_ERROR_LOG_PATH, "test_mode=true but test_page_id is empty. Abort.")
            return

        page = pages_by_id.get(test_page_id)
        if not page:
            append_log(PUBLISH_ERROR_LOG_PATH, f"test_page_id={test_page_id} not found in pages config. Abort.")
            return

        if not page.get("publish_enabled", False):
            append_log(PUBLISH_ERROR_LOG_PATH, f"test page {test_page_id} publish_enabled=false. Abort.")
            return

        candidate = get_test_candidate(approved.get("posts", []), test_page_id, tz, now)
        if not candidate:
            append_log(PUBLISH_LOG_PATH, f"No approved due post for test_page_id={test_page_id}.")
            return

        st, post_key, post = candidate
        requested_key = str(publisher_cfg.get("test_post_key", "")).strip()
        if requested_key and requested_key != post_key:
            append_log(PUBLISH_ERROR_LOG_PATH, f"Requested test_post_key mismatch. requested={requested_key} actual={post_key}. Abort.")
            return

        if post_key in published_keys:
            append_log(PUBLISH_LOG_PATH, f"Test post already published: {post_key}")
            return

        eligible = [(st, post_key, post, page)]
    else:
        for post in approved.get("posts", []):
            if post.get("status") != "approved":
                continue

            page_id = str(post.get("page_id"))
            page = pages_by_id.get(page_id)
            if not page:
                continue

            if not page.get("publish_enabled", False):
                continue

            st = parse_scheduled_time(post.get("scheduled_time"), tz)
            if st > now:
                continue

            post_key = f"{page_id}|{post.get('scheduled_time')}|{post.get('product_id')}"
            if post_key in published_keys:
                continue

            eligible.append((st, post_key, post, page))

        eligible.sort(key=lambda x: x[0])

    max_posts = 1 if publisher_cfg.get("test_mode", True) else int(publisher_cfg.get("max_posts_per_run", 1))
    to_publish = eligible[:max_posts]

    if not to_publish:
        append_log(PUBLISH_LOG_PATH, "No eligible approved posts to publish.")
        return

    for _, post_key, post, page in to_publish:
        page_id = str(post.get("page_id"))
        page_name = post.get("page_name", "")
        scheduled_time = post.get("scheduled_time", "")
        token = tokens_cfg.get("pages", {}).get(page_id, {}).get("page_access_token", "")

        ok, reason, audit = token_audit(page_id, token)
        if not ok:
            append_log(
                PUBLISH_ERROR_LOG_PATH,
                json.dumps({
                    "page_name": page_name,
                    "facebook_page_id": page_id,
                    "scheduled_time": scheduled_time,
                    "actual_publish_time": now.isoformat(),
                    "publish_status": "failed",
                    "post_id": None,
                    "error_reason": f"token_audit_failed:{reason}",
                    "token_audit": audit,
                }, ensure_ascii=False),
            )
            continue

        success, post_id, err = publish_post(page_id, token, post)
        row = {
            "post_key": post_key,
            "page_name": page_name,
            "facebook_page_id": page_id,
            "scheduled_time": scheduled_time,
            "actual_publish_time": now.isoformat(),
            "publish_status": "success" if success else "failed",
            "post_id": post_id,
            "error_reason": None if success else err,
            "link_placement": post.get("link_placement"),
            "product_id": post.get("product_id"),
            "product_title": post.get("product_title"),
        }

        if success:
            history.setdefault("published", []).append(row)
            post["status"] = "published"
            post.setdefault("meta", {})["published_post_id"] = post_id
            append_log(PUBLISH_LOG_PATH, json.dumps(row, ensure_ascii=False))
        else:
            append_log(PUBLISH_ERROR_LOG_PATH, json.dumps(row, ensure_ascii=False))

    save_json(PUBLISH_HISTORY_PATH, history)
    save_json(APPROVED_PLAN_PATH, approved)

    # auto-disable after one test publish attempt to prevent further posts
    if publisher_cfg.get("test_mode", True):
        publisher_cfg["enabled"] = False
        publisher_cfg["test_confirmed"] = False
        save_json(PUBLISHER_CONFIG_PATH, publisher_cfg)
        append_log(PUBLISH_LOG_PATH, "Test publish flow auto-disabled: publisher.enabled=false, test_confirmed=false.")


if __name__ == "__main__":
    main()
