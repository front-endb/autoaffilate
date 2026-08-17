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
The goal is a warm, casual product lifestyle photo for Pinterest.
The image will be clearly labeled as AI-generated in the pin description,
so do NOT try to hide that — just make it attractive and on-trend.
Return a JSON array of prompt strings, nothing else."""

IMAGE_PROMPT_USER = """Product: {title}
Trend aesthetic: {aesthetic}
Possible surfaces: {surfaces}
Lighting: {lighting}
Background elements to optionally include: {background}

Write {n} distinct image prompts. Each prompt: the product on one of the
surfaces, the given lighting, cozy lived-in feel, casual smartphone-photo
framing, vertical 2:3 composition, no text, no watermarks, no brand logos.
Vary surface/angle/background between prompts."""


PIN_COPY_SYSTEM = """You are a Pinterest SEO copywriter. Return only JSON:
{
  "title": "max 100 chars, keyword-rich, natural",
  "description": "max 400 chars, friendly and helpful, naturally includes target keywords, no hashtag spam, no hype words",
  "hashtags": ["5 relevant hashtags without #"],
  "board_suggestions": ["3 board names"]
}"""

PIN_COPY_USER = """Product: {title}
Price: ${price}
Trending category: {category}
Target keywords: {keywords}"""


def generate_image_prompts(product: dict, trend: dict,
                           n: int = config.VARIATIONS_PER_PRODUCT) -> list[str]:
    if MOCK:
        return [
            f"{product['title']} on {surface}, {trend['lighting']}, "
            f"{trend['aesthetic']}, casual smartphone photo, vertical 2:3, "
            f"cozy lived-in scene with {random.choice(trend['background_elements'])}, "
            f"no text, no logos"
            for surface in random.sample(trend["surfaces"], k=min(n, len(trend["surfaces"])))
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
            "board_suggestions": [trend["category"].title(), "Home Finds", "Budget Decor"],
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
