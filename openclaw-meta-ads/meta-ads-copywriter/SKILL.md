---
name: meta-ads-copywriter
description: AI copywriting skill for Meta Ads creative development with strict Meta Policy guardrails. Generates multi-angle ad copy (Hook, Primary Text, Headline, CTA) without unsafe claims.
---

# Meta Ads Copywriter

## Purpose

Generate persuasive ad copy angles that are practical for testing while staying policy-safe for Meta Ads.

## Guardrails (Mandatory)

- Never promise unrealistic outcomes (e.g., "khỏi bệnh 100%", "kiếm 100tr/tháng chắc chắn").
- Never target or infer sensitive/personal attributes of the audience.
- Never use extreme before/after framing that implies guaranteed transformation.
- Prefer responsible wording: practical benefit, clear context, realistic expectation.

## Runtime

- Source file: `copywriter.py`
- Main function: `generate_ad_copy(product_name, insight_note)`

## Output Shape

The function returns Markdown containing 2 tested angles:

- Angle 1: Pain Point
- Angle 2: Proof / Benefit

Each angle contains:
- Hook
- Primary Text
- Headline
- CTA
