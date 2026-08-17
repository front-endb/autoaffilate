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
            title TEXT,
            image_path TEXT,
            created_at TEXT,
            dry_run INTEGER DEFAULT 0
        )
    """)
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
            image_path: str, dry_run: bool = False):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO pins (product_id, pin_id, board_id, title, image_path, created_at, dry_run) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, pin_id, board_id, title, image_path,
             datetime.now(timezone.utc).isoformat(), int(dry_run)),
        )


def recent_pins(limit: int = 200) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, product_id, pin_id, board_id, title, image_path, created_at, dry_run "
            "FROM pins ORDER BY id DESC LIMIT ?", (limit,)
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
