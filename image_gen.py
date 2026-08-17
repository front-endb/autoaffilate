"""Image generation with a free-first, cheap-fallback backend chain:
Gemini 2.5 Flash Image ("nano banana", free tier but rate-limited) is tried
first, fal.ai flux/schnell (paid, ~$0.003/image) catches whatever Gemini's
quota rejects, and a labeled placeholder covers the case where neither key
is set (or both backends fail) so the pipeline stays testable end-to-end."""
import base64
import hashlib
import io
import textwrap

import requests
from PIL import Image, ImageDraw

import config
import ui

MOCK = not (config.GEMINI_API_KEY or config.FAL_API_KEY)

FAL_URL = "https://fal.run/fal-ai/flux/schnell"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{config.GEMINI_IMAGE_MODEL}:generateContent"
)


def _generate_gemini(prompt: str) -> Image.Image:
    resp = requests.post(
        GEMINI_URL,
        params={"key": config.GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        },
        timeout=120,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    inline = next(p["inlineData"] for p in parts if "inlineData" in p)
    return Image.open(io.BytesIO(base64.b64decode(inline["data"])))


def _generate_fal(prompt: str) -> Image.Image:
    resp = requests.post(
        FAL_URL,
        headers={"Authorization": f"Key {config.FAL_API_KEY}"},
        json={
            "prompt": prompt,
            "image_size": {"width": config.PIN_WIDTH, "height": config.PIN_HEIGHT},
            "num_images": 1,
        },
        timeout=120,
    )
    resp.raise_for_status()
    image_url = resp.json()["images"][0]["url"]
    img_bytes = requests.get(image_url, timeout=60).content
    return Image.open(io.BytesIO(img_bytes))


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
    if config.GEMINI_API_KEY:
        try:
            img = _generate_gemini(prompt)
            ui.log("IMAGE", "generated via Gemini (nano banana, free tier)")
            return img
        except Exception as e:
            ui.log("WARN", f"Gemini image gen failed ({e}) — falling back")
    if config.FAL_API_KEY:
        try:
            img = _generate_fal(prompt)
            ui.log("IMAGE", "generated via fal.ai flux/schnell (paid fallback)")
            return img
        except Exception as e:
            ui.log("WARN", f"fal.ai image gen failed ({e}) — using mock placeholder")
    return _generate_placeholder(prompt, reason="no working image backend")


def generate_pin_image(prompt: str, product_id: str, variation: int) -> str:
    img = _generate_placeholder(prompt) if MOCK else _generate_with_fallback(prompt)
    img = crop_to_pin(img)
    path = config.IMAGES_DIR / f"{product_id}_v{variation}.jpg"
    img.save(path, "JPEG", quality=90)
    return str(path)
