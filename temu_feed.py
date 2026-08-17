"""Load and filter the Temu affiliate product feed (CSV/JSON export from the
affiliate dashboard). No scraping — only the official feed file."""
import json
from pathlib import Path

import pandas as pd

import config
import db


def load_feed(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        df = pd.DataFrame(raw if isinstance(raw, list) else raw.get("products", []))
    else:
        df = pd.read_csv(path)

    # Normalize column names to internal ones via FEED_COLUMN_MAP
    rename = {v: k for k, v in config.FEED_COLUMN_MAP.items() if v in df.columns}
    df = df.rename(columns=rename)

    missing = [k for k in config.FEED_COLUMN_MAP if k not in df.columns]
    if missing:
        raise ValueError(
            f"У фіді немає колонок: {missing}. "
            f"Онови FEED_COLUMN_MAP у config.py під реальні назви колонок фіду."
        )

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["sold_count"] = pd.to_numeric(df["sold_count"], errors="coerce")
    df["commission_pct"] = pd.to_numeric(df["commission_pct"], errors="coerce")
    return df.dropna(subset=["price", "affiliate_url", "title"])


def filter_products(df: pd.DataFrame, category: str | None = None,
                    limit: int = 10) -> list[dict]:
    mask = (
        (df["price"] <= config.MAX_PRICE_USD)
        & (df["sold_count"] >= config.MIN_SOLD_COUNT)
        & (df["commission_pct"] >= config.MIN_COMMISSION_PCT)
    )
    if category:
        mask &= df["category"].str.contains(category, case=False, na=False)

    selected = df[mask].sort_values("commission_pct", ascending=False)

    products = []
    for _, row in selected.iterrows():
        if db.is_posted(str(row["product_id"])):
            continue  # уже постили — пропускаємо
        products.append(row.to_dict())
        if len(products) >= limit:
            break
    return products
