---
name: meta-ads-insights-reporter
description: Meta Ads reporting skill for pulling and formatting campaign/adset/ad insights via Meta Graph API. Depends on meta-ads-api-core for safe API calls, versioned endpoints, and pagination.
---

# Meta Ads Insights Reporter

## Purpose

This skill fetches performance insights from Meta Ads API and converts raw payloads into readable Markdown reports.

It is read-focused and reuses `meta-ads-api-core` for all Graph communication.

## Dependency

- Core dependency path: `../meta-ads-api-core/meta_api_core.py`
- This skill must import and use:
  - `graph_api_call_paginated(...)`
  - `MetaApiCoreError`

## Required Env

- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID` (format recommended: `act_<id>`)
- `META_API_VERSION` (optional, default `v23.0`)

## Primary Functions

1. `get_ads_insights(level="campaign", date_preset="last_7d")`
   - Endpoint: `/{META_AD_ACCOUNT_ID}/insights`
   - Params:
     - `level`
     - `date_preset`
     - `fields=campaign_name,adset_name,ad_name,spend,impressions,inline_link_clicks,ctr,cpc,cpm,actions,purchase_roas,action_values`

2. `format_insights_to_markdown(raw_data)`
   - Build Markdown table.
   - Extract `Purchases` from `actions` array by matching:
     - `offsite_conversion.fb_pixel_purchase`
     - or `purchase`
   - Extract `Revenue` from `action_values` array with same matching logic.
   - Extract `ROAS` from `purchase_roas` array (value).
   - Compute `CPA = spend / purchases` with divide-by-zero safe handling.

## Execution Policy

- Do not auto-run on skill load.
- Run only when user requests report/test explicitly.
- Keep token hygiene from core skill: never print access token.
