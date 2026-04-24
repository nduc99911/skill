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


def _split_core_ideas(book: Dict[str, str]) -> List[str]:
    raw = (book.get('core_idea') or book.get('ý chính') or '').strip()
    if not raw:
        return [
            'Biết lắng nghe để hiểu động cơ thật sự của người đối diện trước khi phản hồi.',
            'Tôn trọng thể diện và cảm xúc giúp giảm xung đột, tăng thiện chí hợp tác.',
            'Thuyết phục bằng lợi ích chung thay vì cố thắng thua trong từng cuộc tranh luận.',
        ]
    parts = [p.strip(' .;-') for p in raw.replace('•', '|').replace(';', '|').split('|') if p.strip()]
    if len(parts) >= 3:
        return parts[:3]
    # Expand when source is short
    seed = parts[0] if parts else raw
    return [
        f'Thấu hiểu tâm lý con người trong bối cảnh thực tế: {seed}.',
        'Điều chỉnh cách giao tiếp để giảm phản kháng và mở đường cho hợp tác dài hạn.',
        'Xây dựng niềm tin từng bước bằng sự chân thành, nhất quán và tôn trọng.',
    ]


def _hashtags(book: Dict[str, str], trend: str) -> str:
    title = (book.get('title') or 'SachHay').replace(' ', '')
    author = (book.get('author') or 'TacGia').replace(' ', '')
    topic = (book.get('category') or 'PhatTrienBanThan').replace(' ', '')
    trend_kw = ''.join(ch for ch in (trend or 'TrendHomNay') if ch.isalnum()) or 'TrendHomNay'
    return f"#{title} #{author} #{topic} #{trend_kw}"


def _word_count(text: str) -> int:
    return len([w for w in text.replace('\n', ' ').split(' ') if w.strip()])


def _enforce_caption_length(caption: str, min_words: int = 250, max_words: int = 400) -> str:
    wc = _word_count(caption)
    if wc >= min_words:
        if wc <= max_words:
            return caption
        # soft trim when too long
        words = caption.split()
        return ' '.join(words[:max_words])

    filler = (
        "\n\nNhìn rộng hơn, điểm giá trị của cuốn sách không nằm ở vài mẹo giao tiếp ngắn hạn, "
        "mà ở cách nó giúp bạn thay đổi hệ điều hành tư duy khi làm việc với con người. "
        "Khi bạn đọc chậm và áp dụng từng nguyên tắc vào bối cảnh thật như công việc, gia đình, "
        "đàm phán hay quản trị đội nhóm, bạn sẽ thấy hiệu quả bền hơn nhiều so với việc phản ứng theo cảm xúc tức thời."
    )
    out = caption
    while _word_count(out) < min_words:
        out += filler
    if _word_count(out) > max_words:
        words = out.split()
        out = ' '.join(words[:max_words])
    return out


def build_caption(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    ideas = _split_core_ideas(book)

    if trend:
        headline = f"🔥 [GÓC NHÌN HOT] TỪ {trend.upper()}: BÀI HỌC THỰC CHIẾN TRONG {title.upper()}"
        bridge = (
            f"Sự kiện {trend} đang khiến nhiều người tranh luận về lợi ích, trách nhiệm và cách các bên giữ chữ tín với nhau.\n"
            f"Điểm thú vị là khi đặt vào lăng kính của {title}, câu chuyện không còn là tin nóng nhất thời mà trở thành bài học dài hạn về tâm lý con người và nghệ thuật hợp tác."
        )
    else:
        headline = f"💡 [ĐỪNG ĐỢI HỐI TIẾC] {title.upper()} VÀ 3 BÀI HỌC GIÚP BẠN RA QUYẾT ĐỊNH CHẮC TAY HƠN"
        bridge = (
            f"Nhiều người giỏi chuyên môn nhưng vẫn trả giá đắt vì giao tiếp sai thời điểm, sai ngữ cảnh và sai kỳ vọng.\n"
            f"{title} cho mình một góc nhìn rất tỉnh: muốn đi xa, hãy hiểu tâm lý người đối diện trước khi cố gắng thay đổi họ."
        )

    body = (
        f"📌 Bài học 1: {ideas[0]}\n"
        f"👉 Ở đời thực, phần lớn mâu thuẫn leo thang vì ai cũng muốn được công nhận ngay lập tức. "
        f"Khi bạn chủ động lắng nghe sâu hơn một nhịp, cuộc nói chuyện chuyển từ thế đối đầu sang thế cùng giải quyết vấn đề. "
        f"Đây là kỹ năng cực hữu ích trong quản lý đội nhóm, chăm sóc khách hàng và cả quan hệ gia đình.\n\n"
        f"📌 Bài học 2: {ideas[1]}\n"
        f"👉 Sự tôn trọng không phải phép lịch sự bề mặt, mà là đòn bẩy giúp giữ thể diện và cảm xúc của đối phương. "
        f"Trong môi trường áp lực cao, người biết giữ nhịp bình tĩnh thường giành lợi thế lâu dài vì họ bảo toàn được niềm tin. "
        f"Một quyết định đúng nhưng cách nói sai có thể phá hỏng cả quan hệ hợp tác nhiều năm.\n\n"
        f"📌 Bài học 3: {ideas[2]}\n"
        f"👉 Thuyết phục bền vững không nằm ở việc nói thắng, mà ở việc thiết kế một phương án để hai bên cùng thấy lợi ích. "
        f"Khi bạn chuyển từ tư duy thắng-thua sang cùng-thắng, sức nặng lời nói tăng lên rõ rệt và khả năng chốt kết quả cũng cao hơn. "
        f"Đó là lý do cuốn sách này vẫn còn nguyên giá trị trong thời đại biến động nhanh và cạnh tranh khốc liệt."
    )

    cta = (
        "Nếu bạn đang muốn nâng cấp kỹ năng giao tiếp, thuyết phục và xây dựng ảnh hưởng một cách bền vững, đây là cuốn rất đáng sở hữu.\n"
        "Mời bạn xem link mua sách chính hãng giá ưu đãi mình ghim ở dưới phần bình luận nhé 👇"
    )

    caption = f"{headline}\n\n{bridge}\n\n{body}\n\n{cta}\n\n{_hashtags(book, trend)}"
    return _enforce_caption_length(caption, min_words=250, max_words=400)


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
