"""Agent-style console UI on top of rich: colored tag log, progress, summary table.

Also supports a pluggable "sink" so a caller (e.g. the web backend) can capture
log events as plain structured data (tag, message, timestamp) for streaming to
a browser, without touching how the CLI itself behaves. The sink is stored in
a contextvar so concurrent runs (each in its own thread) don't leak into each
other's stream — see `use_sink()`.
"""
import contextvars
import re
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TaskProgressColumn,
                           TextColumn)
from rich.table import Table

console = Console()

TAG_STYLES = {
    "SYSTEM": "bold cyan",
    "SCOUT": "bold magenta",
    "FEED": "bold green",
    "CLAUDE": "bold blue",
    "IMAGE": "bold yellow",
    "UPLOAD": "bold bright_blue",
    "DB": "dim white",
    "WARN": "bold red",
}

_sink_var: contextvars.ContextVar = contextvars.ContextVar("ui_sink", default=None)
_MARKUP_RE = re.compile(r"\[/?[a-zA-Z_ ]*\]")


def _plain(text: str) -> str:
    """Strip rich markup (e.g. [bold]...[/bold]) for plain-text consumers."""
    return _MARKUP_RE.sub("", text)


class use_sink:
    """Context manager: within this block, every log() call is also forwarded
    to `callback(tag, plain_message, timestamp)`. Safe for concurrent runs as
    long as each run's thread is started via a copied context, e.g.:

        ctx = contextvars.copy_context()
        threading.Thread(target=ctx.run, args=(pipeline.run, ...)).start()
    """

    def __init__(self, callback):
        self.callback = callback
        self._token = None

    def __enter__(self):
        self._token = _sink_var.set(self.callback)
        return self

    def __exit__(self, *exc):
        _sink_var.reset(self._token)


def log(tag: str, message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    style = TAG_STYLES.get(tag, "white")
    console.print(f"[dim]{ts}[/dim] [{style}]\\[{tag}][/{style}] {message}")
    sink = _sink_var.get()
    if sink is not None:
        sink(tag, _plain(message), ts)


def banner(title: str, subtitle: str = ""):
    body = f"[bold bright_white]{title}[/bold bright_white]"
    if subtitle:
        body += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(body, border_style="magenta", expand=False))


def progress() -> Progress:
    return Progress(
        SpinnerColumn(style="magenta"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="magenta", finished_style="green"),
        TaskProgressColumn(),
        console=console,
    )


def summary_table(rows: list[dict]):
    """rows: [{product, price, images, pins, board, status}]"""
    table = Table(title="Pipeline summary", border_style="dim")
    table.add_column("Product", max_width=40)
    table.add_column("Price", justify="right")
    table.add_column("Images", justify="right")
    table.add_column("Pins", justify="right")
    table.add_column("Board")
    table.add_column("Status")
    for r in rows:
        status_style = "green" if r["status"] == "posted" else "yellow"
        table.add_row(
            r["product"], f"${r['price']:.2f}", str(r["images"]),
            str(r["pins"]), r["board"],
            f"[{status_style}]{r['status']}[/{status_style}]",
        )
    console.print(table)
