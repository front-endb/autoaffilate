"""Main pipeline: trend -> feed filter -> image prompts -> images -> pin copy -> Pinterest.

Приклади:
    python pipeline.py --feed sample_feed.csv --trend "desk organization" --limit 3
    python pipeline.py --feed sample_feed.csv            # перший тренд з trends.json
    python pipeline.py --feed real_feed.csv --post       # реальний постинг (потрібен токен)

Без --post нічого не публікується — тільки генерація і лог у консоль/БД.
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


def load_trend(category: str | None) -> dict:
    trends = json.loads(config.TRENDS_PATH.read_text(encoding="utf-8"))["trends"]
    if category:
        for t in trends:
            if t["category"].lower() == category.lower():
                return t
        raise SystemExit(f"Тренд '{category}' не знайдено у trends.json")
    return trends[0]


def run(feed_path: str, category: str | None, limit: int, post: bool):
    ui.banner("PIN PIPELINE", "trend -> feed -> claude -> images -> pinterest")
    ui.log("SYSTEM", "Pipeline initialized. Starting cycle")

    trend = load_trend(category)
    ui.log("SCOUT", f"Trend loaded: [bold]{trend['category']}[/bold] "
                    f"({', '.join(trend['keywords'][:3])})")

    df = temu_feed.load_feed(feed_path)
    ui.log("FEED", f"Feed loaded: {len(df)} products")
    products = temu_feed.filter_products(df, category=trend["category"], limit=limit)
    ui.log("FEED", f"After filters (price<=${config.MAX_PRICE_USD:.0f}, "
                   f"sold>={config.MIN_SOLD_COUNT}, comm>={config.MIN_COMMISSION_PCT:.0f}%): "
                   f"[bold]{len(products)}[/bold] products")
    if not products:
        ui.log("WARN", "Нема продуктів під фільтри — онови фід або посла́б фільтри в config.py")
        return []

    dry_run = not post or pinterest_client.MOCK
    if post and pinterest_client.MOCK:
        ui.log("WARN", "--post вказано, але PINTEREST_ACCESS_TOKEN порожній — dry-run")
    mode = "[green]LIVE POSTING[/green]" if not dry_run else "[yellow]DRY-RUN[/yellow]"
    ui.log("SYSTEM", f"Mode: {mode} | Claude: {'mock' if claude_client.MOCK else 'live'} "
                     f"| Images: {'mock' if image_gen.MOCK else 'live'}")

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
        description = f"{copy['description']}\n\n{config.DISCLOSURE_TEXT}"

        board = pinterest_client.get_or_create_board(copy["board_suggestions"][0])
        ui.log("UPLOAD", f"Target board: {board['name']}")

        pins_created = 0
        with ui.progress() as prog:
            task = prog.add_task(f"[magenta]{pid}[/magenta] generating pins",
                                 total=len(prompts))
            for i, prompt in enumerate(prompts):
                image_path = image_gen.generate_pin_image(prompt, pid, i)
                pin_id = pinterest_client.create_pin(
                    board_id=board["id"],
                    title=copy["title"],
                    description=description,
                    link=product["affiliate_url"],
                    image_path=image_path,
                )
                db.log_pin(pid, pin_id, board["id"], copy["title"], image_path,
                           dry_run=dry_run)
                pins_created += 1
                prog.advance(task)
                if not dry_run and i < len(prompts) - 1:
                    ui.log("SYSTEM", f"Cooldown {config.SECONDS_BETWEEN_PINS}s before next pin")
                    time.sleep(config.SECONDS_BETWEEN_PINS)

        if not dry_run:
            db.mark_posted(pid, product["title"])
            ui.log("DB", f"{pid} marked as posted")

        summary.append({
            "product": product["title"], "price": product["price"],
            "images": len(prompts), "pins": pins_created,
            "board": board["name"],
            "status": "posted" if not dry_run else "dry-run",
        })

    ui.summary_table(summary)
    ui.log("SYSTEM", f"Done. Images -> {config.IMAGES_DIR}")
    if dry_run:
        ui.log("SYSTEM", "Dry-run: нічого не опубліковано. Додай ключі в .env і прапор --post")

    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pinterest affiliate pin pipeline")
    ap.add_argument("--feed", default=str(config.SAMPLE_FEED_PATH),
                    help="шлях до фіду Temu (CSV/JSON)")
    ap.add_argument("--trend", default=None, help="категорія з trends.json")
    ap.add_argument("--limit", type=int, default=3, help="максимум продуктів за запуск")
    ap.add_argument("--post", action="store_true",
                    help="реально публікувати в Pinterest (без прапора — dry-run)")
    args = ap.parse_args()
    run(args.feed, args.trend, args.limit, args.post)
