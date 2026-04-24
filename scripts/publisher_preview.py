#!/usr/bin/env python3
import json
import os
import mimetypes
import requests
import struct
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


def _read_image_dimensions(path: str):
    with open(path, "rb") as f:
        head = f.read(32)
        if len(head) < 10:
            return None
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            f.seek(16)
            w, h = struct.unpack(">II", f.read(8))
            return int(w), int(h)
        if head[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", head[6:10])
            return int(w), int(h)
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marker_start = f.read(1)
                if not marker_start:
                    return None
                if marker_start != b"\xff":
                    continue
                marker = f.read(1)
                while marker == b"\xff":
                    marker = f.read(1)
                if marker in [b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"]:
                    _len = struct.unpack(">H", f.read(2))[0]
                    _precision = f.read(1)
                    h, w = struct.unpack(">HH", f.read(4))
                    return int(w), int(h)
                else:
                    seg_len_b = f.read(2)
                    if len(seg_len_b) != 2:
                        return None
                    seg_len = struct.unpack(">H", seg_len_b)[0]
                    f.seek(seg_len - 2, 1)
    return None


def validate_image_source(post: dict):
    image_type = (post.get("image_type") or "").strip()
    image_url = (post.get("image_url") or "").strip()

    if not image_type:
        return True, {
            "required": False,
            "source": "",
            "source_type": "",
            "status": "not_required",
        }

    # Cloudflare-only gate: local images are forbidden.
    if (post.get("image_local_path") or "").strip():
        return False, {
            "required": True,
            "source": (post.get("image_local_path") or "").strip(),
            "source_type": "local",
            "status": "cloudflare_only_local_forbidden",
        }

    if not image_url:
        return False, {
            "required": True,
            "source": "",
            "source_type": "url",
            "status": "missing_cloudflare_image_url",
        }

    try:
        r = requests.get(image_url, timeout=15, allow_redirects=True, stream=True)
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200:
            return False, {
                "required": True,
                "source": image_url,
                "source_type": "url",
                "status": f"http_{r.status_code}",
                "content_type": ct,
            }
        if not ct.startswith("image/"):
            return False, {
                "required": True,
                "source": image_url,
                "source_type": "url",
                "status": "url_not_image",
                "content_type": ct,
            }
        return True, {
            "required": True,
            "source": image_url,
            "source_type": "url",
            "status": "PASS",
            "content_type": ct,
        }
    except Exception as e:
        return False, {
            "required": True,
            "source": image_url,
            "source_type": "url",
            "status": "url_check_error",
            "error": str(e),
        }


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

    img_ok, img_val = validate_image_source(post)

    safe = bool(
        post.get("affiliate_link") == catalog_links.get(pid, "")
        and not post.get("affiliate_link", "").startswith("https://shopee.vn/product/")
        and "một cuốn cùng chủ đề" not in (post.get("caption") or "").lower()
        and "một cuốn giúp áp dụng thực tế" not in (post.get("caption") or "").lower()
        and img_ok
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
        "image_type": post.get("image_type", ""),
        "image_text": post.get("image_text", ""),
        "image_validation_status": img_val.get("status"),
        "image_source": img_val.get("source"),
        "image_source_type": img_val.get("source_type"),
        "image_content_type": img_val.get("content_type", ""),
        "image_file_size": img_val.get("file_size", 0),
        "image_dimensions": img_val.get("dimensions", ""),
        "source_file": "output/approved-plan.json",
        "safe_to_publish": safe,
        "reason_for_selection": "Bài approved gần nhất đã đến giờ của đúng page test được chỉ định; test_mode chỉ cho phép 1 bài duy nhất.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
