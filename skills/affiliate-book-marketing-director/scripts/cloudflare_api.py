#!/usr/bin/env python3
from __future__ import annotations
import io
import textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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

    def _ensure_vn_font(self) -> Path | None:
        preferred = [
            self.font_dir / 'PlayfairDisplay-Regular.ttf',
            self.font_dir / 'Merriweather-Regular.ttf',
            self.font_dir / 'Lora-Regular.ttf',
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'),
        ]
        for p in preferred:
            if p.exists():
                return p

        download_targets = [
            (
                self.font_dir / 'PlayfairDisplay-Regular.ttf',
                'https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf',
            ),
            (
                self.font_dir / 'Merriweather-Regular.ttf',
                'https://raw.githubusercontent.com/google/fonts/main/ofl/merriweather/Merriweather-Regular.ttf',
            ),
            (
                self.font_dir / 'Lora-Regular.ttf',
                'https://raw.githubusercontent.com/google/fonts/main/ofl/lora/Lora%5Bwght%5D.ttf',
            ),
        ]
        for font_path, url in download_targets:
            try:
                r = requests.get(url, timeout=30)
                if r.status_code < 400 and r.content:
                    font_path.write_bytes(r.content)
                    return font_path
            except Exception:
                continue
        return None

    def render_image(self, prompt: str, negative_prompt: str = '') -> bytes:
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning'
        payload = {'prompt': prompt, 'negative_prompt': negative_prompt} if negative_prompt else {'prompt': prompt}
        last_err = None
        for _ in range(3):
            try:
                r = requests.post(
                    url,
                    headers={
                        'Authorization': f'Bearer {self.api_token}',
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    timeout=90,
                )
                if r.status_code < 400:
                    return r.content
                last_err = f'{r.status_code}: {r.text[:300]}'
            except Exception as e:
                last_err = str(e)
                continue
        raise CloudflareApiError(f'Cloudflare render failed after retries: {last_err}')

    def render_text_overlay(self, background_bytes: bytes, text: str, out_size: int = 1080) -> bytes:
        try:
            bg = Image.open(io.BytesIO(background_bytes)).convert('RGBA')
        except Exception as e:
            raise CloudflareApiError(f'Cannot decode background image: {e}')

        bg = bg.resize((out_size, out_size), Image.Resampling.LANCZOS)

        # darker cinematic overlay + subtle vignette for depth
        overlay = Image.new('RGBA', bg.size, (8, 8, 12, 105))
        img = Image.alpha_composite(bg, overlay)
        vignette = Image.new('L', bg.size, 0)
        vdraw = ImageDraw.Draw(vignette)
        margin = int(out_size * 0.08)
        vdraw.ellipse((margin, margin, out_size - margin, out_size - margin), fill=150)
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=int(out_size * 0.12)))
        vignette_rgba = Image.new('RGBA', bg.size, (0, 0, 0, 0))
        vignette_rgba.putalpha(Image.eval(vignette, lambda px: max(0, 170 - px)))
        img = Image.alpha_composite(img, vignette_rgba)
        draw = ImageDraw.Draw(img)

        font_path = self._ensure_vn_font()
        font_size = int(out_size * 0.06)
        try:
            font = ImageFont.truetype(str(font_path), font_size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

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
            try:
                font = ImageFont.truetype(str(font_path), font_size) if font_path else ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            wrapped = test_text

        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=int(font_size * 0.35), align='center')
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (out_size - tw) // 2
        y = (out_size - th) // 2

        spacing = int(font_size * 0.42)

        # blurred drop shadow layer for depth
        shadow_offset = max(4, int(font_size * 0.10))
        shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.multiline_text(
            (x + shadow_offset, y + shadow_offset),
            wrapped,
            font=font,
            fill=(18, 18, 20, 210),
            spacing=spacing,
            align='center',
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(3, int(font_size * 0.08))))
        img = Image.alpha_composite(img, shadow_layer)
        draw = ImageDraw.Draw(img)

        # main serif text with warmer premium tone
        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill=(247, 244, 233, 248),
            spacing=spacing,
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
