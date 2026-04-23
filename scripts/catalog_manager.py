#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

ROOT = "/root/.openclaw/workspace"
CSV_PATH = os.path.join(ROOT, "data/products.csv")
CATALOG_PATH = os.path.join(ROOT, "data/catalog.json")
CONFIG_PATH = os.path.join(ROOT, "config/pages.json")

DEFAULT_PATTERN = r"^https?://([a-z0-9-]+\.)?shopee\.vn/(product|[A-Za-z0-9_./?=&%-]+)"


def load_rules():
    if not os.path.exists(CONFIG_PATH):
        return {
            "affiliate_link_pattern": DEFAULT_PATTERN,
            "affiliate_required_subdomains": ["s", "shopee"],
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    rules = cfg.get("global_rules", {})
    rules.setdefault("affiliate_link_pattern", DEFAULT_PATTERN)
    rules.setdefault("affiliate_required_subdomains", ["s", "shopee"])
    return rules


def validate_affiliate_link(link: str, rules: dict):
    if not link or not link.strip():
        return False, "empty_link"
    link = link.strip()

    try:
        parsed = urlparse(link)
    except Exception:
        return False, "malformed_url"

    if parsed.scheme not in ("http", "https"):
        return False, "invalid_scheme"

    host = (parsed.hostname or "").lower()
    if not host.endswith("shopee.vn"):
        return False, "invalid_domain"

    pattern = re.compile(rules.get("affiliate_link_pattern", DEFAULT_PATTERN), re.IGNORECASE)
    if not pattern.match(link):
        return False, "invalid_pattern"

    required_subdomains = [x.lower() for x in rules.get("affiliate_required_subdomains", [])]
    if required_subdomains:
        pre = host[:-len("shopee.vn")].strip(".")
        parts = pre.split(".") if pre else []
        if not any(req in parts for req in required_subdomains if req != "shopee"):
            if not ("shopee" in required_subdomains and host == "shopee.vn"):
                return False, "missing_required_affiliate_subdomain"

    return True, "ok"


def parse_blocks(raw: str):
    blocks = []
    current = {}

    def push_current():
        if current:
            blocks.append(current.copy())
            current.clear()

    for line in raw.splitlines():
        l = line.strip()
        if not l:
            continue
        lower = l.lower()

        # Start markers for a new block
        if lower.startswith("thêm sản phẩm") or re.match(r"^\d+[\.)]?$", l):
            push_current()
            continue

        if ":" not in l:
            continue

        k, v = l.split(":", 1)
        key = k.strip().lower()
        val = v.strip()

        if key in ("tên", "ten", "title"):
            current["title"] = val
        elif key in ("category", "danh mục", "danhmuc"):
            current["category"] = val
        elif key in ("link", "affiliate_link", "url"):
            current["affiliate_link"] = val
        elif key in ("priority", "priority_score", "độ ưu tiên", "do uu tien"):
            current["priority_score"] = val

    push_current()
    return [b for b in blocks if any(b.values())]


def load_catalog():
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # bootstrap from CSV once
    items = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append({
                    "product_id": row.get("product_id"),
                    "title": row.get("title"),
                    "category": row.get("category"),
                    "affiliate_link": row.get("affiliate_link"),
                    "priority_score": int(row.get("priority_score") or 5),
                    "status": row.get("status", "active"),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "source": "products.csv",
                })

    catalog = {"updated_at": datetime.now().isoformat(timespec="seconds"), "items": items}
    save_catalog(catalog)
    return catalog


def save_catalog(catalog):
    catalog["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def next_product_id(items):
    mx = 100
    for it in items:
        pid = (it.get("product_id") or "").strip().upper()
        m = re.match(r"BK(\d+)$", pid)
        if m:
            mx = max(mx, int(m.group(1)))
    return f"BK{mx+1}"


def add_from_chat(raw: str):
    rules = load_rules()
    catalog = load_catalog()
    items = catalog.get("items", [])
    blocks = parse_blocks(raw)

    results = []

    for b in blocks:
        title = (b.get("title") or "").strip()
        category = (b.get("category") or "").strip()
        link = (b.get("affiliate_link") or "").strip()
        priority_raw = (b.get("priority_score") or "5").strip()

        if not title:
            results.append({"status": "fail", "reason": "missing_title", "input": b})
            continue
        if not category:
            results.append({"status": "fail", "reason": "missing_category", "input": b})
            continue

        ok, reason = validate_affiliate_link(link, rules)
        if not ok:
            results.append({"status": "fail", "reason": f"affiliate_link_{reason}", "title": title})
            continue

        try:
            pr = int(priority_raw)
        except Exception:
            results.append({"status": "fail", "reason": "invalid_priority", "title": title})
            continue

        # upsert by title (case-insensitive)
        existing = next((x for x in items if x.get("title", "").strip().lower() == title.lower()), None)
        if existing:
            before = {
                "category": existing.get("category"),
                "affiliate_link": existing.get("affiliate_link"),
                "priority_score": existing.get("priority_score"),
            }
            existing["category"] = category
            existing["affiliate_link"] = link
            existing["priority_score"] = pr
            existing["status"] = "active"
            existing["updated_at"] = datetime.now().isoformat(timespec="seconds")
            existing["source"] = "chat"
            results.append({
                "status": "updated",
                "product_id": existing.get("product_id"),
                "title": title,
                "before": before,
            })
            continue

        pid = next_product_id(items)
        new_item = {
            "product_id": pid,
            "title": title,
            "category": category,
            "affiliate_link": link,
            "priority_score": pr,
            "status": "active",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": "chat",
        }
        items.append(new_item)
        results.append({"status": "pass", "product_id": pid, "title": title})

    catalog["items"] = items
    save_catalog(catalog)

    last5 = items[-5:]
    out = {
        "added": [r for r in results if r["status"] == "pass"],
        "updated": [r for r in results if r["status"] == "updated"],
        "failed": [r for r in results if r["status"] == "fail"],
        "skipped": [r for r in results if r["status"] == "skip"],
        "total_products": len(items),
        "last_5_products": [
            {
                "product_id": p.get("product_id"),
                "title": p.get("title"),
                "category": p.get("category"),
                "priority_score": p.get("priority_score"),
            }
            for p in last5
        ],
    }
    return out


def main():
    parser = argparse.ArgumentParser(description="Catalog manager for chat-based product input")
    parser.add_argument("command", choices=["add-chat"])
    parser.add_argument("--text", default="", help="Chat text containing one or many 'Thêm sản phẩm' blocks")
    args = parser.parse_args()

    if args.command == "add-chat":
        result = add_from_chat(args.text)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
