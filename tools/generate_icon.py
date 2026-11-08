#!/usr/bin/env python3
"""
Draw the NEX launcher icon.

Two glowing cyan robot eyes on a deep black background. The foreground layer is
drawn at 108dp (the adaptive-icon safe area is the central 72dp) and the
legacy square/round icons are drawn at their normal size.

    python3 tools/generate_icon.py
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "app", "android", "app", "src", "main", "res")

CYAN = (79, 216, 255)
WHITE = (244, 252, 255)
BLACK = (6, 10, 16)

DENSITIES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}


def draw_eyes(size: int, eye_ratio: float, glow: bool = True) -> Image.Image:
    """Two rounded-square eyes with a cyan pupil, centred on black."""
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), BLACK + (255,))
    draw = ImageDraw.Draw(canvas)

    s = size * scale
    eye_w = s * eye_ratio
    eye_h = s * eye_ratio
    gap = s * eye_ratio * 1.05
    radius = eye_w * 0.3

    cy = s * 0.5
    cx_left = s * 0.5 - gap / 2 - eye_w / 2
    cx_right = s * 0.5 + gap / 2 + eye_w / 2

    boxes = []
    for cx in (cx_left, cx_right):
        boxes.append(
            (cx - eye_w / 2, cy - eye_h / 2, cx + eye_w / 2, cy + eye_h / 2)
        )

    if glow:
        halo = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        halo_draw = ImageDraw.Draw(halo)
        for box in boxes:
            halo_draw.rounded_rectangle(
                box, radius=radius, fill=CYAN + (110,)
            )
        halo = halo.filter(ImageFilter.GaussianBlur(radius=s * 0.045))
        canvas = Image.alpha_composite(canvas, halo)
        draw = ImageDraw.Draw(canvas)

    # Sclera
    for box in boxes:
        draw.rounded_rectangle(box, radius=radius, fill=WHITE + (255,))

    # Pupil
    pupil_r = eye_w * 0.27
    for box in boxes:
        pcx = (box[0] + box[2]) / 2
        pcy = (box[1] + box[3]) / 2
        draw.ellipse(
            (pcx - pupil_r, pcy - pupil_r, pcx + pupil_r, pcy + pupil_r),
            fill=(11, 27, 42, 255),
        )
        hr = pupil_r * 0.3
        draw.ellipse(
            (
                pcx - pupil_r * 0.42 - hr,
                pcy - pupil_r * 0.45 - hr,
                pcx - pupil_r * 0.42 + hr,
                pcy - pupil_r * 0.45 + hr,
            ),
            fill=(255, 255, 255, 235),
        )

    return canvas.resize((size, size), Image.LANCZOS)


def circle_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def main() -> None:
    for density, size in DENSITIES.items():
        folder = os.path.join(RES, f"mipmap-{density}")
        os.makedirs(folder, exist_ok=True)

        # Legacy square icon
        icon = draw_eyes(size, 0.30)
        icon.save(os.path.join(folder, "ic_launcher.png"))

        # Round icon
        round_icon = draw_eyes(size, 0.28)
        mask = circle_mask(size)
        round_icon.putalpha(mask)
        round_icon.save(os.path.join(folder, "ic_launcher_round.png"))

        # Adaptive foreground: 108dp canvas, eyes inside the 72dp safe zone
        fg_size = int(size * 108 / 48)
        fg = draw_eyes(fg_size, 0.185)
        fg.save(os.path.join(folder, "ic_launcher_foreground.png"))

        print(f"  mipmap-{density}: {size}px")

    # Adaptive icon background colour
    colors = os.path.join(RES, "values", "ic_launcher_background.xml")
    with open(colors, "w", encoding="utf-8") as fh:
        fh.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<resources>\n"
            '    <color name="ic_launcher_background">#060A10</color>\n'
            "</resources>\n"
        )
    print("Icon assets written.")


if __name__ == "__main__":
    main()
