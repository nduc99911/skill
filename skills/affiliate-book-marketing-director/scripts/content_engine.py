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
    title = book.get('title', 'Book')
    mood = (book.get('category') or '').strip().lower()

    if any(k in mood for k in ['kinh doanh', 'tài chính', 'business']):
        style = 'luxury editorial desk mood, cinematic key light, premium paper texture, subtle gold accents'
    elif any(k in mood for k in ['tâm lý', 'healing', 'chữa lành']):
        style = 'soft atmospheric gradient, dreamy bokeh, warm film grain, gentle depth and calm emotional tone'
    elif any(k in mood for k in ['triết', 'philosophy']):
        style = 'moody museum-light ambiance, classical texture, deep contrast, contemplative and intellectual atmosphere'
    else:
        style = 'modern editorial background, layered composition, rich depth, nuanced texture, cinematic lighting'

    return (
        f"Create a visually rich 1:1 background for Vietnamese book content about '{title}'. "
        f"{style}. "
        f"Keep center area clean for text overlay, but preserve depth and visual interest around edges. "
        f"Ultra-detailed, high-quality, social-media ready, no people."
    )


def build_image_negative_prompt() -> str:
    return 'text, letters, words, typography, watermark, logo, signature, gibberish, artifacts'
