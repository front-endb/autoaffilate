"""FastAPI backend for the pin_pipeline web UI.

Run from the pin_pipeline directory:
    python -m uvicorn webapp.main:app --reload --port 8000
Then open http://localhost:8000
"""
import sys
from pathlib import Path

# Sibling modules (config.py, ui.py, pipeline.py, ...) live one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import queue
import threading
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

import claude_client
import config
import db
import image_gen
import pinterest_client
import pipeline
import temu_feed
import ui
from webapp.schemas import FeedPreviewRequest, RunRequest, SettingsPayload, TrendsPayload

app = FastAPI(title="Pin Pipeline")

# run_id -> {"queue": Queue, "status": "running"|"done"|"error", "summary": [...], "error": str}
_runs: dict[str, dict] = {}

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


@app.get("/api/status")
def get_status():
    return {
        "claude": "mock" if claude_client.MOCK else "live",
        "image_gen": "mock" if image_gen.MOCK else "live",
        "pinterest": "mock" if pinterest_client.MOCK else "live",
        "trends_path": str(config.TRENDS_PATH),
        "trends_exists": config.TRENDS_PATH.exists(),
        "sample_feed_path": str(config.SAMPLE_FEED_PATH),
    }


@app.get("/api/trends")
def get_trends():
    data = json.loads(config.TRENDS_PATH.read_text(encoding="utf-8"))
    return {"trends": data.get("trends", [])}


@app.put("/api/trends")
def put_trends(payload: TrendsPayload):
    existing = {}
    if config.TRENDS_PATH.exists():
        existing = json.loads(config.TRENDS_PATH.read_text(encoding="utf-8"))
    existing["trends"] = [t.model_dump() for t in payload.trends]
    config.TRENDS_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"ok": True, "count": len(payload.trends)}


@app.post("/api/feed/upload")
async def upload_feed(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".csv", ".json")):
        raise HTTPException(400, "Підтримуються тільки .csv і .json фіди")
    dest = config.FEEDS_DIR / file.filename
    dest.write_bytes(await file.read())
    try:
        df = temu_feed.load_feed(dest)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"feed_path": str(dest), "columns": list(df.columns), "row_count": len(df)}


@app.get("/api/feed/list")
def list_feeds():
    feeds = [str(p) for p in config.FEEDS_DIR.glob("*") if p.suffix in (".csv", ".json")]
    feeds.insert(0, str(config.SAMPLE_FEED_PATH))
    return {"feeds": feeds}


@app.post("/api/feed/preview")
def preview_feed(payload: FeedPreviewRequest):
    try:
        df = temu_feed.load_feed(payload.feed_path)
    except Exception as e:
        raise HTTPException(400, str(e))
    products = temu_feed.filter_products(df, category=payload.trend, limit=payload.limit)
    return jsonable_encoder({"count": len(products), "products": products})


def _execute_run(run_id: str, payload: RunRequest):
    q = _runs[run_id]["queue"]

    def sink(tag, message, ts):
        q.put({"type": "log", "tag": tag, "message": message, "ts": ts})

    categories = payload.trends if payload.trends else payload.trend
    try:
        with ui.use_sink(sink):
            summary = pipeline.run(payload.feed_path, categories, payload.limit, payload.post)
        _runs[run_id]["status"] = "done"
        _runs[run_id]["summary"] = summary or []
        q.put({"type": "done", "summary": jsonable_encoder(summary or [])})
    except Exception as e:
        _runs[run_id]["status"] = "error"
        _runs[run_id]["error"] = str(e)
        q.put({"type": "error", "message": str(e)})
    finally:
        q.put(None)  # sentinel: closes the SSE stream


@app.post("/api/run")
def start_run(payload: RunRequest):
    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {"queue": queue.Queue(), "status": "running", "summary": None, "error": None}
    threading.Thread(target=_execute_run, args=(run_id, payload), daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/run/{run_id}")
def get_run(run_id: str):
    if run_id not in _runs:
        raise HTTPException(404, "run_id not found")
    r = _runs[run_id]
    return {"status": r["status"], "summary": jsonable_encoder(r["summary"]), "error": r["error"]}


@app.get("/api/run/{run_id}/stream")
def stream_run(run_id: str):
    if run_id not in _runs:
        raise HTTPException(404, "run_id not found")
    q = _runs[run_id]["queue"]

    def gen():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _write_env_var(key: str, value: str):
    """Update KEY=value in .env (append if missing)."""
    env_path = config.BASE_DIR / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.get("/api/settings")
def get_settings():
    return {
        "ANTHROPIC_API_KEY": bool(config.ANTHROPIC_API_KEY),
        "PINTEREST_ACCESS_TOKEN": bool(config.PINTEREST_ACCESS_TOKEN),
        "PINTEREST_APP_ID": bool(config.PINTEREST_APP_ID),
        "PINTEREST_APP_SECRET": bool(config.PINTEREST_APP_SECRET),
        "redirect_uri": config.PINTEREST_REDIRECT_URI,
    }


@app.post("/api/settings")
def post_settings(payload: SettingsPayload):
    updated = [k for k, v in payload.model_dump(exclude_none=True).items() if v]
    for key in updated:
        _write_env_var(key, getattr(payload, key))
    return {
        "updated": updated,
        "note": "Перезапусти сервер (Ctrl+C і запусти знову), щоб нові ключі підхопились."
                if updated else "Нічого не змінено — поля були порожні.",
    }


@app.get("/api/pinterest/auth-url")
def pinterest_auth_url():
    if not config.PINTEREST_APP_ID or not config.PINTEREST_APP_SECRET:
        raise HTTPException(400, "Спочатку заповни PINTEREST_APP_ID і PINTEREST_APP_SECRET у Settings")
    return {"auth_url": pinterest_client.auth_url(), "redirect_uri": config.PINTEREST_REDIRECT_URI}


@app.get("/api/pinterest/callback")
def pinterest_callback(code: str = ""):
    if not code:
        raise HTTPException(400, "Немає параметра code в редіректі")
    try:
        tokens = pinterest_client.exchange_code(code)
    except Exception as e:
        raise HTTPException(400, f"Обмін коду на токен не вдався: {e}")
    _write_env_var("PINTEREST_ACCESS_TOKEN", tokens["access_token"])
    return HTMLResponse(
        "<body style='font-family:sans-serif;padding:2rem'>"
        "<h3>Pinterest підключено</h3>"
        "<p>Access token збережено в .env. Перезапусти сервер і онови сторінку Settings.</p>"
        "</body>"
    )


@app.get("/api/history")
def get_history(limit: int = 200):
    return {
        "pins": db.recent_pins(limit),
        "posted_products": db.posted_products(limit),
    }


@app.get("/favicon.ico")
def favicon():
    return FileResponse(STATIC_DIR / "favicon.ico")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": "index.html not found yet — frontend not built"}
