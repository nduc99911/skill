#!/usr/bin/env python3
import json
import mimetypes
import os
import struct
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ROOT = "/root/.openclaw/workspace"
APPROVED_PLAN_PATH = os.path.join(ROOT, "output/approved-plan.json")
PAGES_CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
PUBLISHER_CONFIG_PATH = os.path.join(ROOT, "config/publisher.json")
TOKENS_PATH = os.path.join(ROOT, "config/page-tokens.json")
CATALOG_PATH = os.path.join(ROOT, "data/catalog.json")
PRODUCTS_CSV_PATH = os.path.join(ROOT, "data/products.csv")
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


def load_catalog_links():
    links = {}
    if os.path.exists(CATALOG_PATH):
        d = load_json(CATALOG_PATH, {"items": []})
        for it in d.get("items", []):
            pid = it.get("product_id")
            lk = (it.get("affiliate_link") or "").strip()
            if pid and lk:
                links[str(pid)] = lk

    # fallback CSV if missing in catalog
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


def is_placeholder_link(link: str) -> bool:
    return link.startswith("https://shopee.vn/product/")


def _read_image_dimensions(path: str):
    with open(path, "rb") as f:
        head = f.read(32)
        if len(head) < 10:
            return None

        # PNG
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            f.seek(16)
            w, h = struct.unpack(">II", f.read(8))
            return int(w), int(h)

        # GIF
        if head[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", head[6:10])
            return int(w), int(h)

        # JPEG
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
    image_local = (post.get("image_local_path") or "").strip()

    if not image_type:
        return True, {"required": False, "source": "", "source_type": "", "status": "not_required"}

    allowed_local_prefixes = [
        os.path.join(ROOT, "data", "cloudflare_generated") + os.sep,
        os.path.join(ROOT, "data", "quote_images_cf") + os.sep,
        os.path.join(ROOT, "data", "quote_images_tonight") + os.sep,
    ]

    if image_local:
        norm = os.path.abspath(image_local)
        if not any(norm.startswith(p) for p in allowed_local_prefixes):
            return False, {"required": True, "source": image_local, "source_type": "local", "status": "non_cloudflare_local_forbidden"}
        if not os.path.exists(norm):
            return False, {"required": True, "source": norm, "source_type": "local", "status": "local_missing"}
        size = os.path.getsize(norm)
        if size < 10 * 1024:
            return False, {"required": True, "source": norm, "source_type": "local", "status": "local_too_small", "file_size": size}
        mime, _ = mimetypes.guess_type(norm)
        if not mime or not mime.startswith("image/"):
            return False, {"required": True, "source": norm, "source_type": "local", "status": "local_not_image", "content_type": mime or "unknown"}
        dims = _read_image_dimensions(norm)
        if not dims:
            return False, {"required": True, "source": norm, "source_type": "local", "status": "local_dimensions_unreadable", "content_type": mime}
        return True, {"required": True, "source": norm, "source_type": "local", "status": "PASS", "content_type": mime, "file_size": size, "dimensions": f"{dims[0]}x{dims[1]}"}

    if image_url:
        try:
            r = requests.get(image_url, timeout=20, allow_redirects=True, stream=True)
            ct = (r.headers.get("content-type") or "").lower()
            if r.status_code != 200:
                return False, {"required": True, "source": image_url, "source_type": "url", "status": f"http_{r.status_code}", "content_type": ct}
            if not ct.startswith("image/"):
                return False, {"required": True, "source": image_url, "source_type": "url", "status": "url_not_image", "content_type": ct}
            return True, {"required": True, "source": image_url, "source_type": "url", "status": "PASS", "content_type": ct}
        except Exception as e:
            return False, {"required": True, "source": image_url, "source_type": "url", "status": "url_check_error", "error": str(e)}

    return False, {"required": True, "source": "", "source_type": "", "status": "missing_cloudflare_image_source"}


def quality_gate(post: dict, catalog_links: dict):
    caption = (post.get("caption") or "")
    link = (post.get("affiliate_link") or "").strip()
    pid = str(post.get("product_id") or "")

    forbidden = ["một cuốn cùng chủ đề", "một cuốn giúp áp dụng thực tế", "link affiliate"]
    for phrase in forbidden:
        if phrase in caption.lower():
            return False, f"caption_quality_blocked:{phrase}", None

    if is_placeholder_link(link):
        return False, "placeholder_link_blocked", None

    catalog_link = (catalog_links.get(pid) or "").strip()
    if not catalog_link:
        return False, "catalog_link_missing", None

    if link != catalog_link:
        return False, "affiliate_link_mismatch_vs_catalog", None

    if post.get("link_placement") == "caption" and catalog_link not in caption:
        return False, "caption_missing_catalog_link", None

    if post.get("link_placement") == "comment":
        first_comment = (post.get("first_comment") or "")
        if catalog_link not in first_comment:
            return False, "first_comment_missing_catalog_link", None

    image_ok, image_validation = validate_image_source(post)
    if not image_ok:
        return False, f"image_validation_failed:{image_validation.get('status')}", image_validation

    return True, "ok", image_validation


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


def clean_caption_for_publish(text: str) -> str:
    lines = (text or "").splitlines()
    kept = []
    for ln in lines:
        if ln.strip().lower() == "link affiliate":
            continue
        kept.append(ln)
    return "\n".join(kept).strip()


def publish_post(page_id, token, post):
    message = clean_caption_for_publish(post.get("caption", ""))
    image_type = (post.get("image_type") or "").strip()
    image_url = (post.get("image_url") or "").strip()
    image_local = (post.get("image_local_path") or "").strip()

    # publish with photo endpoint when image concept/source provided
    if image_type:
        if image_url:
            r = requests.post(
                f"{GRAPH_BASE}/{page_id}/photos",
                data={"caption": message, "url": image_url, "access_token": token},
                timeout=45,
            )
        elif image_local:
            if not os.path.exists(image_local):
                return False, None, f"image_local_not_found:{image_local}"
            with open(image_local, "rb") as img:
                r = requests.post(
                    f"{GRAPH_BASE}/{page_id}/photos",
                    data={"caption": message, "access_token": token},
                    files={"source": img},
                    timeout=60,
                )
        else:
            return False, None, "missing_image_source"

        if r.status_code != 200:
            return False, None, f"photo_post_failed:{r.text[:400]}"

        post_id = r.json().get("post_id") or r.json().get("id")
        if not post_id:
            return False, None, "photo_post_no_id"
    else:
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
    catalog_links = load_catalog_links()

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

        ok, reason, image_validation = quality_gate(post, catalog_links)
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
                    "error_reason": reason,
                    "image_validation": image_validation,
                }, ensure_ascii=False),
            )
            continue

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
            "image_type": post.get("image_type", ""),
            "image_source": post.get("image_url") or post.get("image_local_path") or "",
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
