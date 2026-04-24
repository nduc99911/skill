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

    # Thematic cue: keep brand-consistent look but add subtle topic-related motifs.
    if any(k in category for k in ['tâm lý', 'chữa lành', 'healing']):
        motif = 'soft light beams, calm organic curves, subtle warm bokeh suggesting emotional healing'
    elif any(k in category for k in ['kinh doanh', 'tài chính', 'business']):
        motif = 'structured geometric layers, clean chart-like lines, premium executive desk mood'
    elif any(k in category for k in ['triết', 'philosophy', 'cổ nhân']):
        motif = 'classical paper texture, subtle ink brush traces, contemplative museum-like lighting'
    elif any(k in category for k in ['kỹ năng', 'phát triển', 'self-help']):
        motif = 'upward dynamic gradients, roadmap-like abstract paths, optimistic disciplined tone'
    else:
        motif = 'editorial abstract composition with subtle symbolic shapes related to learning and books'

    return (
        f"Create a premium, consistent 1:1 abstract thematic background for Vietnamese book content about '{title}'. "
        f"Style base: cinematic scene with soft depth, elegant color grading, clean center safe-area for headline text. "
        f"Visual direction: landscape elements or human silhouette/figure in artistic abstract style, emotionally evocative. "
        f"Add subtle thematic motif: {motif}. "
        f"Strict exclusions: no book, no bookshelf, no readable text, no letters, no logo, no watermark, no clutter."
    )


def build_image_negative_prompt() -> str:
    return 'text, letters, words, typography, watermark, logo, signature, gibberish, artifacts, book, books, bookshelf, book cover, magazine, newspaper'
