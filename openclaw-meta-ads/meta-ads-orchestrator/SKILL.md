---
name: meta-ads-orchestrator
description: Chief Marketing Officer (CMO) Agent for Meta Ads MVP. Orchestrates insights, optimization decisions, creative generation, testing matrix, and PAUSED-only campaign draft approvals into one end-to-end automation loop.
---

# Meta Ads Orchestrator (CMO Agent)

## Purpose

This skill is the top-level coordinator of the MVP.
It links all other skills into one continuous marketing workflow:

1. Pull performance insights
2. Diagnose via rule engine
3. Generate new copy angles for weak creatives
4. Build creative testing matrix
5. Produce approval packet + PAUSED payload drafts

## Connected Skills

- `meta-ads-insights-reporter`
- `meta-ads-optimizer`
- `meta-ads-copywriter`
- `meta-ads-creative-matrix`
- `meta-ads-campaign-drafter`

## Safety Model

- Orchestrator does not force live publishing.
- Final campaign drafting must remain `PAUSED`.
- Approval packet must be generated before any future write action.

## Runtime

- Source file: `pipeline_runner.py`
- Main entry: `run_full_automation_loop()`
