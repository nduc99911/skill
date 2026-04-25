#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs


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


def _has_utm(url: str) -> bool:
    try:
        q = parse_qs(urlparse(url).query)
        return any(k.startswith('utm_') for k in q.keys())
    except Exception:
        return False


def _check_status_paused(level_name: str, status: str) -> Tuple[str, str]:
    if str(status).upper().strip() == 'PAUSED':
        return '✅ PASS', f'{level_name}: status=PAUSED'
    return '❌ ERROR', f'{level_name}: status phải là PAUSED, hiện tại={status}'


def validate_post_ready(payloads_list: Dict[str, Any]) -> str:
    """Pre-flight checklist before any future write API call.

    Rules:
    - Ad creative must include image_hash or video_id inside object_story_spec.
    - Ad destination URL (link) is required.
    - Warn if URL has no UTM params.
    - Ad set daily_budget must be >= 20000.
    - All status fields must be PAUSED.
    """
    rows: List[Tuple[str, str, str]] = []
    blocked = False

    campaign = payloads_list.get('campaign', {}) or {}
    adset = payloads_list.get('adset', {}) or {}
    ads = payloads_list.get('ads', []) or []

    # Campaign status check
    st, detail = _check_status_paused('Campaign', campaign.get('status', ''))
    rows.append(('Campaign Status', st, detail))
    if st.startswith('❌'):
        blocked = True

    # AdSet checks
    st, detail = _check_status_paused('AdSet', adset.get('status', ''))
    rows.append(('AdSet Status', st, detail))
    if st.startswith('❌'):
        blocked = True

    daily_budget = int(float(adset.get('daily_budget', 0) or 0))
    if daily_budget >= 20000:
        rows.append(('Budget Check', '✅ PASS', f'daily_budget={daily_budget}'))
    else:
        rows.append(('Budget Check', '❌ ERROR', f'daily_budget={daily_budget} < 20000'))
        blocked = True

    # Ad-level checks
    for idx, ad in enumerate(ads, 1):
        ad_name = ad.get('name', f'Ad_{idx}')

        st, detail = _check_status_paused(f'Ad[{ad_name}]', ad.get('status', ''))
        rows.append((f'Ad Status #{idx}', st, detail))
        if st.startswith('❌'):
            blocked = True

        oss = ((ad.get('creative') or {}).get('object_story_spec') or {})
        link_data = oss.get('link_data') or {}

        # Media asset check (image_hash or video_id)
        has_image = bool(link_data.get('image_hash'))
        has_video = bool((oss.get('video_data') or {}).get('video_id')) or bool(link_data.get('video_id'))
        if has_image or has_video:
            rows.append((f'Media Asset #{idx}', '✅ PASS', f'{ad_name}: has image/video asset'))
        else:
            rows.append((f'Media Asset #{idx}', '❌ THIẾU MEDIA ASSET', f'{ad_name}: thiếu image_hash/video_id'))
            blocked = True

        # Destination URL check
        link = str(link_data.get('link', '') or '').strip()
        if not link:
            rows.append((f'Destination URL #{idx}', '❌ ERROR', f'{ad_name}: thiếu link đích'))
            blocked = True
        else:
            rows.append((f'Destination URL #{idx}', '✅ PASS', f'{ad_name}: {link}'))
            if _has_utm(link):
                rows.append((f'Tracking UTM #{idx}', '✅ PASS', f'{ad_name}: có tham số UTM'))
            else:
                rows.append((f'Tracking UTM #{idx}', '⚠️ CẢNH BÁO TRACKING', f'{ad_name}: link chưa có UTM'))

    lines = [
        '# 🛫 POST-ready Checklist (Pre-flight Check)',
        '',
        '| Hạng mục | Kết quả | Chi tiết |',
        '|---|---|---|',
    ]
    for name, status, detail in rows:
        lines.append(f'| {name} | {status} | {detail} |')

    lines.append('')
    if blocked:
        lines.append('🚫 BLOCKED: Payload thiếu trường bắt buộc. Hệ thống từ chối gọi API.')
    else:
        lines.append('✅ PAYLOAD HỢP LỆ: Sẵn sàng gửi lên Meta API.')

    return '\n'.join(lines)


if __name__ == "__main__":
    # End-to-end test data (Phase 5 MVP)
    campaign_name = "Test_Angle_Moi"
    daily_budget = 500000
    adset_name = "Broad_VN_Office"
    page_id = "123456789"

    ads_list = [
        {
            "ad_name": "Ad_Office_PainPoint_01",
            "primary_text": "Dân văn phòng thường không thiếu cố gắng, chỉ thiếu một khoảng dừng đúng cách để đầu óc nhẹ lại.",
            "headline": "Đọc để đầu óc bớt quá tải sau giờ làm",
            "cta": "LEARN_MORE",
        },
        {
            "ad_name": "Ad_Office_PainPoint_02",
            "primary_text": "Đi làm đều nhưng càng ngày càng cạn năng lượng? Nội dung này giúp bạn nhìn lại áp lực công việc.",
            "headline": "Một cuốn sách cho người đi làm đang cạn pin",
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
    print("\n" + "=" * 80 + "\n")
    print(validate_post_ready(payloads))
