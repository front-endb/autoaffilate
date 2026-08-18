"""SQLite storage: dedup of posted products + log of created pins."""
import sqlite3
from datetime import datetime, timezone

import config


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_products (
            product_id TEXT PRIMARY KEY,
            title TEXT,
            posted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            pin_id TEXT,
            board_id TEXT,
            board_name TEXT,
            title TEXT,
            image_path TEXT,
            created_at TEXT,
            dry_run INTEGER DEFAULT 0
        )
    """)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(pins)").fetchall()]
    if "board_name" not in cols:
        conn.execute("ALTER TABLE pins ADD COLUMN board_name TEXT")
    return conn


def is_posted(product_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_products WHERE product_id = ?", (product_id,)
        ).fetchone()
    return row is not None


def mark_posted(product_id: str, title: str):
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_products (product_id, title, posted_at) VALUES (?, ?, ?)",
            (product_id, title, datetime.now(timezone.utc).isoformat()),
        )


def log_pin(product_id: str, pin_id: str, board_id: str, title: str,
            image_path: str, dry_run: bool = False, board_name: str = ""):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO pins (product_id, pin_id, board_id, board_name, title, "
            "image_path, created_at, dry_run) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (product_id, pin_id, board_id, board_name or board_id, title, image_path,
             datetime.now(timezone.utc).isoformat(), int(dry_run)),
        )


def recent_pins(limit: int = 200) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, product_id, pin_id, board_id, board_name, title, image_path, "
            "created_at, dry_run FROM pins ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def posted_products(limit: int = 200) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT product_id, title, posted_at FROM posted_products "
            "ORDER BY posted_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def pins_per_day(days: int = 30) -> list[dict]:
    """[{date, count}, ...] за останні `days` днів, від найстарішого до найновішого."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS count "
            "FROM pins WHERE created_at >= date('now', ?) "
            "GROUP BY date ORDER BY date",
            (f"-{days} days",),
        ).fetchall()
    return [{"date": r[0], "count": r[1]} for r in rows]


def pins_per_month(months: int = 12) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS count "
            "FROM pins WHERE created_at >= date('now', ?) "
            "GROUP BY month ORDER BY month",
            (f"-{months} months",),
        ).fetchall()
    return [{"month": r[0], "count": r[1]} for r in rows]


def totals() -> dict:
    with _connect() as conn:
        total_pins = conn.execute("SELECT COUNT(*) FROM pins").fetchone()[0]
        live_pins = conn.execute("SELECT COUNT(*) FROM pins WHERE dry_run = 0").fetchone()[0]
        total_products = conn.execute("SELECT COUNT(*) FROM posted_products").fetchone()[0]
        by_board = conn.execute(
            "SELECT COALESCE(NULLIF(board_name, ''), board_id) AS name, COUNT(*) AS c "
            "FROM pins GROUP BY name ORDER BY c DESC LIMIT 10"
        ).fetchall()
    return {
        "total_pins": total_pins,
        "live_pins": live_pins,
        "dry_run_pins": total_pins - live_pins,
        "posted_products": total_products,
        "top_boards": [{"board": b, "count": c} for b, c in by_board],
    }
