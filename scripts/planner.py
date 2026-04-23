import csv
import hashlib
import json
import os
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = "/root/.openclaw/workspace"
DATA_PATH = os.path.join(ROOT, "data/products.csv")
CONFIG_PATH = os.path.join(ROOT, "config/pages.json")
HISTORY_PATH = os.path.join(ROOT, "state/posting-history.json")
OUTPUT_PATH = os.path.join(ROOT, "output/daily-plan.json")

DEFAULT_SHOPEE_PATTERN = re.compile(r"^https?://([a-z0-9-]+\.)?shopee\.vn/(product|[A-Za-z0-9_./?=&%-]+)", re.IGNORECASE)


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


def validate_affiliate_link(link: str, rules: dict) -> tuple[bool, str]:
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

    raw_pattern = rules.get("affiliate_link_pattern", "")
    pattern = re.compile(raw_pattern, re.IGNORECASE) if raw_pattern else DEFAULT_SHOPEE_PATTERN
    if not pattern.match(link):
        return False, "invalid_pattern"

    required_subdomains = rules.get("affiliate_required_subdomains", [])
    if required_subdomains:
        # host parts before base domain, e.g. s.shopee.vn => ["s"]
        pre = host[:-len("shopee.vn")].strip(".")
        parts = pre.split(".") if pre else []
        if not any(req.lower() in parts for req in required_subdomains if req.lower() != "shopee"):
            # allow root shopee.vn only when explicitly permitted via "shopee"
            if not ("shopee" in [r.lower() for r in required_subdomains] and host == "shopee.vn"):
                return False, "missing_required_affiliate_subdomain"

    return True, "ok"


def load_data():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    history_data.setdefault("history", [])
    history_data.setdefault("draft_history", [])

    rules = config.get("global_rules", {})

    products = []
    errors = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") != "active":
                continue
            ok, reason = validate_affiliate_link(row.get("affiliate_link", ""), rules)
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

    for entry in history_data.get("draft_history", []):
        if entry.get("page_id") != page_id:
            continue
        dt = parse_history_time(entry.get("planned_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff:
            rows.append((dt, entry.get("post_type", "soft_content")))

    rows.sort(key=lambda x: x[0])
    return [t for _, t in rows]


def recent_caption_candidates(history_data: dict, page_id: str, now_tz: datetime, lookback_days: int = 30) -> list[str]:
    cutoff = now_tz - timedelta(days=lookback_days)
    caps = []

    for entry in history_data.get("history", []):
        if entry.get("page_id") != page_id:
            continue
        dt = parse_history_time(entry.get("posted_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff and entry.get("caption"):
            caps.append(entry.get("caption"))

    for entry in history_data.get("draft_history", []):
        if entry.get("page_id") != page_id:
            continue
        dt = parse_history_time(entry.get("planned_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff and entry.get("caption"):
            caps.append(entry.get("caption"))

    return caps


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
    pri_cats = set(page_cfg.get("categories", page_cfg.get("priority_categories", [])))
    primary = [p for p in products if p.get("category") in pri_cats and p.get("product_id") not in blocked_product_ids]
    fallback = [p for p in products if p.get("product_id") not in blocked_product_ids]
    pool = primary if primary else fallback
    if not pool:
        return None

    pool.sort(key=lambda x: (int(x.get("priority_score", 5)), int(x.get("discount_percent", 0))), reverse=True)
    return random.choice(pool[: min(6, len(pool))])


def choose_caption_style() -> str:
    return random.choices(
        ["style_1_review", "style_2_direct", "style_3_listicle"],
        weights=[60, 25, 15],
        k=1,
    )[0]


def build_caption_templates(style_key: str, title: str, link_text: str, hashtags: str, page_name: str) -> list[str]:
    cta = f"Xem chi tiết tại đây 👇\n{link_text}" if "comment" not in link_text.lower() else "Link mình để bên dưới 👇\nLink ở comment 👇"

    style_1_review = [
        f"Có lúc mình mở mắt ra là đã thấy đầu óc đầy việc, nhưng đến cuối ngày lại chẳng xong được gì ra hồn.\n\nMình từng nghĩ do mình thiếu cố gắng. Sau này mới thấy vấn đề nằm ở cách mình giữ nhịp mỗi ngày, chứ không phải ở ý chí bốc lên nhất thời.\n\n{title} cho mình cảm giác như đang được một người đi trước chỉ lại từng nút thắt rất đời thường, đọc xong thấy dễ bắt đầu lại hơn.\n\nCuốn này hợp nếu bạn:\n- Hay trì hoãn dù biết việc quan trọng\n- Dễ mất nhịp sau vài ngày quyết tâm\n- Muốn có cách làm đều đặn, không quá sức\n\n{cta}\n{hashtags}",
        f"Bạn có bao giờ tự hứa từ mai sẽ sống kỷ luật hơn, rồi chỉ vài hôm sau mọi thứ lại quay về như cũ chưa?\n\nMình đã từng như vậy rất nhiều lần. Không phải vì lười, mà vì chưa có một cách đủ đơn giản để bám theo mỗi ngày.\n\n{title} là cuốn mình thích ở chỗ nói đúng cảm giác đó và chỉ ra hướng đi khá thực tế.\n\nCuốn này hợp nếu bạn:\n- Đang muốn lấy lại kỷ luật cá nhân\n- Thường bắt đầu tốt nhưng nhanh nản\n- Cần một lộ trình rõ để làm theo mỗi ngày\n\n{cta}\n{hashtags}",
        f"Dạo trước mình hay bị cuốn vào việc vặt, bận cả ngày nhưng vẫn thấy bản thân đứng yên.\n\nChỉ khi nhìn lại thói quen của mình, mình mới hiểu vì sao càng cố càng dễ mệt.\n\n{title} không nói chuyện xa vời, mà giúp mình sắp lại nhịp sống theo kiểu rất dễ ngấm.\n\nCuốn này hợp nếu bạn:\n- Luôn thấy bận nhưng không tiến nhiều\n- Muốn giảm phân tán và tập trung hơn\n- Cần thay đổi nhỏ nhưng hiệu quả rõ\n\n{cta}\n{hashtags}",
    ]

    style_2_direct = [
        f"Nếu bạn đang muốn sống kỷ luật hơn nhưng chưa biết bắt đầu từ đâu, đây là cuốn nên xem trước.\n\n{title} hợp với người dễ trì hoãn, hay mất tập trung, hoặc luôn thấy mình quyết tâm được vài hôm rồi hụt hơi.\n\nĐiểm đáng tiền là nội dung rõ, dễ áp dụng và không làm người đọc thấy ngợp.\n\nCuốn này hợp nếu bạn:\n- Cần kết quả thực tế trong vài tuần tới\n- Muốn bớt trì hoãn ngay trong công việc\n- Tìm một phương pháp dễ áp dụng hằng ngày\n\n{cta}\n{hashtags}",
        f"Cuốn này hợp với người cần một cách làm cụ thể để chỉnh lại thói quen sống.\n\n{title} đi thẳng vào chuyện nhiều người gặp hằng ngày: thiếu kỷ luật, khó duy trì, dễ bỏ dở giữa chừng.\n\nĐọc để có khung hành động rõ ràng, thay vì chỉ thấy hứng trong chốc lát.\n\nCuốn này hợp nếu bạn:\n- Đang mất tập trung trong công việc\n- Muốn siết lại thói quen ngủ/nghỉ/làm\n- Cần một lộ trình có thể bắt đầu ngay hôm nay\n\n{cta}\n{hashtags}",
        f"Bạn đang cần một cuốn sách dễ đọc nhưng tác động rõ vào thói quen hằng ngày?\n\n{title} phù hợp với người đi làm bận, người đang muốn lấy lại tập trung, hoặc ai đang cố xây lại nếp sống ổn định hơn.\n\nNội dung đi thẳng vào lợi ích thực tế, không vòng vo.\n\nCuốn này hợp nếu bạn:\n- Hay rơi vào vòng lặp trì hoãn\n- Muốn tăng hiệu suất mà không kiệt sức\n- Cần một phương pháp đủ rõ để duy trì lâu dài\n\n{cta}\n{hashtags}",
    ]

    style_3_listicle = [
        f"Nếu đang muốn chỉnh lại guồng sống, mình sẽ ưu tiên 3 kiểu sách này:\n\n- Sách giúp nhìn ra thói quen xấu đang kéo mình chậm lại\n- Sách cho cách làm đủ cụ thể để bắt đầu ngay\n- Sách đọc xong thấy muốn hành động chứ không chỉ thấy hay\n\nTrong 3 kiểu đó, {title} là cuốn mình sẽ xem trước.\n\nCuốn này hợp nếu bạn:\n- Đang muốn bắt đầu lại từ nền tảng\n- Cần một cuốn dễ đọc, dễ làm theo\n- Muốn chuyển từ biết sang hành động\n\n{cta}\n{hashtags}",
        f"Có 3 dấu hiệu cho thấy bạn nên đọc một cuốn về kỷ luật cá nhân ngay lúc này:\n\n- Việc nhỏ cũng dễ trì hoãn\n- Làm nhiều nhưng không thấy tiến\n- Muốn thay đổi nhưng không giữ được lâu\n\nNếu thấy mình ở trong đó, {title} là cuốn khá đáng để bắt đầu.\n\nCuốn này hợp nếu bạn:\n- Đang mất nhịp và muốn lấy lại sự ổn định\n- Cần một phương pháp rõ để theo mỗi ngày\n- Muốn thay đổi thật, không chỉ có động lực ngắn hạn\n\n{cta}\n{hashtags}",
    ]

    mapping = {
        "style_1_review": style_1_review,
        "style_2_direct": style_2_direct,
        "style_3_listicle": style_3_listicle,
    }
    return mapping.get(style_key, style_1_review)


def enforce_caption_depth(caption: str, style_key: str) -> str:
    # Rule: avoid short/flat captions. Keep a deeper, human tone.
    if len((caption or "").strip()) >= 520:
        return caption

    depth_by_style = {
        "style_1_review": "\n\nĐiều mình học được sau cùng là: thay đổi bền vững không đến từ một ngày bùng nổ, mà từ việc dám nhìn thẳng vào vấn đề của mình rồi chỉnh từng chút một.",
        "style_2_direct": "\n\nĐiểm khác biệt của cuốn này là cho bạn một hướng làm rõ ràng để áp dụng ngay, thay vì chỉ truyền động lực ngắn hạn rồi để mọi thứ quay về điểm cũ.",
        "style_3_listicle": "\n\nNếu chọn đúng một cuốn để bắt đầu lại trong giai đoạn này, mình vẫn ưu tiên cuốn trên vì nó giúp chuyển từ hiểu vấn đề sang hành động cụ thể.",
    }
    addon = depth_by_style.get(style_key, depth_by_style["style_1_review"])

    if "#" in caption:
        idx = caption.find("#")
        head = caption[:idx].rstrip()
        tail = caption[idx:]
        return f"{head}{addon}\n\n{tail}".strip()

    return f"{caption.rstrip()}{addon}".strip()


def pick_caption(title: str, link_text: str, hashtags: str, page_name: str,
                 existing_captions: list[str], threshold: float) -> tuple[str, dict]:
    style_key = choose_caption_style()
    templates = build_caption_templates(style_key, title, link_text, hashtags, page_name)
    random.shuffle(templates)

    for c in templates:
        c2 = enforce_caption_depth(c, style_key)
        sims = [caption_similarity(c2, x) for x in existing_captions] if existing_captions else [0.0]
        mx = max(sims) if sims else 0.0
        if mx < threshold:
            return c2, {
                "max_similarity": round(mx, 4),
                "threshold": threshold,
                "template_count": len(templates),
                "style_key": style_key,
            }

    best = min(templates, key=lambda t: max([caption_similarity(enforce_caption_depth(t, style_key), x) for x in existing_captions] or [0.0]))
    best = enforce_caption_depth(best, style_key)
    best_mx = max([caption_similarity(best, x) for x in existing_captions] or [0.0])
    return best, {
        "max_similarity": round(best_mx, 4),
        "threshold": threshold,
        "fallback": True,
        "template_count": len(templates),
        "style_key": style_key,
    }


def generate_first_comment(title: str, category: str, link: str, used_patterns: set[str]) -> str:
    candidates = [
        ("review", f"Xem review chi tiết cuốn {title} tại đây 👇"),
        ("discount", f"Link sách đang giảm giá cho {title} ở đây 👇"),
        ("preview", f"Xem nội dung cuốn {title} trước khi mua 👇"),
        ("quick", f"Mình để link tham khảo nhanh của {title} ở đây 👇"),
        ("below", f"Bạn có thể xem bản này của {title} tại link bên dưới 👇"),
    ]

    # add category flavor with unique pattern keys
    if category == "tam-ly":
        candidates.insert(0, ("tamly", f"Nếu bạn đang cần một cuốn dễ áp dụng về tâm lý, xem {title} ở đây 👇"))
    elif category == "tam-linh":
        candidates.insert(0, ("tamlinh", f"Cuốn này hợp để đọc chậm và ngẫm, xem {title} tại đây 👇"))
    elif category == "phat-trien-ban-than":
        candidates.insert(0, ("ptbt", f"Muốn nâng cấp thói quen mỗi ngày, xem {title} ở đây 👇"))
    elif category == "ky-nang-song":
        candidates.insert(0, ("kns", f"Cuốn này khá thực tế cho đời sống hằng ngày, xem {title} tại đây 👇"))

    opener = None
    picked_key = None
    for key, text in candidates:
        if key not in used_patterns:
            picked_key = key
            opener = text
            break
    if opener is None:
        picked_key, opener = random.choice(candidates)

    used_patterns.add(picked_key)
    tails = [
        "Mình đã đọc và thấy khá dễ ngấm.",
        "Bạn xem thử mục lục trước rồi quyết nhé.",
        "Đọc vài trang đầu là biết có hợp mình không.",
        "Nếu đúng gu, chốt luôn cho kịp đợt giá tốt.",
        "Hợp thì mua sớm để giữ mức giá này."
    ]
    tail = random.choice(tails)
    return f"{opener}\n{link}\n{tail}"


def build_image_concept(post_type: str, title: str, caption: str) -> dict:
    # Rule: always quote_image for cleaner, consistent visuals.
    image_type = "quote_image"

    quote_candidates = [
        "Sống rõ hơn\ntừ những điều nhỏ mỗi ngày",
        "Bình tĩnh lại\nđể nhìn đúng vấn đề",
        "Đổi tư duy trước\nđổi kết quả sau",
        "Đừng sống để vừa lòng tất cả",
    ]

    caption_l = (caption or "").lower()
    if "trì hoãn" in caption_l:
        image_text = "Đừng để trì hoãn\nđánh cắp ngày của bạn"
    elif "kỷ luật" in caption_l:
        image_text = "Kỷ luật mỗi ngày\nđổi lấy tự do lâu dài"
    elif "chữa lành" in caption_l or "mệt" in caption_l or "bình an" in caption_l:
        image_text = "Cho mình một khoảng lặng\nđể nhẹ lòng hơn"
    else:
        image_text = random.choice(quote_candidates)

    image_layout = {
        "background": "minimal, clean background tông be/trắng/tối nhẹ",
        "text_position": "text lớn ở giữa",
        "book_cover_position": "bìa sách nhỏ góc dưới phải",
        "lighting": "soft, calm"
    }

    image_prompt = (
        f"Minimalist quote image 1:1 cho bài về '{title}'. "
        f"Nền sạch màu trung tính, chữ lớn ở giữa (tiếng Việt): '{image_text}'. "
        f"Font hiện đại, dễ đọc trên mobile. Bìa sách nhỏ ở góc dưới phải. "
        f"Soft calm lighting, không rối, không watermark."
    )

    image_caption = (
        f"Quote image tối giản: nền trung tính, text lớn ở giữa '{image_text}', "
        f"bìa sách nhỏ góc dưới phải. Render bằng Cloudflare."
    )

    return {
        "image_type": image_type,
        "image_text": image_text,
        "image_layout": image_layout,
        "image_caption": image_caption,
        "image_prompt": image_prompt,
    }


def append_draft_history(history_data: dict, plan_posts: list[dict], now_tz: datetime):
    drafts = history_data.setdefault("draft_history", [])
    new_rows = []
    for p in plan_posts:
        row = {
            "page_id": p["page_id"],
            "product_id": p["product_id"],
            "post_type": p["post_type"],
            "planned_at": now_tz.isoformat(),
            "scheduled_time": p["scheduled_time"],
            "caption_fingerprint": p.get("meta", {}).get("caption_fingerprint"),
            "caption": p.get("caption", "")
        }
        new_rows.append(row)
    drafts.extend(new_rows)

    # Keep only recent draft history (45 days)
    cutoff = now_tz - timedelta(days=45)
    kept = []
    for d in drafts:
        dt = parse_history_time(d.get("planned_at", ""), now_tz.tzinfo)
        if dt and dt > cutoff:
            kept.append(d)
    history_data["draft_history"] = kept

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)


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

    existing_captions_global = []
    existing_fingerprints = set(
        h.get("caption_fingerprint")
        for h in (history_data.get("history", []) + history_data.get("draft_history", []))
        if h.get("caption_fingerprint")
    )

    placement_cycle = ["caption", "comment"]
    placement_idx = 0
    used_comment_openers = set()

    for page in config.get("pages", []):
        page_id = page.get("facebook_page_id") or page.get("page_id")
        cooldown = int(page.get("cooldown_days_same_product", rules.get("cooldown_days_same_product", 14)))
        blocked = get_posted_products(history_data, page_id, cooldown, now_tz)
        hist_types = recent_post_types(history_data, page_id, now_tz)
        page_recent_captions = recent_caption_candidates(history_data, page_id, now_tz, lookback_days=30)

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

            link_ok, link_reason = validate_affiliate_link(product.get("affiliate_link", ""), rules)
            if not link_ok:
                daily_plan["errors"].append({
                    "page_id": page_id,
                    "product_id": product.get("product_id"),
                    "error": f"affiliate_link_{link_reason}"
                })
                continue

            hashtags = " ".join(page.get("hashtags", [])[:5])
            link_placement = placement_cycle[placement_idx % len(placement_cycle)]
            placement_idx += 1

            if link_placement == "caption":
                link_text = product.get("affiliate_link", "")
                first_comment = ""
            else:
                link_text = "Link ở comment 👇"
                first_comment = generate_first_comment(
                    product.get('title', ''),
                    product.get('category', ''),
                    product.get('affiliate_link', ''),
                    used_comment_openers,
                )

            caption, cap_meta = pick_caption(
                product.get("title", ""),
                link_text,
                hashtags,
                page.get("page_name", ""),
                page_recent_captions + existing_captions_global,
                threshold,
            )

            fp = fingerprint_text(caption)
            if fp in existing_fingerprints:
                caption += "\n\nGợi mở thêm: hãy chọn một ý và áp dụng ngay hôm nay."
                fp = fingerprint_text(caption)
            existing_fingerprints.add(fp)
            existing_captions_global.append(caption)
            page_recent_captions.append(caption)

            image_concept = build_image_concept(chosen_type, product["title"], caption)

            daily_plan["posts"].append({
                "page_id": page_id,
                "internal_page_key": page.get("internal_page_key"),
                "page_name": page["page_name"],
                "post_type": chosen_type,
                "product_id": product["product_id"],
                "product_title": product["title"],
                "scheduled_time": f"{plan_date} {slot}",
                "caption": caption,
                "affiliate_link": product["affiliate_link"],
                "link_placement": link_placement,
                "first_comment": first_comment,
                "status": "ready_to_publish",
                "image_type": image_concept["image_type"],
                "image_text": image_concept["image_text"],
                "image_layout": image_concept["image_layout"],
                "image_caption": image_concept["image_caption"],
                "image_prompt": image_concept.get("image_prompt", ""),
                "meta": {
                    "caption_fingerprint": fp,
                    "publish_mode": config.get("publish_mode", False),
                    "post_type_logic": type_meta,
                    "caption_similarity": cap_meta,
                },
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(daily_plan, f, indent=2, ensure_ascii=False)

    append_draft_history(history_data, daily_plan["posts"], now_tz)

    return daily_plan


if __name__ == "__main__":
    plan = generate_plan()
    print(f"Generated plan with {len(plan['posts'])} posts. timezone={plan['timezone']} mode={plan['schedule_day_mode']}")
