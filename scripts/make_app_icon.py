"""One-off script: generates a simple app icon for the Pinterest Developer App
(must not contain the Pinterest logo/wordmark). Flat, no gradients — matches
the pipeline's terminal-style accent color."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
BG = (22, 23, 26)          # matches webapp --bg
ACCENT = (244, 0, 95)      # matches webapp --accent (pink used for [SCOUT] etc.)
LIGHT = (246, 246, 239)    # matches webapp #f6f6ef text

img = Image.new("RGB", (SIZE, SIZE), BG)
draw = ImageDraw.Draw(img)

# Rounded square background
radius = 90
draw.rounded_rectangle([0, 0, SIZE, SIZE], radius=radius, fill=BG)

# Circular "automation loop" arc (~290°, leaving a gap) with an arrowhead
cx, cy, r = SIZE // 2, SIZE // 2, 170
stroke = 22
start_angle, end_angle = -230, 60  # degrees, PIL convention: 0=3 o'clock, clockwise
draw.arc([cx - r, cy - r, cx + r, cy + r], start=start_angle, end=end_angle,
          fill=ACCENT, width=stroke)

# Arrowhead at the end of the arc
end_rad = math.radians(end_angle)
tip_x = cx + r * math.cos(end_rad)
tip_y = cy + r * math.sin(end_rad)
tangent = end_rad + math.pi / 2  # direction of travel along the arc
head_len = 34
back_x = tip_x - head_len * math.cos(tangent)
back_y = tip_y - head_len * math.sin(tangent)
perp = tangent + math.pi / 2
half_w = 22
p1 = (tip_x, tip_y)
p2 = (back_x + half_w * math.cos(perp), back_y + half_w * math.sin(perp))
p3 = (back_x - half_w * math.cos(perp), back_y - half_w * math.sin(perp))
draw.polygon([p1, p2, p3], fill=ACCENT)

# Centered bold "A" monogram
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 200)
text = "A"
bbox = draw.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), text, font=font, fill=LIGHT)

out = Path(__file__).resolve().parent.parent / "output" / "app_icon.png"
out.parent.mkdir(exist_ok=True)
img.save(out, "PNG")
print(f"saved: {out}")
