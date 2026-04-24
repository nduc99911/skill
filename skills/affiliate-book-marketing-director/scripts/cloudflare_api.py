#!/usr/bin/env python3
from __future__ import annotations
import requests
from typing import Dict, Any


class CloudflareApiError(RuntimeError):
    pass


class CloudflareClient:
    def __init__(self, account_id: str, api_token: str):
        if not account_id or not api_token:
            raise CloudflareApiError('CF_ACCOUNT_ID or CF_API_TOKEN missing')
        self.account_id = account_id
        self.api_token = api_token

    def render_image(self, prompt: str) -> bytes:
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning'
        r = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
            },
            json={'prompt': prompt},
            timeout=60,
        )
        if r.status_code >= 400:
            raise CloudflareApiError(f'Cloudflare render failed {r.status_code}: {r.text[:500]}')
        return r.content

    def upload_image_public(self, image_bytes: bytes) -> Dict[str, Any]:
        # Optional path. Requires Cloudflare Images enabled in account.
        # Returns id + delivery URL template when available.
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/images/v1'
        files = {'file': ('render.png', image_bytes, 'image/png')}
        r = requests.post(
            url,
            headers={'Authorization': f'Bearer {self.api_token}'},
            files=files,
            timeout=60,
        )
        data = r.json() if r.text else {}
        if r.status_code >= 400 or not data.get('success', False):
            raise CloudflareApiError(f'Cloudflare images upload failed {r.status_code}: {str(data)[:500]}')
        return data.get('result', {})
