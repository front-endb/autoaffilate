"""Image generation via Pollinations AI (genuinely free, zero setup — no key,
no account, no card). Falls back to a labeled placeholder if the request
fails (network issue, etc.) so the pipeline stays testable end-to-end."""
import hashlib
import io
import textwrap
import urllib.parse

import requests
from PIL import Image, ImageDraw

import config
import ui

MOCK = False  # Pollinations needs no key, so real generation is always attempted

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


def _generate_pollinations(prompt: str) -> Image.Image:
    url = POLLINATIONS_URL.format(prompt=urllib.parse.quote(prompt))
    resp = requests.get(
        url,
        params={
            "model": "flux", "width": 1024, "height": 1536,
            "nologo": "true", "enhance": "true",
        },
        timeout=90,
    )
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def _generate_placeholder(prompt: str, reason: str = "") -> Image.Image:
    """Сіра картка з текстом промпта — щоб бачити, що саме згенерувалось би."""
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
    bg = (200 + seed % 40, 195 + seed % 30, 190 + seed % 50)
    img = Image.new("RGB", (config.PIN_WIDTH, config.PIN_HEIGHT), bg)
    draw = ImageDraw.Draw(img)
    label = f"MOCK IMAGE{f' ({reason})' if reason else ''}"
    draw.text((40, 40), label, fill=(60, 60, 60))
    y = 120
    for line in textwrap.wrap(prompt, width=48)[:25]:
        draw.text((40, y), line, fill=(80, 80, 80))
        y += 30
    return img


def crop_to_pin(img: Image.Image) -> Image.Image:
    """Center-crop до 2:3 і resize до 1000x1500."""
    target_ratio = config.PIN_WIDTH / config.PIN_HEIGHT
    w, h = img.size
    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img.resize((config.PIN_WIDTH, config.PIN_HEIGHT), Image.LANCZOS)


def _generate_with_fallback(prompt: str) -> Image.Image:
    try:
        img = _generate_pollinations(prompt)
        ui.log("IMAGE", "generated via Pollinations AI (free, no key)")
        return img
    except Exception as e:
        ui.log("WARN", f"Pollinations image gen failed ({e}) — using mock placeholder")
        return _generate_placeholder(prompt, reason="Pollinations unreachable")


def generate_pin_image(prompt: str, product_id: str, variation: int) -> str:
    img = _generate_with_fallback(prompt)
    img = crop_to_pin(img)
    path = config.IMAGES_DIR / f"{product_id}_v{variation}.jpg"
    img.save(path, "JPEG", quality=90)
    return str(path)
