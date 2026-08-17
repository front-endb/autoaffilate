"""Central config. All keys are optional — modules fall back to mock mode when missing."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
FAL_API_KEY = os.getenv("FAL_API_KEY", "").strip()
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
PINTEREST_APP_ID = os.getenv("PINTEREST_APP_ID", "").strip()
PINTEREST_APP_SECRET = os.getenv("PINTEREST_APP_SECRET", "").strip()
PINTEREST_REDIRECT_URI = os.getenv(
    "PINTEREST_REDIRECT_URI", "http://localhost:8000/api/pinterest/callback"
)

CLAUDE_MODEL = "claude-sonnet-5"

# --- Product feed filtering ---
MAX_PRICE_USD = 15.0
MIN_SOLD_COUNT = 10_000
MIN_COMMISSION_PCT = 10.0

# Temu affiliate feed column names vary; adjust this mapping to the real feed
# once you have access to the dashboard export. Keys = our internal names,
# values = column names in the feed file.
FEED_COLUMN_MAP = {
    "product_id": "product_id",
    "title": "title",
    "price": "price",
    "sold_count": "sold_count",
    "commission_pct": "commission_pct",
    "affiliate_url": "affiliate_url",
    "category": "category",
    "image_url": "image_url",
}

# --- Image generation ---
VARIATIONS_PER_PRODUCT = 3          # 3-5; більше = дорожче й довше
PIN_WIDTH, PIN_HEIGHT = 1000, 1500  # Pinterest optimal 2:3

# Порядок спроб: Gemini має безкоштовний ліміт (rate-limited, не безмежний) —
# пробуємо його першим; коли квота вичерпається чи ключа немає, падаємо
# на платний, але дешевий fal.ai (~$0.003/зображення). Якщо й того нема —
# mock-заглушка з текстом промпта.
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

# --- Posting ---
SECONDS_BETWEEN_PINS = 300  # спокійний темп, щоб виглядати як людина, а не спам
# Обов'язковий disclosure — Pinterest/FTC вимагають позначати affiliate-контент
DISCLOSURE_TEXT = "AI-generated image. This pin contains an affiliate link — I may earn a commission."

# --- Paths ---
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
FEEDS_DIR = OUTPUT_DIR / "feeds"
DB_PATH = BASE_DIR / "pipeline.db"
TRENDS_PATH = BASE_DIR / "trends.json"
SAMPLE_FEED_PATH = BASE_DIR / "sample_feed.csv"

OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
FEEDS_DIR.mkdir(exist_ok=True)
