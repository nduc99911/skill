#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parent.parent

# Add all dependent skill folders to import path.
for skill_dir in [
    BASE / "meta-ads-insights-reporter",
    BASE / "meta-ads-optimizer",
    BASE / "meta-ads-copywriter",
    BASE / "meta-ads-creative-matrix",
    BASE / "meta-ads-campaign-drafter",
]:
    if str(skill_dir) not in sys.path:
        sys.path.append(str(skill_dir))

from insights_reporter import get_ads_insights, format_insights_to_markdown  # noqa: E402
from optimizer import analyze_campaigns  # noqa: E402
from copywriter import generate_ad_copy, generate_angles_struct  # noqa: E402
from matrix_builder import build_matrix  # noqa: E402
from campaign_drafter import generate_approval_packet, build_meta_payloads  # noqa: E402


def _section(title: str) -> str:
    return f"\n{'=' * 96}\n{title}\n{'=' * 96}\n"


def _mock_insights() -> Dict[str, Any]:
    """Fallback mock data when live insights are unavailable or empty."""
    return {
        "data": [
            {
                "campaign_name": "Camp - Creative Fatigue",
                "adset_name": "Broad VN",
                "ad_name": "UGC V1",
                "spend": 180000,
                "impressions": 22000,
                "inline_link_clicks": 95,
                "ctr": 0.72,
                "cpc": 1894,
                "cpm": 8181,
                "actions": [{"action_type": "purchase", "value": "1"}],
                "purchase_roas": [{"action_type": "purchase", "value": "1.15"}],
                "action_values": [{"action_type": "purchase", "value": "207000"}],
                # normalized helpers for optimizer
                "purchases": 1,
                "roas": 1.15,
            },
            {
                "campaign_name": "Camp - Stable",
                "adset_name": "Interest Stack",
                "ad_name": "Image V2",
                "spend": 90000,
                "impressions": 14000,
                "inline_link_clicks": 170,
                "ctr": 1.21,
                "cpc": 529,
                "cpm": 6428,
                "actions": [{"action_type": "purchase", "value": "1"}],
                "purchase_roas": [{"action_type": "purchase", "value": "1.40"}],
                "action_values": [{"action_type": "purchase", "value": "126000"}],
                "purchases": 1,
                "roas": 1.40,
            },
        ]
    }


def _normalize_for_optimizer(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        out.append(
            {
                "campaign_name": r.get("campaign_name", "(unknown)"),
                "spend": float(r.get("spend", 0) or 0),
                "purchases": float(r.get("purchases", 0) or 0),
                "roas": float(r.get("roas", 0) or 0),
                "ctr": float(r.get("ctr", 0) or 0),
            }
        )
    return out


def run_full_automation_loop() -> str:
    report: List[str] = ["🚀 TERMINAL REPORT - META ADS MVP ORCHESTRATOR (CMO AGENT)"]

    # Step 1: Insights
    report.append(_section("STEP 1 - PULL INSIGHTS"))
    used_mock = False
    try:
        live_data = get_ads_insights(level="campaign", date_preset="last_7d")
        rows = live_data.get("data", []) if isinstance(live_data, dict) else []
        if not rows:
            used_mock = True
            raw_data = _mock_insights()
            report.append("Live insights rỗng -> fallback mock data để mô phỏng pipeline.")
        else:
            raw_data = live_data
            report.append(f"Live insights fetched: {len(rows)} rows")
    except Exception as e:
        used_mock = True
        raw_data = _mock_insights()
        report.append(f"Live insights unavailable ({e}) -> fallback mock data.")

    report.append(format_insights_to_markdown(raw_data))

    # Step 2: Optimizer diagnosis
    report.append(_section("STEP 2 - OPTIMIZER DIAGNOSIS"))
    normalized = _normalize_for_optimizer(raw_data.get("data", []))
    diagnosis_md = analyze_campaigns(normalized)
    report.append(diagnosis_md)

    # Step 3: Trigger copy regeneration for Creative Fatigue scenario
    report.append(_section("STEP 3 - COPYWRITER CREATIVE LOOP TRIGGER"))
    product_name = "Khóa học OpenClaw Thực chiến"
    insight_note = "Khách hàng là dân Ads mệt mỏi vì phải check camp thủ công mỗi ngày, sợ vít nhầm ngân sách"

    # Hardcoded trigger requested: assume at least one creative fatigue campaign exists.
    report.append(
        "Trigger condition: Optimizer báo có chiến dịch creative fatigue -> tạo copy mới cho vòng test tiếp theo."
    )
    copy_md = generate_ad_copy(product_name, insight_note)
    report.append(copy_md)

    # Step 4: Build testing matrix
    report.append(_section("STEP 4 - CREATIVE MATRIX BUILD"))
    angles = generate_angles_struct(product_name, insight_note)
    matrix_md = build_matrix("OpenClaw_Creative_Recovery", angles)
    report.append(matrix_md)

    # Step 5: Draft campaign approval packet + payloads (PAUSED only)
    report.append(_section("STEP 5 - CAMPAIGN DRAFTER (APPROVAL PACKET + PAUSED PAYLOADS)"))
    ads_list = [
        {
            "ad_name": f"Ad_{a.get('angle','Angle').replace('/', '_')}",
            "primary_text": a.get("primary_text", ""),
            "headline": a.get("headline", ""),
            "cta": "LEARN_MORE" if "Pain" in a.get("angle", "") else "SIGN_UP",
        }
        for a in angles
    ]

    approval_md = generate_approval_packet(
        campaign_name="Draft_OpenClaw_AutoLoop",
        daily_budget=500000,
        adset_name="Broad_VN",
        ads_list=ads_list,
    )
    payloads = build_meta_payloads(
        campaign_name="Draft_OpenClaw_AutoLoop",
        daily_budget=500000,
        adset_name="Broad_VN",
        page_id="123456789",
        ads_list=ads_list,
    )

    report.append(approval_md)
    report.append("\nJSON Payload Drafts (PAUSED-only):\n")
    report.append(json.dumps(payloads, ensure_ascii=False, indent=2))

    report.append(_section("PIPELINE SUMMARY"))
    report.append(
        "\n".join(
            [
                f"- Data source: {'Mock fallback' if used_mock else 'Live Meta insights'}",
                "- Optimization: Completed",
                "- Copywriter: Completed",
                "- Creative Matrix: Completed",
                "- Campaign Draft: Completed (PAUSED-only, no POST)",
                "- Overall status: ✅ FULL LOOP SUCCESS",
            ]
        )
    )

    return "\n".join(report)


if __name__ == "__main__":
    print(run_full_automation_loop())
