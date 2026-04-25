---
name: meta-ads-api-core
description: Core Meta Ads API hub for OpenClaw MVP (single-user). Provides safe read-first API primitives with strict token hygiene, dry-run/paused write guardrails, versioned Graph endpoint handling, and reusable pagination support for downstream skills.
---

# Meta Ads API Core

## Purpose

This skill is the foundational API layer for all Meta Ads skills in this MVP.
It is the single hub for Graph API communication and should be reused by higher-level skills.

## Required Environment Variables

- `META_ACCESS_TOKEN` (required for any live API call)
- `META_AD_ACCOUNT_ID` (required by downstream ads operations)
- `META_API_VERSION` (optional, defaults to `v23.0`)

## Safety & Guardrails (Mandatory)

1. Never log, print, echo, or expose `META_ACCESS_TOKEN`.
2. Default posture for write operations is `PAUSED` or `dry-run`.
3. Use Graph base URL format strictly:
   - `https://graph.facebook.com/{version}/`
4. Always read `version` from `META_API_VERSION`, fallback `v23.0`.
5. Do not auto-call API on skill load. Only call when:
   - user explicitly requests a test/action, or
   - downstream skill explicitly invokes this core module.

## System Prompt (for downstream orchestration)

Use this policy when this skill is active:

- You are the core Meta Ads API gateway.
- You must sanitize all errors and never include raw access tokens in output.
- You must enforce versioned Graph URL construction from `META_API_VERSION`.
- You must treat all write-intent actions as paused/dry-run by default unless an explicit override is provided by user instruction.
- You should return structured error data (`message`, `type`, `code`, `error_subcode`) when available.
- You should not perform any background polling loops unless explicitly requested.

## Bundled Runtime

Implementation file:

- `meta_api_core.py`

This module provides two reusable primitives:

1. `graph_api_call(...)`
   - basic Graph call with automatic token injection and normalized Meta error parsing.
2. `graph_api_call_paginated(...)`
   - auto-pagination using `paging.next` until exhaustion.

Downstream skills should import this module instead of re-implementing API plumbing.
