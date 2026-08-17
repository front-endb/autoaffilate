"""Записує один запуск пайплайна в HTML (для прев'ю, як виглядає консоль)."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console

import ui

ui.console = Console(record=True, force_terminal=True, width=95)

import config
import pipeline

pipeline.run(str(config.SAMPLE_FEED_PATH), "bathroom organization", 2, False)

import re

from rich.terminal_theme import MONOKAI

html = ui.console.export_html(inline_styles=True, theme=MONOKAI)
body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)
# прибрати проміжні кадри progress-бара та escape-залишки
lines = [ln for ln in body.splitlines()
         if "⠋" not in ln and "⠙" not in ln and "⠹" not in ln]
body = "\n".join(lines).replace("[2K", "").replace("[2K", "")

out = config.OUTPUT_DIR / "demo_body.html"
out.write_text(body, encoding="utf-8")
print(f"saved: {out}")
