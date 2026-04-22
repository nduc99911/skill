import csv
import hashlib
import json
import os
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

ROOT = "/root/.openclaw/workspace"
DATA_PATH = os.path.join(ROOT, "data/products.csv")
CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
HISTORY_PATH = os.path.join(ROOT, "state/posting-history.json")
OUTPUT_PATH = os.path.join(ROOT, "output/daily-plan.json")

SHOPEE_PATTERN = re.compile(r"^https?://([a-z0-9-]+\.)?shopee\.vn/(product|[A-Za-z0-9_./?=&%-]+)", re.IGNORECASE)


def fingerprint_text(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()[:16]


def tokenize(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\sÀ-ỹ]", " ", text.lower())
    return {t for t in cleaned.split() if len(t) > 2}


def caption_similarity(a: str, b: str) -> float:
    # blend lexical overlap + sequence similarity
    ta, tb = tokenize(a), tokenize(b)
    jaccard = (len(ta & tb) / len(ta | tb)) if (ta or tb) else 0.0
    seq = SequenceMatcher(None, a, b).ratio()
    return 0.6 * seq + 0.4 * jaccard


def validate_affiliate_link(link: str) -> tuple[bool, str]:
    if not link or not link.strip():
        return False, "empty_link"
    link = link.strip()
    if "shopee.vn" not in link:
        return False, "invalid_domain"
    if not SHOPEE_PATTERN.match(link):
        return False, "invalid_pattern"
    return True, "ok"


def load_data():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    products = []
    errors = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") != "active":
                continue
            ok, reason = validate_affiliate_link(row.get("affiliate_link", ""))
            if not ok:
                errors.append({
                    "product_id": row.get("product_id"),
                    "error": f"affiliate_link_{reason}"
                })
                continue
            products.append(row)

    return config, products, history_data, errors


def parse_history_time(ts: str, tz: ZoneInfo) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except Exception:
        return None


def get_posted_products(history_data: dict, page_id: str, days: int, now_tz: datetime) -> set[str]:
    cutoff = now_tz - timedelta(days=days)
    posted = set()
    for entry in history_data.get("history", []):
        if entry.get("page_id") != page_id:
            continue
        dt = parse_history_time(entry.get("posted_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff:
            posted.add(entry.get("product_id"))
    return posted


def recent_post_types(history_data: dict, page_id: str, now_tz: datetime, lookback_days: int = 30) -> list[str]:
    cutoff = now_tz - timedelta(days=lookback_days)
    rows = []
    for entry in history_data.get("history", []):
        if entry.get("page_id") != page_id:
            continue
        dt = parse_history_time(entry.get("posted_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff:
            rows.append((dt, entry.get("post_type", "soft_content")))
    rows.sort(key=lambda x: x[0])
    return [t for _, t in rows]


def choose_post_type(page_cfg: dict, history_types: list[str], slot_index: int, global_rules: dict) -> tuple[str, dict]:
    allowed = page_cfg.get("allowed_post_types", ["soft_content", "direct_sell"])
    max_streak = page_cfg.get("max_direct_sell_streak", global_rules.get("max_direct_sell_streak_default", 2))
    min_soft_ratio = global_rules.get("min_soft_ratio", 0.4)
    min_direct_ratio = global_rules.get("min_direct_ratio", 0.3)

    recent_direct_streak = 0
    for t in reversed(history_types):
        if t == "direct_sell":
            recent_direct_streak += 1
        else:
            break

    count = Counter(history_types)
    total = max(1, len(history_types))
    soft_ratio = count.get("soft_content", 0) / total
    direct_ratio = count.get("direct_sell", 0) / total

    # candidate weights influenced by ratio gaps
    weights = {}
    for t in allowed:
        if t == "direct_sell":
            w = 1.0
            if recent_direct_streak >= max_streak:
                w = 0.0
            elif direct_ratio < min_direct_ratio:
                w = 2.2
            weights[t] = w
        elif t == "soft_content":
            w = 1.2
            if soft_ratio < min_soft_ratio:
                w = 2.2
            weights[t] = w
        else:
            weights[t] = 0.7

    # If all zero due to streak, force non-direct fallback
    if sum(weights.values()) <= 0:
        for t in allowed:
            if t != "direct_sell":
                return t, {
                    "rule_applied": "max_direct_sell_streak",
                    "recent_direct_streak": recent_direct_streak,
                    "soft_ratio": round(soft_ratio, 3),
                    "direct_ratio": round(direct_ratio, 3)
                }
        # no fallback available
        return allowed[0], {
            "rule_applied": "fallback_single_type",
            "recent_direct_streak": recent_direct_streak,
            "soft_ratio": round(soft_ratio, 3),
            "direct_ratio": round(direct_ratio, 3)
        }

    # weighted random selection
    items = list(weights.items())
    population = [k for k, _ in items]
    probs = [v for _, v in items]
    picked = random.choices(population, weights=probs, k=1)[0]
    return picked, {
        "rule_applied": "ratio_weighted_selection",
        "recent_direct_streak": recent_direct_streak,
        "soft_ratio": round(soft_ratio, 3),
        "direct_ratio": round(direct_ratio, 3),
        "weights": weights,
        "slot_index": slot_index
    }


def available_slots_for_plan(day: datetime, time_slots: list[str], now_tz: datetime) -> list[str]:
    avail = []
    for slot in time_slots:
        hh, mm = slot.split(":")
        dt = day.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if dt >= now_tz:
            avail.append(slot)
    return avail


def pick_product(products: list[dict], page_cfg: dict, blocked_product_ids: set[str]) -> dict | None:
    pri_cats = set(page_cfg.get("priority_categories", []))
    primary = [p for p in products if p.get("category") in pri_cats and p.get("product_id") not in blocked_product_ids]
    fallback = [p for p in products if p.get("product_id") not in blocked_product_ids]
    pool = primary if primary else fallback
    if not pool:
        return None

    pool.sort(key=lambda x: (int(x.get("priority_score", 5)), int(x.get("discount_percent", 0))), reverse=True)
    return random.choice(pool[: min(6, len(pool))])


def build_caption_templates(post_type: str, title: str, link: str, hashtags: str, page_name: str) -> list[str]:
    soft = [
        f"Đôi khi thứ mình cần không phải thêm một lời khuyên, mà là một cuốn sách đủ sâu để nhìn lại chính mình.\n\n{title} là cuốn như vậy: đọc chậm, ngẫm kỹ, rồi tự thấy nhẹ hơn.\n\nBạn có thể tham khảo tại đây: {link}\n{hashtags}\nlink affiliate",
        f"Có những ngày lòng nặng mà không gọi tên được. Những lúc như vậy, {title} thường giúp mình bình tâm lại và nhìn mọi thứ rõ hơn.\n\nNếu bạn cũng đang cần một khoảng lặng, có thể xem thử.\n{link}\n{hashtags}\nlink affiliate",
        f"Không phải cuốn nào cũng khiến mình dừng lại để suy nghĩ, nhưng {title} làm được điều đó.\n\nĐọc xong thấy cách mình đối diện cảm xúc cũng khác đi một chút.\n\nTham khảo: {link}\n{hashtags}\nlink affiliate",
    ]
    direct = [
        f"Nếu bạn muốn một cuốn sách dễ đọc nhưng áp dụng được ngay vào đời sống, {title} là lựa chọn đáng tiền.\n\nNội dung rõ, không dài dòng, phù hợp đọc mỗi ngày 15-20 phút.\n\nXem chi tiết: {link}\n{hashtags}\nlink affiliate",
        f"Nhiều bạn hỏi nên bắt đầu từ cuốn nào để vừa dễ đọc vừa có giá trị thực tế. Gợi ý hôm nay là {title}.\n\nĐây là cuốn mình thấy hợp để đọc và áp dụng ngay.\n\nLink tham khảo: {link}\n{hashtags}\nlink affiliate",
        f"Một cuốn sách tốt là cuốn khiến mình hành động ngay sau khi đọc. {title} là kiểu sách như vậy.\n\nNếu bạn đang cân nhắc mua, mình để link ở đây:\n{link}\n{hashtags}\nlink affiliate",
    ]
    listicle = [
        f"Gợi ý nhanh cho bạn đang muốn đọc để nâng chất lượng sống:\n1) {title}\n2) Một cuốn cùng chủ đề\n3) Một cuốn giúp áp dụng thực tế\n\nBắt đầu từ cuốn số 1 tại đây: {link}\n{hashtags}\nlink affiliate",
        f"Top lựa chọn hôm nay cho tệp {page_name}:\n- {title}\n- Một cuốn nền tảng\n- Một cuốn để ứng dụng\n\nBạn có thể xem cuốn đầu tại: {link}\n{hashtags}\nlink affiliate",
    ]
    if post_type == "soft_content":
        return soft + direct[:1] + listicle[:1]
    if post_type == "direct_sell":
        return direct + soft[:1] + listicle[:1]
    return listicle + soft[:2] + direct[:1]


def pick_caption(post_type: str, title: str, link: str, hashtags: str, page_name: str,
                 existing_captions: list[str], threshold: float) -> tuple[str, dict]:
    templates = build_caption_templates(post_type, title, link, hashtags, page_name)
    random.shuffle(templates)

    for c in templates:
        sims = [caption_similarity(c, x) for x in existing_captions] if existing_captions else [0.0]
        mx = max(sims) if sims else 0.0
        if mx < threshold:
            return c, {"max_similarity": round(mx, 4), "threshold": threshold, "template_count": len(templates)}

    # fallback: pick least similar
    best = min(templates, key=lambda t: max([caption_similarity(t, x) for x in existing_captions] or [0.0]))
    best_mx = max([caption_similarity(best, x) for x in existing_captions] or [0.0])
    return best, {"max_similarity": round(best_mx, 4), "threshold": threshold, "fallback": True, "template_count": len(templates)}


def generate_plan():
    config, products, history_data, product_errors = load_data()
    tz_name = config.get("global_rules", {}).get("timezone", "Asia/Ho_Chi_Minh")
    tz = ZoneInfo(tz_name)
    now_tz = datetime.now(tz)

    # schedule logic: avoid past slots; if all passed => next day
    today_slots_count = 0
    for p in config.get("pages", []):
        today_slots_count += len(available_slots_for_plan(now_tz, p.get("time_slots", []), now_tz))

    if today_slots_count == 0:
        plan_day = now_tz + timedelta(days=1)
        plan_date = plan_day.strftime("%Y-%m-%d")
        day_mode = "tomorrow_all_today_slots_passed"
    else:
        plan_day = now_tz
        plan_date = now_tz.strftime("%Y-%m-%d")
        day_mode = "today_future_slots_only"

    rules = config.get("global_rules", {})
    threshold = float(rules.get("avoid_similar_caption_threshold", 0.75))

    daily_plan = {
        "generated_at": now_tz.isoformat(),
        "timezone": tz_name,
        "schedule_day_mode": day_mode,
        "publish_mode": config.get("publish_mode", False),
        "date": plan_date,
        "errors": product_errors[:],
        "posts": []
    }

    existing_captions = []
    existing_fingerprints = set(
        h.get("caption_fingerprint")
        for h in history_data.get("history", [])
        if h.get("caption_fingerprint")
    )

    for page in config.get("pages", []):
        page_id = page["page_id"]
        cooldown = int(page.get("cooldown_days_same_product", rules.get("cooldown_days_same_product", 14)))
        blocked = get_posted_products(history_data, page_id, cooldown, now_tz)
        hist_types = recent_post_types(history_data, page_id, now_tz)

        slots = available_slots_for_plan(plan_day, page.get("time_slots", []), now_tz if plan_date == now_tz.strftime("%Y-%m-%d") else plan_day.replace(hour=0, minute=0, second=0, microsecond=0))
        slots = slots[: int(page.get("posts_per_day", len(slots)))]

        if not slots:
            daily_plan["errors"].append({
                "page_id": page_id,
                "error": "no_available_time_slots",
                "details": {"requested": page.get("time_slots", [])}
            })
            continue

        for i, slot in enumerate(slots):
            chosen_type, type_meta = choose_post_type(page, hist_types, i, rules)

            product = pick_product(products, page, blocked)
            if not product:
                daily_plan["errors"].append({
                    "page_id": page_id,
                    "error": "no_product_available_after_filters",
                    "details": {"cooldown_days": cooldown}
                })
                continue

            blocked.add(product["product_id"])
            hist_types.append(chosen_type)

            link_ok, link_reason = validate_affiliate_link(product.get("affiliate_link", ""))
            if not link_ok:
                daily_plan["errors"].append({
                    "page_id": page_id,
                    "product_id": product.get("product_id"),
                    "error": f"affiliate_link_{link_reason}"
                })
                continue

            hashtags = " ".join(page.get("hashtags", [])[:5])
            caption, cap_meta = pick_caption(
                chosen_type,
                product.get("title", ""),
                product.get("affiliate_link", ""),
                hashtags,
                page.get("page_name", ""),
                existing_captions,
                threshold,
            )

            fp = fingerprint_text(caption)
            if fp in existing_fingerprints:
                caption += "\n\nGợi mở thêm: hãy chọn một ý và áp dụng ngay hôm nay."
                fp = fingerprint_text(caption)
            existing_fingerprints.add(fp)
            existing_captions.append(caption)

            daily_plan["posts"].append({
                "page_id": page_id,
                "page_name": page["page_name"],
                "post_type": chosen_type,
                "product_id": product["product_id"],
                "product_title": product["title"],
                "scheduled_time": f"{plan_date} {slot}",
                "caption": caption,
                "affiliate_link": product["affiliate_link"],
                "status": "ready_to_publish",
                "meta": {
                    "caption_fingerprint": fp,
                    "publish_mode": config.get("publish_mode", False),
                    "post_type_logic": type_meta,
                    "caption_similarity": cap_meta,
                },
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(daily_plan, f, indent=2, ensure_ascii=False)

    return daily_plan


if __name__ == "__main__":
    plan = generate_plan()
    print(f"Generated plan with {len(plan['posts'])} posts. timezone={plan['timezone']} mode={plan['schedule_day_mode']}")
