#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Dict, List


def generate_approval_packet(
    campaign_name: str,
    daily_budget: int,
    adset_name: str,
    ads_list: List[Dict[str, Any]],
) -> str:
    """Generate a human-readable approval packet in Markdown.

    This packet must be shown to user before any future write action.
    """
    lines: List[str] = [
        "# 🧾 Approval Packet - Meta Ads Draft",
        "",
        "## Tóm tắt Draft",
        f"- Campaign: **{campaign_name}**",
        f"- Ad Set: **{adset_name}**",
        f"- Ngân sách ngày: **{daily_budget:,}**",
        f"- Số mẫu quảng cáo dự kiến: **{len(ads_list)}**",
        "- Trạng thái bắt buộc: **PAUSED**",
        "",
        "## Cảnh báo an toàn",
        "- Tuyệt đối chưa publish live ở bước này.",
        "- Đây chỉ là gói chờ duyệt trước khi gọi API write.",
        "",
        "## Danh sách Ads dự kiến",
        "| # | Ad Name | Headline | CTA | Status |",
        "|---|---|---|---|---|",
    ]

    for i, ad in enumerate(ads_list, 1):
        ad_name = str(ad.get("ad_name", f"Ad_{i}"))
        headline = str(ad.get("headline", "-")).replace("|", "\\|")
        cta = str(ad.get("cta", "-")).replace("|", "\\|")
        lines.append(f"| {i} | {ad_name} | {headline} | {cta} | PAUSED |")

    lines.append("\n✅ Chờ người dùng duyệt trước khi cho phép gọi POST API.")
    return "\n".join(lines)


def build_meta_payloads(
    campaign_name: str,
    daily_budget: int,
    adset_name: str,
    page_id: str,
    ads_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build Meta payload drafts (MVP: return payloads only, no API call)."""

    campaign_payload = {
        "name": campaign_name,
        "objective": "OUTCOME_SALES",
        "status": "PAUSED",
        "special_ad_categories": [],
    }

    adset_payload = {
        "name": adset_name,
        "daily_budget": int(daily_budget),
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "status": "PAUSED",
    }

    ad_payloads: List[Dict[str, Any]] = []
    for i, ad in enumerate(ads_list, 1):
        ad_name = ad.get("ad_name", f"Ad_{i}")
        message = ad.get("primary_text", "")
        headline = ad.get("headline", "")
        cta = ad.get("cta", "LEARN_MORE")

        ad_payloads.append(
            {
                "name": ad_name,
                "status": "PAUSED",
                "creative": {
                    "object_story_spec": {
                        "page_id": str(page_id),
                        "link_data": {
                            "message": message,
                            "name": headline,
                            "call_to_action": {"type": cta},
                        },
                    }
                },
            }
        )

    return {
        "campaign": campaign_payload,
        "adset": adset_payload,
        "ads": ad_payloads,
        "mvp_mode": "draft_only_no_post",
    }


if __name__ == "__main__":
    # End-to-end test data (Phase 5 MVP)
    campaign_name = "Draft_OpenClaw_Test"
    daily_budget = 500000
    adset_name = "Broad_VN"
    page_id = "123456789"

    ads_list = [
        {
            "ad_name": "Ad_Angle_PainPoint",
            "primary_text": "Bạn đang mệt vì phải check camp thủ công mỗi ngày?",
            "headline": "Giảm áp lực vận hành Ads mỗi sáng",
            "cta": "LEARN_MORE",
        },
        {
            "ad_name": "Ad_Angle_Proof",
            "primary_text": "Áp dụng checklist tối ưu để giảm sai sót khi chỉnh ngân sách.",
            "headline": "Quy trình Ads rõ ràng, dễ triển khai",
            "cta": "SIGN_UP",
        },
    ]

    approval_md = generate_approval_packet(
        campaign_name=campaign_name,
        daily_budget=daily_budget,
        adset_name=adset_name,
        ads_list=ads_list,
    )

    payloads = build_meta_payloads(
        campaign_name=campaign_name,
        daily_budget=daily_budget,
        adset_name=adset_name,
        page_id=page_id,
        ads_list=ads_list,
    )

    print(approval_md)
    print("\n" + "=" * 80 + "\n")
    print(json.dumps(payloads, ensure_ascii=False, indent=2))
