#!/usr/bin/env python3
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = "/root/.openclaw/workspace"
APPROVED_PLAN_PATH = os.path.join(ROOT, "output/approved-plan.json")
PAGES_CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
PUBLISHER_CONFIG_PATH = os.path.join(ROOT, "config/publisher.json")
CATALOG_PATH = os.path.join(ROOT, "data/catalog.json")
PRODUCTS_CSV_PATH = os.path.join(ROOT, "data/products.csv")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_scheduled_time(s, tz):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=tz)


def load_catalog_links():
    links = {}
    if os.path.exists(CATALOG_PATH):
        d = load_json(CATALOG_PATH, {"items": []})
        for it in d.get("items", []):
            pid = it.get("product_id")
            lk = (it.get("affiliate_link") or "").strip()
            if pid and lk:
                links[str(pid)] = lk
    if os.path.exists(PRODUCTS_CSV_PATH):
        import csv
        with open(PRODUCTS_CSV_PATH, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                pid = row.get("product_id")
                lk = (row.get("affiliate_link") or "").strip()
                if pid and lk and str(pid) not in links:
                    links[str(pid)] = lk
    return links


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

    catalog_links = load_catalog_links()
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
    pid = str(post.get("product_id") or "")
    image_url = (post.get("image_url") or "").strip()
    image_local = (post.get("image_local_path") or "").strip()
    image_type = (post.get("image_type") or "").strip()
    image_source = image_url if image_url else image_local

    safe = bool(
        post.get("affiliate_link") == catalog_links.get(pid, "")
        and not post.get("affiliate_link", "").startswith("https://shopee.vn/product/")
        and "một cuốn cùng chủ đề" not in (post.get("caption") or "").lower()
        and "một cuốn giúp áp dụng thực tế" not in (post.get("caption") or "").lower()
        and (not image_type or bool(image_source))
    )

    out = {
        "page_name": post.get("page_name"),
        "facebook_page_id": post.get("page_id"),
        "scheduled_time": post.get("scheduled_time"),
        "post_key": post_key,
        "product_title": post.get("product_title"),
        "product_id": pid,
        "link_placement": post.get("link_placement"),
        "caption": post.get("caption"),
        "first_comment": post.get("first_comment", "") if post.get("link_placement") == "comment" else "",
        "affiliate_link_in_approved_plan": post.get("affiliate_link"),
        "affiliate_link_in_catalog": catalog_links.get(pid, ""),
        "image_type": image_type,
        "image_text": post.get("image_text", ""),
        "image_source": image_source,
        "source_file": "output/approved-plan.json",
        "safe_to_publish": safe,
        "reason_for_selection": "Bài approved gần nhất đã đến giờ của đúng page test được chỉ định; test_mode chỉ cho phép 1 bài duy nhất.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
