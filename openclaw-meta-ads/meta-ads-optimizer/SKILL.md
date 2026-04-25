---
name: meta-ads-optimizer
description: AI rule engine for Meta Ads optimization decisions (Pause / Scale / Creative Warning / Monitor). Consumes normalized insights data from meta-ads-insights-reporter and outputs grouped actionable markdown recommendations.
---

# Meta Ads Optimizer

## Purpose

This skill is the decision layer for Meta Ads optimization.
It does not call Meta API directly.

Input data must come from `meta-ads-insights-reporter` (or any equivalent normalized dataset).

## Core Behavior

The optimizer applies deterministic business rules to classify each campaign into one action group:

- 🔴 TẮT NGAY
- 🟢 SCALE
- 🟡 THAY CREATIVE
- 🔵 THEO DÕI

## Rule Set

1. Pause:
- If `Spend > 200000` and `Purchases == 0`
- Label: `🔴 TẮT NGAY`
- Reason: `Đốt tiền không ra đơn`

2. Scale:
- If `ROAS >= 3.0` and `Purchases >= 2`
- Label: `🟢 SCALE`
- Reason: `Chiến dịch đang win, đề xuất tăng 15-20% budget`

3. Creative Warning:
- If `CTR < 1.0%` and `Spend > 100000`
- Label: `🟡 THAY CREATIVE`
- Reason: `Click thấp, nội dung có thể đã bị "mù"`

4. Monitor:
- All remaining cases
- Label: `🔵 THEO DÕI`

## Output Contract

- Function `analyze_campaigns(campaign_data)` returns Markdown text.
- Output is grouped by action sections, each listing campaigns and key metrics.
- Designed for direct send to chat/reporting channels.

## Runtime File

- `optimizer.py`
