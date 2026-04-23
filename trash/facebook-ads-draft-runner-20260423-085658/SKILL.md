---
name: facebook-ads-draft-runner
description: Create review-only Facebook ads drafts for the Facebook Affiliate Books system. Use when the user wants to pick 1 approved post per page (max 3 total/day), propose objective, audience, budget, and creative, and write only to output/ads-drafts.json without launching campaigns or calling Meta Ads API.
---

# Facebook Ads Draft Runner

Use this skill when the user wants ad draft recommendations from already-approved Facebook affiliate book posts.

## Scope

Allowed inputs only:
- `output/approved-plan.json`
- `config/pages.json`
- `data/products.csv`
- `state/posting-history.json`
- `state/planner_summary.txt`

Primary script:
- `scripts/facebook_ads_draft_runner.py`

Output only:
- `output/ads-drafts.json`

## Hard safety rules

Never do any of these in this skill:
- launch campaign
- create ad on Facebook
- call Meta Ads API
- use ads tokens
- enable spend cap/bid/pause/scale actions
- read from `daily-plan.json` as a source of eligible posts

If a post is not in `approved-plan.json`, it is not eligible.

## Selection rules

- Maximum 1 ad draft per page per day
- Maximum 3 drafts total per day
- Prioritize:
  - higher `priority_score`
  - better page-persona/category fit
  - stronger ad-friendly post type
  - valid affiliate link
- Avoid selecting the same product if it was recently used for ads
- Avoid two drafts with overly similar message openings

## Objective rules

- `direct_sell` -> prefer `traffic`
- `soft_content` / `listicle` -> prefer `engagement`
- Always store `objective_reason`

## Audience format

Each draft should propose:
- `age_range`
- `interests`
- `gender`
- `note`

Keep targeting reasonably narrow and meaningful.

## Budget rules

Use only small test budgets.
Store clearly that it is a test budget, not scale budget.

## Workflow

1. Read `output/approved-plan.json`
2. Read page personas from `config/pages.json`
3. Read product metadata from `data/products.csv`
4. Optionally check `state/posting-history.json` and ads history for repeats
5. Run `scripts/facebook_ads_draft_runner.py`
6. Return a compact summary in this format:
   - `page_name | product_title | objective | daily_budget | audience | status`
7. Stop there and wait for explicit user approval

## Approval model

- `output/ads-drafts.json` = ad draft layer
- only if the user explicitly says `duyệt ads cho page X` should the draft move to an approved-ads step
- only if the user explicitly says `bật launch ads thật` may a future launch flow be prepared
