#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


DEFAULT_META_API_VERSION = "v23.0"
DEFAULT_GRAPH_ROOT = "https://graph.facebook.com/"


class MetaApiCoreError(RuntimeError):
    """Normalized Meta API error.

    Important:
    - Never include the raw access token in exception text.
    - Keep error details useful for debugging downstream skills.
    """

    def __init__(
        self,
        message: str,
        *,
        error_type: Optional[str] = None,
        code: Optional[int] = None,
        error_subcode: Optional[int] = None,
        status_code: Optional[int] = None,
        raw_error: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_type = error_type
        self.code = code
        self.error_subcode = error_subcode
        self.status_code = status_code
        self.raw_error = raw_error or {}
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return (
            f"MetaApiCoreError(status={self.status_code}, type={self.error_type}, "
            f"code={self.code}, subcode={self.error_subcode}, message={self.message})"
        )


def get_meta_api_version() -> str:
    """Return configured Meta API version, defaulting to v23.0."""
    return (os.getenv("META_API_VERSION") or DEFAULT_META_API_VERSION).strip()


def get_graph_base_url() -> str:
    """Build Graph base URL using configured version.

    Format must be:
    https://graph.facebook.com/{version}/
    """
    version = get_meta_api_version()
    return urljoin(DEFAULT_GRAPH_ROOT, f"{version}/")


def _require_access_token() -> str:
    """Read token from env without ever logging it."""
    token = (os.getenv("META_ACCESS_TOKEN") or "").strip()
    if not token:
        raise MetaApiCoreError(
            "META_ACCESS_TOKEN is missing",
            error_type="ConfigurationError",
        )
    return token


def _normalize_meta_error(response: requests.Response, body: Any) -> MetaApiCoreError:
    """Extract Meta error.message / error.type / codes when available."""
    error = body.get("error", {}) if isinstance(body, dict) else {}
    return MetaApiCoreError(
        error.get("message") or f"HTTP {response.status_code} from Meta Graph API",
        error_type=error.get("type"),
        code=error.get("code"),
        error_subcode=error.get("error_subcode"),
        status_code=response.status_code,
        raw_error=error if isinstance(error, dict) else {},
    )


def graph_api_call(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    allow_write: bool = False,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Perform a versioned Meta Graph API request.

    Features:
    - Auto-attaches access_token from environment.
    - Uses META_API_VERSION (default v23.0).
    - Parses detailed Meta errors (message, type, code, error_subcode).

    Guardrails:
    - Write operations are blocked unless allow_write=True.
    - Even when allow_write=True, default dry_run=True returns a paused response
      instead of mutating Meta.
    - Never logs or prints the access token.
    """
    method_upper = method.upper().strip()
    is_write = method_upper in {"POST", "DELETE", "PATCH", "PUT"}

    if is_write and not allow_write:
        return {
            "ok": False,
            "paused": True,
            "reason": "write_blocked_by_guardrail",
            "method": method_upper,
            "path": path,
        }

    if is_write and dry_run:
        return {
            "ok": False,
            "paused": True,
            "reason": "dry_run",
            "method": method_upper,
            "path": path,
        }

    token = _require_access_token()
    req_params = dict(params or {})
    req_params["access_token"] = token

    base_url = get_graph_base_url()
    url = urljoin(base_url, path.lstrip("/"))

    response = requests.request(
        method_upper,
        url,
        params=req_params,
        data=data,
        json=json_body,
        timeout=timeout,
    )

    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}

    if response.status_code >= 400:
        raise _normalize_meta_error(response, body)

    if isinstance(body, dict):
        return body
    return {"data": body}


def graph_api_call_paginated(
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Fetch all pages of a Graph API collection.

    Behavior:
    - Starts from versioned Graph path.
    - Follows `paging.next` until exhausted.
    - Accumulates all items into one flat `data` list.

    Notes:
    - Uses GET only.
    - Automatically injects access_token on the first request.
    - `paging.next` already includes a tokenized URL from Meta, so subsequent
      requests follow that URL directly without reconstructing parameters.
    """
    token = _require_access_token()
    base_url = get_graph_base_url()
    next_url: Optional[str] = urljoin(base_url, path.lstrip("/"))
    next_params: Optional[Dict[str, Any]] = dict(params or {})
    next_params["access_token"] = token

    all_items: List[Dict[str, Any]] = []
    page_count = 0

    while next_url:
        response = requests.get(next_url, params=next_params, timeout=timeout)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        if response.status_code >= 400:
            raise _normalize_meta_error(response, body)

        page_count += 1
        page_items = body.get("data", []) if isinstance(body, dict) else []
        if isinstance(page_items, list):
            all_items.extend(page_items)

        paging = body.get("paging", {}) if isinstance(body, dict) else {}
        next_url = paging.get("next")
        next_params = None  # paging.next is already a full URL with cursor state.

    return {
        "data": all_items,
        "pages_fetched": page_count,
        "version": get_meta_api_version(),
    }
