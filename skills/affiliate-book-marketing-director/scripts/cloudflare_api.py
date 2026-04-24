#!/usr/bin/env python3
from __future__ import annotations
import io
import textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any


class CloudflareApiError(RuntimeError):
    pass


class CloudflareClient:
    def __init__(self, account_id: str, api_token: str):
        if not account_id or not api_token:
            raise CloudflareApiError('CF_ACCOUNT_ID or CF_API_TOKEN missing')
        self.account_id = account_id
        self.api_token = api_token
        self.font_dir = Path('/root/.openclaw/workspace/assets/fonts')
        self.font_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_vn_font(self) -> Path:
        font_path = self.font_dir / 'Roboto-Regular.ttf'
        if font_path.exists():
            return font_path
        # Noto Sans (supports Vietnamese) from Google Fonts GitHub raw
        url = 'https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf'
        r = requests.get(url, timeout=30)
        if r.status_code >= 400:
            raise CloudflareApiError(f'Cannot download font: {r.status_code}')
        font_path.write_bytes(r.content)
        return font_path

    def render_image(self, prompt: str, negative_prompt: str = '') -> bytes:
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning'
        r = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
            },
            json={'prompt': prompt, 'negative_prompt': negative_prompt} if negative_prompt else {'prompt': prompt},
            timeout=60,
        )
        if r.status_code >= 400:
            raise CloudflareApiError(f'Cloudflare render failed {r.status_code}: {r.text[:500]}')
        return r.content

    def render_text_overlay(self, background_bytes: bytes, text: str, out_size: int = 1080) -> bytes:
        try:
            bg = Image.open(io.BytesIO(background_bytes)).convert('RGBA')
        except Exception as e:
            raise CloudflareApiError(f'Cannot decode background image: {e}')

        bg = bg.resize((out_size, out_size), Image.Resampling.LANCZOS)

        # dark overlay for readability
        overlay = Image.new('RGBA', bg.size, (0, 0, 0, 85))
        img = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(img)

        font_path = self._ensure_vn_font()
        font_size = int(out_size * 0.06)
        font = ImageFont.truetype(str(font_path), font_size)

        # wrap text dynamically
        max_width = int(out_size * 0.78)
        wrapped = text.strip()
        # try shrink loop to fit visually
        for _ in range(8):
            lines = []
            for para in wrapped.split('\n'):
                para = para.strip()
                if not para:
                    lines.append('')
                    continue
                # approximate wrap by character width
                width_char = max(12, int(0.55 * font_size))
                chars_per_line = max(10, max_width // width_char)
                lines.extend(textwrap.wrap(para, width=chars_per_line))
            test_text = '\n'.join(lines)
            bbox = draw.multiline_textbbox((0, 0), test_text, font=font, spacing=int(font_size * 0.35), align='center')
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw <= max_width and th <= int(out_size * 0.65):
                wrapped = test_text
                break
            font_size = max(28, int(font_size * 0.9))
            font = ImageFont.truetype(str(font_path), font_size)
            wrapped = test_text

        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=int(font_size * 0.35), align='center')
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (out_size - tw) // 2
        y = (out_size - th) // 2

        # drop shadow
        shadow_offset = max(2, int(font_size * 0.08))
        draw.multiline_text(
            (x + shadow_offset, y + shadow_offset),
            wrapped,
            font=font,
            fill=(0, 0, 0, 180),
            spacing=int(font_size * 0.35),
            align='center',
        )
        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill=(255, 255, 255, 245),
            spacing=int(font_size * 0.35),
            align='center',
        )

        out = io.BytesIO()
        img.convert('RGB').save(out, format='PNG', optimize=True)
        return out.getvalue()

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
