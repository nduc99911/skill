#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, List


def generate_ad_copy(product_name: str, insight_note: str) -> str:
    """Generate policy-safe ad copy in 2 angles.

    Guardrails applied by template design:
    - No unrealistic guarantees
    - No personal-attribute targeting
    - No extreme before/after claims
    """

    angles: List[Dict[str, str]] = [
        {
            "angle": "Pain Point",
            "hook": "Mỗi sáng mở Ads Manager mà tim đập nhanh vì sợ vít nhầm ngân sách?",
            "primary_text": (
                f"{product_name} được thiết kế cho người chạy quảng cáo muốn giảm thao tác thủ công mỗi ngày. "
                f"Từ insight thực tế: {insight_note}. "
                "Khóa học tập trung vào quy trình kiểm tra nhanh, checklist ra quyết định rõ ràng, "
                "và cách thiết lập nhịp tối ưu an toàn để bạn bớt quá tải khi quản camp."
            ),
            "headline": "Bớt áp lực check camp thủ công mỗi ngày",
            "cta": "Xem lộ trình học thử",
        },
        {
            "angle": "Proof/Benefit",
            "hook": "Không cần thêm công cụ phức tạp, bạn vẫn có thể kiểm soát camp gọn hơn mỗi ngày.",
            "primary_text": (
                f"Trong {product_name}, bạn nhận bộ khung thực chiến để theo dõi chỉ số theo mức ưu tiên, "
                "đi kèm các tình huống xử lý ngân sách thường gặp trong vận hành ads. "
                "Mục tiêu là giúp bạn ra quyết định có cơ sở dữ liệu, giảm sai sót do thao tác vội, "
                "và duy trì nhịp tối ưu ổn định hơn theo thời gian."
            ),
            "headline": "Quy trình tối ưu ads rõ ràng, dễ áp dụng",
            "cta": "Nhận outline khóa học",
        },
    ]

    lines: List[str] = [f"# Ad Copy Draft - {product_name}"]
    for i, a in enumerate(angles, 1):
        lines.append(f"\n## Angle {i}: {a['angle']}")
        lines.append(f"- Hook: {a['hook']}")
        lines.append(f"- Primary Text: {a['primary_text']}")
        lines.append(f"- Headline: {a['headline']}")
        lines.append(f"- CTA: {a['cta']}")

    return "\n".join(lines)


def generate_angles_struct(product_name: str, insight_note: str) -> List[Dict[str, str]]:
    """Structured angle list for downstream matrix builder."""
    _ = insight_note  # explicitly accepted for future dynamic templates
    return [
        {
            "angle": "Pain Point",
            "hook": "Mỗi sáng mở Ads Manager mà tim đập nhanh vì sợ vít nhầm ngân sách?",
            "primary_text": (
                f"{product_name} giúp bạn giảm thao tác thủ công và ra quyết định có checklist rõ ràng, "
                "để vận hành camp đỡ căng thẳng hơn mỗi ngày."
            ),
            "headline": "Bớt áp lực check camp thủ công",
            "cta": "Xem lộ trình học thử",
        },
        {
            "angle": "Proof/Benefit",
            "hook": "Không cần thêm tool rối, vẫn có thể tối ưu camp có hệ thống.",
            "primary_text": (
                f"{product_name} cung cấp khung theo dõi chỉ số và quy trình thao tác thực chiến, "
                "giúp giảm sai sót khi chỉnh ngân sách."
            ),
            "headline": "Tối ưu ads bằng quy trình rõ ràng",
            "cta": "Nhận outline khóa học",
        },
    ]
