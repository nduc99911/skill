#!/usr/bin/env python3
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = "/root/.openclaw/workspace"
APPROVED_PLAN_PATH = os.path.join(ROOT, "output/approved-plan.json")
PAGES_CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
PUBLISHER_CONFIG_PATH = os.path.join(ROOT, "config/publisher.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_scheduled_time(s, tz):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=tz)


def main():
    pages_cfg = load_json(PAGES_CONFIG_PATH, {})
    publisher_cfg = load_json(PUBLISHER_CONFIG_PATH, {})
    approved = load_json(APPROVED_PLAN_PATH, {"posts": []})

    tz_name = pages_cfg.get("global_rules", {}).get("timezone", "Asia/Ho_Chi_Minh")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    test_page_id = str(publisher_cfg.get("test_page_id", "")).strip()
    if not test_page_id:
        print(json.dumps({"error": "test_page_id_empty"}, ensure_ascii=False, indent=2))
        return

    due = []
    for post in approved.get("posts", []):
        if post.get("status") != "approved":
            continue
        if str(post.get("page_id")) != test_page_id:
            continue
        st = parse_scheduled_time(post.get("scheduled_time"), tz)
        if st <= now:
            post_key = f"{test_page_id}|{post.get('scheduled_time')}|{post.get('product_id')}"
            due.append((st, post_key, post))

    due.sort(key=lambda x: x[0], reverse=True)
    if not due:
        print(json.dumps({"error": "no_due_approved_post_for_page", "page_id": test_page_id}, ensure_ascii=False, indent=2))
        return

    st, post_key, post = due[0]
    out = {
        "page_name": post.get("page_name"),
        "facebook_page_id": post.get("page_id"),
        "scheduled_time": post.get("scheduled_time"),
        "post_key": post_key,
        "product_title": post.get("product_title"),
        "link_placement": post.get("link_placement"),
        "caption": post.get("caption"),
        "first_comment": post.get("first_comment", "") if post.get("link_placement") == "comment" else "",
        "reason_for_selection": "Bài approved gần nhất đã đến giờ của đúng page test được chỉ định; test_mode chỉ cho phép 1 bài duy nhất.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
