---
name: meta-ads-campaign-drafter
description: High-safety campaign drafting skill for Meta Ads. Generates approval packets and PAUSED-only payload drafts for campaign/adset/ad creation. Integrates with meta-ads-api-core but does not execute live posting in MVP.
---

# Meta Ads Campaign Drafter

## Purpose

This is the final drafting layer of the MVP.
It prepares campaign creation plans and JSON payloads for human approval.

## Dependencies

- Core module import path: `../meta-ads-api-core/meta_api_core.py`
- Core skill: `meta-ads-api-core`

## Required Environment Variables

- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID`
- `META_API_VERSION`
- `META_PAGE_ID`

## Supreme Guardrails (Must Never Be Violated)

1. **Never publish campaign live directly from this skill.**
2. **Every generated payload must include `status: "PAUSED"` at all levels** (Campaign / Ad Set / Ad).
3. **Always generate an Approval Packet (Markdown) before any future POST execution.**
4. In MVP mode, do not call live write API. Return payload drafts only.

## Runtime File

- `campaign_drafter.py`

## Core Functions

1. `generate_approval_packet(campaign_name, daily_budget, adset_name, ads_list)`
   - Returns a Markdown approval packet for user review.

2. `build_meta_payloads(campaign_name, daily_budget, adset_name, page_id, ads_list)`
   - Returns draft JSON payloads for Campaign / Ad Set / Ads.
   - MVP mode: return-only, no POST execution.
