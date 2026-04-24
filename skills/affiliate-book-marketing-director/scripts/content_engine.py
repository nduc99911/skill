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
    # SEO-friendly social visual style: consistent brand background for recognizability.
    return (
        f"Create a premium, consistent 1:1 social background for Vietnamese book brand content about '{title}'. "
        f"Style guide: dark blue to warm amber cinematic gradient, subtle paper texture, soft vignette, "
        f"clean center safe-area for headline text, elegant editorial lighting, high contrast, minimal noise. "
        f"Keep composition stable and brand-consistent across different posts. "
        f"No people, no objects competing with text, no clutter."
    )


def build_image_negative_prompt() -> str:
    return 'text, letters, words, typography, watermark, logo, signature, gibberish, artifacts'
