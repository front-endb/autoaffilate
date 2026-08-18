"""Main pipeline: trend -> feed filter -> image prompts -> images -> pin copy -> Pinterest.

Приклади:
    python pipeline.py --feed sample_feed.csv --trend "desk organization" --limit 3
    python pipeline.py --feed sample_feed.csv            # перший тренд з trends.json
    python pipeline.py --feed sample_feed.csv --trend "desk organization" --trend "bathroom organization"
    python pipeline.py --feed sample_feed.csv --all-trends
    python pipeline.py --feed real_feed.csv --post       # реальний постинг (потрібен токен)

Без --post нічого не публікується — тільки генерація і лог у консоль/БД.
Кожен пін поститься на ВСІ запропоновані Claude борди (не тільки перший) —
так само, як у оригінальному пайплайні, під який це писалось.
"""
import argparse
import json
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import claude_client
import config
import db
import image_gen
import pinterest_client
import temu_feed
import ui


def _resolve_trends(categories: str | list[str] | None) -> list[dict]:
    all_trends = json.loads(config.TRENDS_PATH.read_text(encoding="utf-8"))["trends"]
    if categories is None:
        return [all_trends[0]]
    if categories == "__all__":
        return all_trends
    if isinstance(categories, str):
        categories = [categories]
    by_name = {t["category"].lower(): t for t in all_trends}
    resolved = []
    for c in categories:
        t = by_name.get(c.lower())
        if not t:
            raise SystemExit(f"Тренд '{c}' не знайдено у trends.json")
        resolved.append(t)
    return resolved


def _run_for_trend(trend: dict, feed_path: str, limit: int, post: bool, dry_run: bool) -> list[dict]:
    ui.log("SCOUT", f"Trend loaded: [bold]{trend['category']}[/bold] "
                    f"({', '.join(trend['keywords'][:3])})")

    df = temu_feed.load_feed(feed_path)
    ui.log("FEED", f"Feed loaded: {len(df)} products")
    products = temu_feed.filter_products(df, category=trend["category"], limit=limit)
    ui.log("FEED", f"After filters (price<=${config.MAX_PRICE_USD:.0f}, "
                   f"sold>={config.MIN_SOLD_COUNT}, comm>={config.MIN_COMMISSION_PCT:.0f}%): "
                   f"[bold]{len(products)}[/bold] products")
    if not products:
        ui.log("WARN", f"[{trend['category']}] Нема продуктів під фільтри — "
                       "онови фід або посла́б фільтри в config.py")
        return []

    summary = []
    for product in products:
        pid = str(product["product_id"])
        ui.log("SCOUT", f"Product: [bold]{product['title']}[/bold] "
                        f"(${product['price']:.2f}, {int(product['sold_count']):,} sold, "
                        f"{product['commission_pct']:.0f}% comm)")

        prompts = claude_client.generate_image_prompts(product, trend)
        ui.log("CLAUDE", f"{len(prompts)} image prompts generated")
        copy = claude_client.generate_pin_copy(product, trend)
        ui.log("CLAUDE", f"Pin copy ready: \"{copy['title'][:60]}\"")

        hashtag_line = " ".join(f"#{h}" for h in copy.get("hashtags", []))
        description = f"{copy['description']}\n\n{hashtag_line}\n\n{config.DISCLOSURE_TEXT}".strip()

        boards = [pinterest_client.get_or_create_board(name)
                  for name in copy["board_suggestions"]]
        ui.log("UPLOAD", f"Target boards: {', '.join(b['name'] for b in boards)}")

        pins_created = 0
        total_posts = len(prompts) * len(boards)
        with ui.progress() as prog:
            task = prog.add_task(f"[magenta]{pid}[/magenta] generating pins", total=total_posts)
            for i, prompt in enumerate(prompts):
                image_path = image_gen.generate_pin_image(prompt, pid, i)
                for j, board in enumerate(boards):
                    pin_id = pinterest_client.create_pin(
                        board_id=board["id"],
                        title=copy["title"],
                        description=description,
                        link=product["affiliate_url"],
                        image_path=image_path,
                    )
                    db.log_pin(pid, pin_id, board["id"], copy["title"], image_path,
                               dry_run=dry_run, board_name=board["name"])
                    pins_created += 1
                    prog.advance(task)
                    is_last = (i == len(prompts) - 1) and (j == len(boards) - 1)
                    if not dry_run and not is_last:
                        ui.log("SYSTEM", f"Cooldown {config.SECONDS_BETWEEN_PINS}s before next board post")
                        time.sleep(config.SECONDS_BETWEEN_PINS)

        if not dry_run:
            db.mark_posted(pid, product["title"])
            ui.log("DB", f"{pid} marked as posted")

        summary.append({
            "product": product["title"], "price": product["price"],
            "images": len(prompts), "pins": pins_created,
            "board": ", ".join(b["name"] for b in boards),
            "status": "posted" if not dry_run else "dry-run",
        })

    return summary


def run(feed_path: str, categories: str | list[str] | None = None,
        limit: int = 3, post: bool = False) -> list[dict]:
    ui.banner("PIN PIPELINE", "trend -> feed -> claude -> images -> pinterest")
    ui.log("SYSTEM", "Pipeline initialized. Starting cycle")

    trends = _resolve_trends(categories)
    ui.log("SYSTEM", f"Processing {len(trends)} trend(s): "
                     f"{', '.join(t['category'] for t in trends)}")

    dry_run = not post or pinterest_client.MOCK
    if post and pinterest_client.MOCK:
        ui.log("WARN", "--post вказано, але PINTEREST_ACCESS_TOKEN порожній — dry-run")
    mode = "[green]LIVE POSTING[/green]" if not dry_run else "[yellow]DRY-RUN[/yellow]"
    ui.log("SYSTEM", f"Mode: {mode} | Claude: {'mock' if claude_client.MOCK else 'live'} "
                     f"| Images: {'mock' if image_gen.MOCK else 'live'}")

    summary = []
    for trend in trends:
        summary.extend(_run_for_trend(trend, feed_path, limit, post, dry_run))

    ui.summary_table(summary)
    ui.log("SYSTEM", f"Done. Images -> {config.IMAGES_DIR}")
    if dry_run:
        ui.log("SYSTEM", "Dry-run: нічого не опубліковано. Додай ключі в .env і прапор --post")

    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pinterest affiliate pin pipeline")
    ap.add_argument("--feed", default=str(config.SAMPLE_FEED_PATH),
                    help="шлях до фіду Temu (CSV/JSON)")
    ap.add_argument("--trend", action="append", default=None,
                    help="категорія з trends.json; можна вказати кілька разів "
                         "(--trend a --trend b) щоб обробити декілька трендів за раз")
    ap.add_argument("--all-trends", action="store_true",
                    help="обробити всі тренди з trends.json за один запуск")
    ap.add_argument("--limit", type=int, default=3, help="максимум продуктів за запуск на тренд")
    ap.add_argument("--post", action="store_true",
                    help="реально публікувати в Pinterest (без прапора — dry-run)")
    args = ap.parse_args()
    categories = "__all__" if args.all_trends else args.trend
    run(args.feed, categories, args.limit, args.post)
