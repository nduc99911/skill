#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, List, Tuple
import random

# Reserved for LLM-based generation mode (if enabled later).
# Keep high token budget to avoid truncation of long-form AIDA captions.
LLM_MAX_TOKENS = 1500


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


def _enforce_caption_length(caption: str, min_words: int = 250, max_words: int = 450) -> str:
    # Preserve paragraph formatting. Never collapse newlines.
    wc = _word_count(caption)
    if wc >= min_words:
        return caption

    filler_blocks = [
        (
            "Nhìn rộng hơn, giá trị của cuốn sách không nằm ở vài mẹo giao tiếp ngắn hạn, "
            "mà ở việc giúp bạn đổi cách tư duy khi làm việc với con người trong bối cảnh áp lực cao."
        ),
        (
            "Khi áp dụng đều đặn từng nguyên tắc vào công việc và cuộc sống, bạn sẽ thấy các cuộc đối thoại "
            "bớt căng thẳng, hiệu quả hợp tác tăng lên và quyết định trở nên sáng suốt hơn."
        ),
    ]
    out = caption
    i = 0
    while _word_count(out) < min_words:
        out += "\n\n" + filler_blocks[i % len(filler_blocks)]
        i += 1
    # Do not hard-trim by words to avoid cutting CTA/hashtags.
    return out


CONTENT_FRAMEWORKS = [
    'storytelling',
    'quote_reflection',
    'pros_cons_review',
    'trend_jacking',
]

# Prompt chuẩn hóa để LLM (nếu bật ở bước sau) luôn bám framework đã chọn.
FRAMEWORK_SYSTEM_PROMPT = (
    "Bạn là copywriter tiếng Việt cho fanpage sách. "
    "Bắt buộc viết theo đúng framework được truyền vào, không tự đổi framework. "
    "Giữ giọng tự nhiên, tránh sáo rỗng, không viết kiểu máy. "
    "Luôn có CTA mềm ở cuối và không spam hashtag."
)


def _pick_framework() -> str:
    return random.choice(CONTENT_FRAMEWORKS)


def _framework_storytelling(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    ideas = _split_core_ideas(book)
    opening = (
        f"Có một giai đoạn mình thấy đầu óc rối tung: làm nhiều nhưng lúc nào cũng có cảm giác bế tắc. "
        f"Mình đọc {title} không phải vì kỳ vọng phép màu, mà vì cần một cách nhìn lại bản thân cho rõ hơn."
    )
    body = (
        f"Điều làm mình dừng lại lâu nhất là ý này: {ideas[0]} "
        f"Mình thử áp dụng vào công việc hằng ngày và nhận ra các cuộc trao đổi bớt căng hơn hẳn.\n\n"
        f"Ý thứ hai mình tâm đắc là {ideas[1].lower()} "
        f"Khi mình bớt phản ứng nóng, người đối diện cũng mềm lại và hợp tác dễ hơn.\n\n"
        f"Cuối cùng là {ideas[2].lower()} "
        f"Nó giúp mình chuyển từ tư duy thắng-thua sang cùng giải quyết vấn đề, đỡ mệt đầu rất nhiều."
    )
    cta = "Nếu bạn cũng đang loay hoay như mình từng trải qua, thử đọc cuốn này một lần nhé. Link mình để ở bình luận 👇"
    return f"📖 [CHIA SẺ THẬT] Mình đã gỡ bế tắc thế nào nhờ {title}\n\n{opening}\n\n{body}\n\n{cta}\n\n{_hashtags(book, trend)}"


def _framework_quote_reflection(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    ideas = _split_core_ideas(book)
    quote = f'“{ideas[0]}”'
    body = (
        f"Câu này nghe tưởng đơn giản, nhưng trong đời sống hiện đại lại rất khó làm. "
        f"Mình thấy đa phần chúng ta phản ứng quá nhanh, nên mâu thuẫn thường đi xa hơn mức cần thiết.\n\n"
        f"Đọc {title}, mình nhận ra một điều: trước khi muốn người khác thay đổi, hãy chỉnh cách mình quan sát và đặt câu hỏi. "
        f"Khi làm vậy, chất lượng đối thoại tăng lên rõ rệt và các quyết định cũng bớt cảm tính.\n\n"
        f"Góc chiêm nghiệm cuối cùng là {ideas[2].lower()} "
        f"Đây không chỉ là kỹ năng giao tiếp, mà là cách sống bớt va đập trong một thế giới quá nhiều nhiễu loạn."
    )
    cta = "Nếu bạn thích những cuốn sách giúp mình sống chậm lại và nghĩ sâu hơn, đây là một lựa chọn rất đáng đọc. Link ở bình luận 👇"
    return f"🌿 [TRÍCH DẪN & CHIÊM NGHIỆM] {title}\n\n{quote}\n\n{body}\n\n{cta}\n\n{_hashtags(book, trend)}"


def _framework_pros_cons(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    ideas = _split_core_ideas(book)
    body = (
        f"✅ 3 điểm hay nhất:\n"
        f"- Dễ áp dụng vào đời sống: {ideas[0]}\n"
        f"- Tư duy thực tế, không lên gân: {ideas[1]}\n"
        f"- Giúp xây nền giao tiếp bền vững: {ideas[2]}\n\n"
        f"👤 Ai BẮT BUỘC nên đọc:\n"
        f"- Người đi làm thường xuyên phải phối hợp nhiều phòng ban\n"
        f"- Người đang muốn nâng kỹ năng giao tiếp và thuyết phục\n"
        f"- Người dễ bị cuốn vào tranh luận thắng-thua\n\n"
        f"⛔ Ai chưa cần đọc lúc này:\n"
        f"- Người chỉ tìm nội dung giải trí nhanh\n"
        f"- Người không có nhu cầu thay đổi cách làm việc với con người\n"
    )
    cta = f"Tóm lại, {title} đáng tiền nếu bạn muốn nâng cấp tư duy làm việc dài hạn. Link mình để ở bình luận 👇"
    return f"🧭 [REVIEW THỰC TẾ] {title} có đáng đọc không?\n\n{body}\n{cta}\n\n{_hashtags(book, trend)}"


def _framework_trend_jacking(book: Dict[str, str], trend: str) -> str:
    title = book.get('title', 'Cuốn sách này')
    ideas = _split_core_ideas(book)
    if not trend:
        trend = 'một vấn đề xã hội đang được bàn luận nhiều'
    body = (
        f"{trend.capitalize()} đang khiến nhiều người tranh luận vì ai cũng có lý lẽ riêng. "
        f"Nhưng nếu nhìn dưới góc của {title}, mình thấy trọng tâm không nằm ở việc ai đúng tuyệt đối, mà là cách chúng ta đối thoại để đi đến giải pháp.\n\n"
        f"3 bài học rút ra rất thực tế:\n"
        f"- {ideas[0]}\n"
        f"- {ideas[1]}\n"
        f"- {ideas[2]}\n\n"
        f"Nếu áp dụng được 3 ý này, bạn sẽ thấy chất lượng hợp tác trong công việc và đời sống cải thiện rõ rệt."
    )
    cta = "Muốn đọc bản đầy đủ để hiểu sâu hơn? Mình để link sách ở bình luận nhé 👇"
    return f"🔥 [BẺ LÁI LINH HOẠT] Từ chuyện '{trend}' nhìn về {title}\n\n{body}\n\n{cta}\n\n{_hashtags(book, trend)}"


def build_caption(book: Dict[str, str], trend: str) -> str:
    framework = _pick_framework()
    if framework == 'storytelling':
        caption = _framework_storytelling(book, trend)
    elif framework == 'quote_reflection':
        caption = _framework_quote_reflection(book, trend)
    elif framework == 'pros_cons_review':
        caption = _framework_pros_cons(book, trend)
    else:
        caption = _framework_trend_jacking(book, trend)

    # Keep caption length healthy while preserving structure.
    return _enforce_caption_length(caption, min_words=170, max_words=420)


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
