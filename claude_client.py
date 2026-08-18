"""Claude calls: image prompt generation + pin copy (title/description/hashtags).
Without ANTHROPIC_API_KEY runs in mock mode with canned output so the whole
pipeline can be tested end-to-end."""
import json
import random

import config

MOCK = not config.ANTHROPIC_API_KEY
if not MOCK:
    import anthropic
    _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _ask_claude(system: str, user: str) -> str:
    resp = _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _extract_json(text: str):
    """Claude sometimes wraps JSON in prose/code fences — cut it out."""
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start:end + 1])


IMAGE_PROMPT_SYSTEM = """You write prompts for a text-to-image model (Flux).
The goal is a photo that PASSES AS REAL user-generated content on Pinterest —
not an obviously-AI product render. Research on what actually converts on
Pinterest found three factors matter equally, all as important as product
legibility: (1) slight imperfection in the background — never a pristine,
staged scene, (2) lighting that behaves realistically for the specific
surface material, (3) a slightly off-center, asymmetric composition, like
someone casually snapped it on a phone. Perfect symmetry and clean
backgrounds are the #1 tell of AI images and kill engagement. The product
itself must still be sharp and clearly recognizable — only the background
may be soft. Return a JSON array of prompt strings, nothing else."""

IMAGE_PROMPT_USER = """Product: {title}
Trend aesthetic: {aesthetic}
Possible surfaces: {surfaces}
Lighting: {lighting}
Background elements to optionally include: {background}

Write {n} distinct image prompts. Each prompt must include ALL of:
- the product on one of the surfaces, sharp and in focus, fully recognizable
- lighting that behaves realistically for THAT surface's material (e.g. soft
  reflections on glossy/marble, matte absorption on wood/fabric) — not the
  same generic lighting description regardless of surface
- one or two small imperfect/lived-in details (a stray crumb, wrinkled
  fabric, uneven clutter) — never a pristine staged look
- a slightly off-center, asymmetric framing, like a casual phone snapshot,
  never perfectly centered/symmetric
- shot on iPhone 14, casual lifestyle photography, shallow depth of field on
  the background only, realistic product photography, vertical 2:3
  composition, no text, no watermarks, no brand logos

Vary surface, lighting angle, and background between prompts — no two
prompts should read as the same shot."""


PIN_COPY_SYSTEM = """You are a Pinterest SEO copywriter. Return only JSON:
{
  "title": "max 100 chars, keyword-rich, natural",
  "description": "max 400 chars, friendly and helpful, naturally includes target keywords, no hashtag spam, no hype words",
  "hashtags": ["5 relevant hashtags without #"],
  "board_suggestions": ["3-4 board names to pin this to"]
}"""

PIN_COPY_USER = """Product: {title}
Price: ${price}
Trending category: {category}
Target keywords: {keywords}"""


# Rotated alongside surface/background so no two variations get identical
# lighting phrasing even though trends.json only stores one base description.
_LIGHTING_MODIFIERS = [
    "{base}",
    "{base}, slightly warmer golden-hour tone",
    "{base}, slightly cooler overcast tone",
    "{base}, coming in from a slightly different angle",
    "{base}, a touch dimmer, late-afternoon feel",
]

_IMPERFECTIONS = [
    "a stray crumb or smudge nearby",
    "slightly wrinkled fabric in frame",
    "a bit of uneven clutter just visible at the edge",
    "a faint fingerprint smudge on a nearby surface",
    "papers or cables not perfectly tidy in the background",
]


def _pick_n(items: list, n: int) -> list:
    """Return exactly n items, sampling without repeats first, then
    filling any remainder with repeats so short lists still yield n."""
    if n <= len(items):
        return random.sample(items, k=n)
    return random.sample(items, k=len(items)) + random.choices(items, k=n - len(items))


def generate_image_prompts(product: dict, trend: dict,
                           n: int | None = None) -> list[str]:
    n = n or random.randint(3, 5)
    if MOCK:
        surfaces = _pick_n(trend["surfaces"], n)
        lightings = _pick_n(_LIGHTING_MODIFIERS, n)
        imperfections = _pick_n(_IMPERFECTIONS, n)
        backgrounds = _pick_n(trend["background_elements"], n)
        return [
            f"{product['title']}, sharp and in focus, clearly visible and recognizable, "
            f"placed on {surface}, {light.format(base=trend['lighting'])} that behaves "
            f"realistically for this surface's material, {trend['aesthetic']}, "
            f"slightly off-center asymmetric framing like a casual phone snapshot, "
            f"{imperfection}, cozy lived-in scene with {background} softly blurred in "
            f"the background, shot on iPhone 14, casual lifestyle photography, "
            f"shallow depth of field on the background only, product tack sharp, "
            f"realistic product photography, 8k quality, no text, no logos"
            for surface, light, imperfection, background
            in zip(surfaces, lightings, imperfections, backgrounds)
        ]
    text = _ask_claude(
        IMAGE_PROMPT_SYSTEM,
        IMAGE_PROMPT_USER.format(
            title=product["title"],
            aesthetic=trend["aesthetic"],
            surfaces=", ".join(trend["surfaces"]),
            lighting=trend["lighting"],
            background=", ".join(trend["background_elements"]),
            n=n,
        ),
    )
    return _extract_json(text)


def generate_pin_copy(product: dict, trend: dict) -> dict:
    if MOCK:
        kw = trend["keywords"][0]
        return {
            "title": f"{product['title']} — {kw} idea"[:100],
            "description": (
                f"Loving this {product['title'].lower()} for my {trend['category']} refresh. "
                f"Under ${product['price']:.0f} and it actually holds everything. "
                f"Great {kw} find."
            ),
            "hashtags": [k.replace(" ", "") for k in trend["keywords"][:5]],
            "board_suggestions": [
                trend["category"].title(), "Home Finds", "Budget Decor", "Small Space Ideas",
            ],
        }
    text = _ask_claude(
        PIN_COPY_SYSTEM,
        PIN_COPY_USER.format(
            title=product["title"],
            price=product["price"],
            category=trend["category"],
            keywords=", ".join(trend["keywords"]),
        ),
    )
    return _extract_json(text)
