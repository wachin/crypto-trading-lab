#!/usr/bin/env python3
"""Generate the animated contributor banner for the README.

Produces ``assets/contributing-agents.gif``: a dark, modern crypto
banner with a self-drawing candlestick chart, a sweeping moving
average, an animated BTC coin and a blinking "bring your AI agent"
terminal line.

It is deterministic (fixed seed) so regenerating it does not produce
random churn. Pillow and NumPy are only needed to *regenerate* the
banner; the application itself does not depend on them.

Usage:

    python3 tools/make_banner_gif.py            # writes the GIF
    python3 tools/make_banner_gif.py --preview  # also writes a PNG frame
"""

from __future__ import annotations

import argparse
import math
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1000, 300
FRAMES = 32
FRAME_MS = 60
SEED = 20260919

ASSETS = Path(__file__).resolve().parents[1] / "assets"
GIF_PATH = ASSETS / "contributing-agents.gif"
PREVIEW_PATH = ASSETS / "contributing-agents-preview.png"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_MONO = FONT_DIR / "DejaVuSansMono.ttf"

#: Candidate fonts for the Bitcoin sign (U+20BF); DejaVu lacks it.
COIN_FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf"),
    FONT_BOLD,
)
BITCOIN_SIGN = "\u20bf"

# Palette
BG_TOP = (7, 11, 22)
BG_BOTTOM = (15, 24, 48)
GRID = (30, 42, 74)
GREEN = (38, 208, 124)
RED = (255, 92, 122)
ACCENT = (125, 211, 252)
TEXT = (234, 240, 255)
MUTED = (150, 165, 200)
GOLD = (247, 191, 62)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _has_glyph(font: ImageFont.FreeTypeFont, char: str) -> bool:
    """True when ``font`` really draws ``char`` (not the .notdef box)."""
    probe = Image.new("L", (90, 70), 0)
    ImageDraw.Draw(probe).text((5, 5), char, font=font, fill=255)
    drawn = probe.tobytes()
    if not any(drawn):
        return False
    notdef = Image.new("L", (90, 70), 0)
    ImageDraw.Draw(notdef).text((5, 5), "\uffff", font=font, fill=255)
    return drawn != notdef.tobytes()


def _load_coin_font(size: int) -> ImageFont.FreeTypeFont | None:
    """First candidate font that can draw the Bitcoin sign."""
    for path in COIN_FONT_CANDIDATES:
        if not path.exists():
            continue
        try:
            font = _font(path, size)
        except OSError:
            continue
        if _has_glyph(font, BITCOIN_SIGN):
            return font
    return None


def _gradient_background() -> Image.Image:
    """Vertical gradient plus a soft grid."""
    top = np.array(BG_TOP, dtype=np.float32)
    bottom = np.array(BG_BOTTOM, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, HEIGHT, dtype=np.float32)[:, None]
    rows = top[None, :] * (1 - ramp) + bottom[None, :] * ramp
    array = np.repeat(rows[:, None, :], WIDTH, axis=1).astype(np.uint8)
    image = Image.fromarray(array, "RGB")

    draw = ImageDraw.Draw(image, "RGBA")
    for x in range(0, WIDTH, 30):
        draw.line([(x, 0), (x, HEIGHT)], fill=(*GRID, 90))
    for y in range(0, HEIGHT, 30):
        draw.line([(0, y), (WIDTH, y)], fill=(*GRID, 70))
    return image


def _price_series(count: int) -> list[float]:
    """Deterministic candle series that rises, dips and recovers."""
    random.seed(SEED)
    prices = []
    price = 100.0
    for i in range(count):
        drift = 1.4 if i < count * 0.55 else -1.2
        if i > count * 0.78:
            drift = 1.8
        price += drift + random.uniform(-1.1, 1.1)
        prices.append(price)
    return prices


class Banner:
    """Renders every frame of the banner."""

    def __init__(self) -> None:
        self.background = _gradient_background()
        self.prices = _price_series(18)
        self.mono_small = _font(FONT_MONO, 15)
        self.bold_display = _font(FONT_BOLD, 36)
        self.bold_lead = _font(FONT_BOLD, 21)
        self.sans_small = _font(FONT_BOLD, 15)
        # ``None`` means no installed font has U+20BF; the coin then draws
        # a hand-made mark so the banner is still correct everywhere.
        self.coin_font = _load_coin_font(58)
        self.coin_fallback_font = _font(FONT_BOLD, 52)
        random.seed(SEED + 1)
        self.particles = [
            (
                random.uniform(0, WIDTH),
                random.uniform(0, HEIGHT),
                random.uniform(0.15, 0.55),
                random.uniform(0.8, 2.0),
            )
            for _ in range(34)
        ]

    # -- pieces ----------------------------------------------------------

    def _draw_chart(self, draw: ImageDraw.ImageDraw, progress: float) -> None:
        left, right = 40, 430
        top, bottom = 62, 250
        values = self.prices
        low, high = min(values) - 3, max(values) + 3
        step = (right - left) / len(values)

        def y_for(price: float) -> float:
            ratio = (price - low) / (high - low)
            return bottom - ratio * (bottom - top)

        visible = progress * len(values)
        colors = []
        for index, price in enumerate(values):
            if index > visible:
                break
            grow = min(1.0, max(0.0, visible - index))
            center_x = left + step * (index + 0.5)
            previous = values[index - 1] if index else price - 1.0
            opening = previous
            closing = previous + (price - previous) * grow
            high_price = max(opening, closing) + 1.2
            low_price = min(opening, closing) - 1.2
            colour = GREEN if closing >= opening else RED
            colors.append((center_x, opening, closing, colour))

            draw.line(
                [(center_x, y_for(high_price)), (center_x, y_for(low_price))],
                fill=colour,
                width=2,
            )
            x0, x1 = center_x - 5, center_x + 5
            y0, y1 = y_for(max(opening, closing)), y_for(min(opening, closing))
            if abs(y1 - y0) < 3:
                y1 = y0 + 3
            draw.rounded_rectangle([x0, y0, x1, y1], radius=2, fill=colour)

        # Sweeping moving average over the visible close prices.
        closes = values[: max(1, int(visible))]
        if len(closes) >= 3:
            points = []
            for index in range(2, len(closes)):
                window = closes[index - 2 : index + 1]
                points.append(
                    (
                        left + step * (index + 0.5),
                        y_for(sum(window) / len(window)),
                    )
                )
            if len(points) >= 2:
                draw.line(points, fill=(*ACCENT, 235), width=3, joint="curve")

        draw.line([(left, bottom + 6), (right, bottom + 6)], fill=(*GRID, 220), width=1)

    def _draw_coin(self, image: Image.Image, pulse: float) -> None:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx, cy, radius = 928, 92, 44 + int(2 * pulse)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*GOLD, 26),
            outline=(*GOLD, 150),
            width=2,
        )
        layer = layer.filter(ImageFilter.GaussianBlur(0.6))
        image.paste(Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB"), (0, 0))

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        alpha = 70 + int(120 * pulse)
        if self.coin_font is not None:
            box = od.textbbox((0, 0), BITCOIN_SIGN, font=self.coin_font)
            od.text(
                (
                    cx - (box[2] - box[0]) / 2 - box[0],
                    cy - (box[3] - box[1]) / 2 - box[1],
                ),
                BITCOIN_SIGN,
                font=self.coin_font,
                fill=(*GOLD, alpha),
            )
        else:
            # Hand-drawn ₿: a bold "B" with the two signature strokes.
            font = self.coin_fallback_font
            box = od.textbbox((0, 0), "B", font=font)
            width, height = box[2] - box[0], box[3] - box[1]
            left, top = cx - width / 2 - box[0], cy - height / 2 - box[1]
            od.text((left, top), "B", font=font, fill=(*GOLD, alpha))
            bar_x = left + width * 0.62
            od.line([(bar_x, top - 9), (bar_x, top + height + 9)],
                    fill=(*GOLD, alpha), width=4)
            od.line([(bar_x + 8, top - 9), (bar_x + 8, top + height + 9)],
                    fill=(*GOLD, alpha), width=4)
        image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"), (0, 0))

    def _draw_text(self, draw: ImageDraw.ImageDraw, frame: int) -> None:
        x = 470
        draw.text((x, 60), "Crypto Trading Lab", font=self.bold_display, fill=TEXT)
        draw.text((x, 118), "Bring your AI agent.", font=self.bold_lead, fill=ACCENT)
        draw.text(
            (x, 152),
            "Survive → Validate → Earn",
            font=self.sans_small,
            fill=MUTED,
        )

        prompt = "agent@lab:~$ clone · test · contribute"
        draw.text((x, 190), prompt, font=self.mono_small, fill=(190, 205, 235))
        width = draw.textlength(prompt, font=self.mono_small)
        if (frame // 3) % 2 == 0:
            cursor_y = 188
            draw.rectangle(
                [x + width + 6, cursor_y, x + width + 16, cursor_y + 18],
                fill=ACCENT,
            )

        draw.text(
            (x, 228),
            "GPL-3.0 · Debian 13 · offline test suite",
            font=self.sans_small,
            fill=(120, 138, 176),
        )

    def _draw_particles(self, draw: ImageDraw.ImageDraw, frame: int) -> None:
        phase = frame / FRAMES
        for x, y, speed, size in self.particles:
            drift = (y - phase * 26 * speed) % HEIGHT
            twinkle = 0.5 + 0.5 * math.sin(2 * math.pi * (phase + x / WIDTH))
            alpha = int(30 + 90 * twinkle)
            draw.ellipse(
                [x - size, drift - size, x + size, drift + size],
                fill=(140, 200, 255, alpha),
            )

    # -- frame -----------------------------------------------------------

    def frame(self, index: int) -> Image.Image:
        image = self.background.convert("RGBA")
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([820, 0, 1000, 200], fill=(247, 191, 62, 34))
        gd.ellipse([10, 50, 470, 290], fill=(56, 189, 248, 26))
        glow = glow.filter(ImageFilter.GaussianBlur(34))
        image = Image.alpha_composite(image, glow)

        draw = ImageDraw.Draw(image, "RGBA")
        self._draw_particles(draw, index)

        # Chart draws itself during the first ~70% of the loop, then holds.
        progress = min(1.0, index / (FRAMES * 0.7))
        self._draw_chart(draw, progress)

        base = image.convert("RGB")
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * index / FRAMES)
        self._draw_coin(base, pulse)

        draw = ImageDraw.Draw(base, "RGBA")
        self._draw_text(draw, index)
        return base


def _optimize_in_place(path: Path) -> None:
    """Shrink the GIF with ImageMagick delta-frame optimization.

    Pillow writes full frames; ImageMagick's ``-layers Optimize`` stores
    only the changes between frames (about 15x smaller). It is optional:
    without ImageMagick the Pillow file is kept as-is.
    """
    tool = shutil.which("magick") or shutil.which("convert")
    if tool is None:
        return
    temporary = path.with_name(path.stem + ".optimized.gif")
    result = subprocess.run(
        [tool, str(path), "-coalesce", "-layers", "Optimize", str(temporary)],
        capture_output=True,
        check=False,
    )
    if (
        result.returncode == 0
        and temporary.exists()
        and temporary.stat().st_size < path.stat().st_size
    ):
        temporary.replace(path)
    else:
        temporary.unlink(missing_ok=True)


def build_gif() -> Path:
    banner = Banner()
    frames = [banner.frame(i) for i in range(FRAMES)]
    # The palette must come from a *fully drawn* frame: frame 0 has an
    # almost empty chart, so its adaptive palette lacks the candle
    # colours and the whole GIF would turn grey.
    palette = frames[-1].convert("P", palette=Image.ADAPTIVE, colors=128)
    quantized = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    ASSETS.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        GIF_PATH,
        save_all=True,
        append_images=quantized[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    _optimize_in_place(GIF_PATH)
    return GIF_PATH


def build_preview() -> Path:
    banner = Banner()
    frame = banner.frame(int(FRAMES * 0.9))
    frame.save(PREVIEW_PATH)
    return PREVIEW_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="also write a PNG frame")
    args = parser.parse_args()
    gif = build_gif()
    print(f"wrote {gif} ({gif.stat().st_size / 1024:.0f} KiB)")
    if args.preview:
        png = build_preview()
        print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
