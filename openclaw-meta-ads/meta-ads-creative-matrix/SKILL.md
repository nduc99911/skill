---
name: meta-ads-creative-matrix
description: Build a Meta Ads creative testing matrix from copy angles. Converts copy hypotheses into trackable creative variants by format, visual concept, and funnel stage.
---

# Meta Ads Creative Matrix

## Purpose

Transform ad copy angles into a practical testing matrix so the team can execute and compare creatives systematically.

## Input

- Campaign name
- Angle list (typically from `meta-ads-copywriter`)

## Output

Markdown table with columns:
- Creative ID
- Angle
- Hook
- Format (Video UGC / Image / Carousel)
- Visual Concept
- Funnel Stage

## Runtime

- Source file: `matrix_builder.py`
- Main function: `build_matrix(campaign_name, angles_list)`

## Notes

This skill does not call external APIs.
It is a planning/structuring tool for creative loop execution.
