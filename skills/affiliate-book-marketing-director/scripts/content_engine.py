#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, List


def pick_trend_for_book(book: Dict[str, str], trends: List[str]) -> str:
    title = (book.get('title') or '').lower()
    for t in trends:
        tl = t.lower()
        if any(k in tl for k in ['ai', 'công nghệ', 'kinh tế', 'tâm lý', 'xã hội']):
            return t
        if title and any(w in tl for w in title.split()[:2]):
            return t
    return ''


def build_caption(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    link = book.get('affiliate_link', '')
    if trend:
        return (
            f"Nhân sự kiện đang được quan tâm hôm nay: {trend}, mình thấy có một góc nhìn rất đáng ngẫm trong {title}.\n\n"
            f"Cuốn này không chỉ kể chuyện, mà giúp mình nhìn lại cách ra quyết định trong đời sống hàng ngày.\n\n"
            f"Nếu bạn muốn đọc sâu hơn về chủ đề này, mình để link ở bình luận nhé 👇"
        )
    return (
        f"Mình vừa đọc lại {title} và thấy đây là cuốn cực kỳ đáng để có trên kệ nếu bạn muốn nâng cấp tư duy mỗi ngày.\n\n"
        f"Điểm mình thích là viết dễ hiểu, áp dụng được ngay, không lý thuyết rườm rà.\n\n"
        f"Mình để link ở bình luận để bạn tham khảo nhé 👇"
    )


def build_image_text(book: Dict[str, str]) -> str:
    title = book.get('title', '').strip()
    if not title:
        return 'Đọc để hiểu mình\nvà sống sâu hơn'
    if len(title) > 30:
        return 'Một cuốn sách hay\nđổi góc nhìn sống'
    return f"{title}\nđáng đọc hôm nay"


def build_image_prompt(book: Dict[str, str], image_text: str) -> str:
    title = (book.get('title') or 'Book').strip()
    category = (book.get('category') or '').strip().lower()

    # Step 1: Visual metaphor (concrete objects, avoid abstract buzzwords)
    if any(k in category for k in ['khởi nghiệp', 'kinh doanh', 'tài chính', 'business']):
        subject = 'a small green sprout growing out of an old bronze coin, next to a vintage brass compass'
        setting = 'on a weathered wooden table over an ancient map with floating dust particles'
    elif any(k in category for k in ['chữa lành', 'healing', 'tâm lý', 'cảm xúc']):
        subject = 'a warm cup of tea with soft steam beside a glowing candle'
        setting = 'near a rainy window in a quiet dim room with gentle reflections'
    elif any(k in category for k in ['triết', 'philosophy', 'cổ nhân']):
        subject = 'a stone path leading to a distant archway under moonlight'
        setting = 'in a misty courtyard with subtle falling leaves and dramatic light rays'
    elif any(k in category for k in ['kỹ năng', 'phát triển', 'self-help']):
        subject = 'a paper airplane rising above layered geometric steps'
        setting = 'in a clean studio-like abstract space with directional light and depth'
    else:
        subject = 'a lone silhouette standing on a hill facing a glowing horizon'
        setting = 'in an abstract cinematic landscape with layered fog and soft light beams'

    # Step 2 + Step 3: explicit setting + mandatory artistic modifiers
    return (
        f"{subject}, {setting}, clean center area reserved for text overlay, no clutter. "
        f"Theme inspired by '{title}'. "
        f"hyperrealistic, highly detailed, cinematic lighting, 8k resolution, professional photography, "
        f"masterpiece, trending on artstation, depth of field"
    )


def build_image_negative_prompt() -> str:
    # Step 4: absolute negative prompt block
    return 'text, letters, words, font, typography, watermark, signature, people faces, messy, chaotic'
