"""Локальна статистика пайплайна — скільки пінів за день/місяць, топ бордів.
Усе з pipeline.db, без жодного зовнішнього API (impressions/дохід з Pinterest
чи Temu сюди не входять — це вимагає живого доступу до їхніх дашбордів,
якого поки немає).

Приклад:
    python stats.py
    python stats.py --days 14 --months 6
"""
import argparse
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from rich import box
from rich.table import Table

import db
import ui

LABEL_WIDTH = 22


def _fmt_label(label: str) -> str:
    label = str(label)
    if len(label) > LABEL_WIDTH:
        return label[:LABEL_WIDTH - 1] + "…"
    return label.rjust(LABEL_WIDTH)


def _bar_chart(rows: list[dict], label_key: str, value_key: str, width: int = 36):
    if not rows:
        ui.console.print("  [dim]Немає даних за цей період.[/dim]")
        return
    max_val = max(r[value_key] for r in rows) or 1
    for r in rows:
        bar_len = max(1, int((r[value_key] / max_val) * width)) if r[value_key] else 0
        bar = "█" * bar_len + "░" * (width - bar_len)
        ui.console.print(f"  [dim]{_fmt_label(r[label_key])}[/dim] │ "
                        f"[magenta]{bar}[/magenta] [bold]{r[value_key]}[/bold]")


def main(days: int, months: int):
    ui.banner("PIN PIPELINE — STATS", "локальна статистика з pipeline.db")

    t = db.totals()
    table = Table(title="Загалом", border_style="dim", box=box.ROUNDED,
                  header_style="bold magenta", title_style="bold bright_white")
    table.add_column("Метрика")
    table.add_column("Значення", justify="right")
    table.add_row("Пінів створено (усього)", str(t["total_pins"]))
    table.add_row("З них реально опубліковано", f"[green]{t['live_pins']}[/green]")
    table.add_row("Dry-run (тест)", f"[yellow]{t['dry_run_pins']}[/yellow]")
    table.add_row("Унікальних продуктів опубліковано", str(t["posted_products"]))
    ui.console.print(table)

    ui.console.print(f"\n  {ui.BRAND_MARK} [bold]Піни за останні {days} днів[/bold]")
    _bar_chart(db.pins_per_day(days), "date", "count")

    ui.console.print(f"\n  {ui.BRAND_MARK} [bold]Піни за останні {months} місяців[/bold]")
    _bar_chart(db.pins_per_month(months), "month", "count")

    if t["top_boards"]:
        ui.console.print(f"\n  {ui.BRAND_MARK} [bold]Топ бордів за кількістю пінів[/bold]")
        _bar_chart(t["top_boards"], "board", "count")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Локальна статистика pin_pipeline")
    ap.add_argument("--days", type=int, default=30, help="скільки останніх днів показати")
    ap.add_argument("--months", type=int, default=12, help="скільки останніх місяців показати")
    args = ap.parse_args()
    main(args.days, args.months)
