#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Import core API module from sibling skill directory.
CORE_DIR = Path(__file__).resolve().parent.parent / "meta-ads-api-core"
if str(CORE_DIR) not in sys.path:
    sys.path.append(str(CORE_DIR))

from meta_api_core import graph_api_call_paginated, MetaApiCoreError  # noqa: E402


INSIGHT_FIELDS = (
    "campaign_name,adset_name,ad_name,spend,impressions,inline_link_clicks,"
    "ctr,cpc,cpm,actions,purchase_roas,action_values"
)

PURCHASE_KEYS = {
    "offsite_conversion.fb_pixel_purchase",
    "purchase",
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_metric_from_action_array(arr: Any, keys: set[str]) -> float:
    if not isinstance(arr, list):
        return 0.0
    total = 0.0
    for item in arr:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type", "")).strip()
        if action_type in keys:
            total += _to_float(item.get("value", 0.0), 0.0)
    return total


def get_ads_insights(level: str = "campaign", date_preset: str = "last_7d") -> Dict[str, Any]:
    """Fetch Meta Ads insights with auto-pagination.

    Endpoint:
      /{META_AD_ACCOUNT_ID}/insights
    """
    ad_account_id = (os.getenv("META_AD_ACCOUNT_ID") or "").strip()
    if not ad_account_id:
        raise MetaApiCoreError("META_AD_ACCOUNT_ID is missing", error_type="ConfigurationError")

    path = f"/{ad_account_id}/insights"
    params = {
        "level": level,
        "date_preset": date_preset,
        "fields": INSIGHT_FIELDS,
    }
    return graph_api_call_paginated(path=path, params=params)


def format_insights_to_markdown(raw_data: Dict[str, Any]) -> str:
    """Convert raw insights JSON list to Markdown table.

    Special handling:
    - Purchases from `actions`
    - Revenue from `action_values`
    - ROAS from `purchase_roas`
    - CPA = spend / purchases (safe when purchases == 0)
    """
    rows = raw_data.get("data", []) if isinstance(raw_data, dict) else []

    header = (
        "| Campaign | Adset | Ad | Spend | Impr. | Clicks | CTR | CPC | CPM | Purchases | Revenue | ROAS | CPA |\n"
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    if not rows:
        return header + "\n| (no data) | - | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"

    out_lines: List[str] = [header]
    for r in rows:
        campaign = str(r.get("campaign_name", "-"))
        adset = str(r.get("adset_name", "-"))
        ad = str(r.get("ad_name", "-"))

        spend = _to_float(r.get("spend", 0.0), 0.0)
        impressions = int(_to_float(r.get("impressions", 0.0), 0.0))
        clicks = int(_to_float(r.get("inline_link_clicks", 0.0), 0.0))
        ctr = _to_float(r.get("ctr", 0.0), 0.0)
        cpc = _to_float(r.get("cpc", 0.0), 0.0)
        cpm = _to_float(r.get("cpm", 0.0), 0.0)

        purchases = _extract_metric_from_action_array(r.get("actions"), PURCHASE_KEYS)
        revenue = _extract_metric_from_action_array(r.get("action_values"), PURCHASE_KEYS)
        roas = _extract_metric_from_action_array(r.get("purchase_roas"), PURCHASE_KEYS)

        cpa = (spend / purchases) if purchases > 0 else 0.0

        out_lines.append(
            "| {campaign} | {adset} | {ad} | {spend:.2f} | {impr} | {clicks} | {ctr:.2f}% | {cpc:.2f} | {cpm:.2f} | {purchases:.0f} | {revenue:.2f} | {roas:.2f} | {cpa:.2f} |".format(
                campaign=campaign.replace("|", "\\|"),
                adset=adset.replace("|", "\\|"),
                ad=ad.replace("|", "\\|"),
                spend=spend,
                impr=impressions,
                clicks=clicks,
                ctr=ctr,
                cpc=cpc,
                cpm=cpm,
                purchases=purchases,
                revenue=revenue,
                roas=roas,
                cpa=cpa,
            )
        )

    return "\n".join(out_lines)


if __name__ == "__main__":
    data = get_ads_insights(level="campaign", date_preset="last_7d")
    print(format_insights_to_markdown(data))
