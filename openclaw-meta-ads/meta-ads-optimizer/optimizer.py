#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List, Tuple


PAUSE_LABEL = "🔴 TẮT NGAY"
SCALE_LABEL = "🟢 SCALE"
CREATIVE_LABEL = "🟡 THAY CREATIVE"
MONITOR_LABEL = "🔵 THEO DÕI"


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _classify_campaign(c: Dict[str, Any]) -> Tuple[str, str]:
    """Return (action_label, reason) based on deterministic optimization rules."""
    spend = _to_float(c.get("spend", 0.0), 0.0)
    purchases = _to_float(c.get("purchases", 0.0), 0.0)
    roas = _to_float(c.get("roas", 0.0), 0.0)
    ctr = _to_float(c.get("ctr", 0.0), 0.0)

    # Rule 1: Pause
    if spend > 200000 and purchases == 0:
        return PAUSE_LABEL, "Đốt tiền không ra đơn"

    # Rule 2: Scale
    if roas >= 3.0 and purchases >= 2:
        return SCALE_LABEL, "Chiến dịch đang win, đề xuất tăng 15-20% budget"

    # Rule 3: Creative Warning
    if ctr < 1.0 and spend > 100000:
        return CREATIVE_LABEL, 'Click thấp, nội dung có thể đã bị "mù"'

    # Rule 4: Monitor
    return MONITOR_LABEL, "Chưa đủ tín hiệu mạnh, tiếp tục theo dõi"


def analyze_campaigns(campaign_data: List[Dict[str, Any]]) -> str:
    """Analyze campaign metrics and return grouped Markdown recommendations."""
    groups = {
        PAUSE_LABEL: [],
        SCALE_LABEL: [],
        CREATIVE_LABEL: [],
        MONITOR_LABEL: [],
    }

    for c in campaign_data:
        action, reason = _classify_campaign(c)
        item = {
            "campaign_name": c.get("campaign_name", "(không rõ tên)"),
            "spend": _to_float(c.get("spend", 0.0), 0.0),
            "purchases": _to_float(c.get("purchases", 0.0), 0.0),
            "roas": _to_float(c.get("roas", 0.0), 0.0),
            "ctr": _to_float(c.get("ctr", 0.0), 0.0),
            "reason": reason,
        }
        groups[action].append(item)

    lines: List[str] = ["# BÁO CÁO CHẨN ĐOÁN ADS (AI Rule Engine)"]

    for action_label in [PAUSE_LABEL, SCALE_LABEL, CREATIVE_LABEL, MONITOR_LABEL]:
        lines.append(f"\n## {action_label}")
        bucket = groups[action_label]
        if not bucket:
            lines.append("- Không có chiến dịch nào trong nhóm này.")
            continue

        for x in bucket:
            lines.append(
                "- **{name}** | Spend: {spend:.0f} | Purchases: {purchases:.0f} | ROAS: {roas:.2f} | CTR: {ctr:.2f}%".format(
                    name=x["campaign_name"],
                    spend=x["spend"],
                    purchases=x["purchases"],
                    roas=x["roas"],
                    ctr=x["ctr"],
                )
            )
            lines.append(f"  - Lý do: {x['reason']}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Mock test data: 4 campaigns, each satisfies one distinct rule branch.
    mock_data = [
        {
            "campaign_name": "Camp A - Burn No Sale",
            "spend": 250000,
            "purchases": 0,
            "roas": 0.0,
            "ctr": 1.2,
        },
        {
            "campaign_name": "Camp B - Winner",
            "spend": 300000,
            "purchases": 3,
            "roas": 3.5,
            "ctr": 1.8,
        },
        {
            "campaign_name": "Camp C - Creative Fatigue",
            "spend": 150000,
            "purchases": 1,
            "roas": 1.1,
            "ctr": 0.7,
        },
        {
            "campaign_name": "Camp D - Stable",
            "spend": 80000,
            "purchases": 1,
            "roas": 1.4,
            "ctr": 1.4,
        },
    ]

    print(analyze_campaigns(mock_data))
