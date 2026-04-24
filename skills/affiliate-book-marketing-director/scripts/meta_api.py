#!/usr/bin/env python3
from __future__ import annotations
import mimetypes
import requests
from pathlib import Path
from typing import Any, Dict

GRAPH_BASE = 'https://graph.facebook.com/v19.0'


class MetaApiError(RuntimeError):
    pass


class MetaClient:
    def __init__(self, access_token: str):
        if not access_token:
            raise MetaApiError('META_ACCESS_TOKEN is missing')
        self.access_token = access_token

    def _req(self, method: str, path: str, access_token: str | None = None, **kwargs) -> Dict[str, Any]:
        params = kwargs.pop('params', {}) or {}
        params['access_token'] = access_token or self.access_token
        r = requests.request(method, f'{GRAPH_BASE}/{path.lstrip("/")}', params=params, timeout=30, **kwargs)
        try:
            data = r.json()
        except Exception:
            data = {'raw': r.text}
        if r.status_code >= 400:
            raise MetaApiError(f'Meta API {r.status_code}: {data}')
        return data

    def list_pages(self) -> list[Dict[str, Any]]:
        data = self._req('GET', 'me/accounts', params={'fields': 'id,name,access_token,category', 'limit': 200})
        return data.get('data', [])

    def list_page_posts(self, page_id: str, page_access_token: str, limit: int = 10) -> Dict[str, Any]:
        return self._req(
            'GET',
            f'{page_id}/posts',
            access_token=page_access_token,
            params={'fields': 'id,message,created_time', 'limit': limit},
        )

    def create_photo_post(self, page_id: str, page_access_token: str, caption: str, image_url: str) -> Dict[str, Any]:
        return self._req(
            'POST',
            f'{page_id}/photos',
            access_token=page_access_token,
            data={'caption': caption, 'url': image_url, 'published': 'true'},
        )

    def create_photo_post_from_file(self, page_id: str, page_access_token: str, caption: str, image_path: str) -> Dict[str, Any]:
        p = Path(image_path)
        if not p.exists():
            raise MetaApiError(f'Image file not found: {image_path}')
        mime = mimetypes.guess_type(str(p))[0] or 'image/png'
        with p.open('rb') as f:
            files = {'source': (p.name, f, mime)}
            return self._req(
                'POST',
                f'{page_id}/photos',
                access_token=page_access_token,
                data={'caption': caption, 'published': 'true'},
                files=files,
            )

    def create_feed_post(self, page_id: str, page_access_token: str, message: str) -> Dict[str, Any]:
        return self._req('POST', f'{page_id}/feed', access_token=page_access_token, data={'message': message})

    def create_comment(self, object_id: str, page_access_token: str, message: str) -> Dict[str, Any]:
        return self._req('POST', f'{object_id}/comments', access_token=page_access_token, data={'message': message})

    def get_post_comments(self, post_id: str, page_access_token: str, limit: int = 50) -> Dict[str, Any]:
        return self._req('GET', f'{post_id}/comments', access_token=page_access_token, params={'fields': 'id,message,from,created_time', 'limit': limit})

    def private_reply_to_comment(self, comment_id: str, page_access_token: str, message: str) -> Dict[str, Any]:
        # Requires proper app/page permissions and feature support.
        return self._req('POST', f'{comment_id}/private_replies', access_token=page_access_token, data={'message': message})

    def publish_instagram_media(self, ig_business_id: str, image_url: str, caption: str) -> Dict[str, Any]:
        # Step 1: create container
        c = self._req('POST', f'{ig_business_id}/media', data={'image_url': image_url, 'caption': caption})
        creation_id = c.get('id')
        if not creation_id:
            raise MetaApiError(f'IG media container missing id: {c}')
        # Step 2: publish container
        return self._req('POST', f'{ig_business_id}/media_publish', data={'creation_id': creation_id})
