"""Draw the home-screen icons (NFR-12) into public/: a white map pin on the page's teal.
Run from the repository root; the PNGs are committed, so this only reruns if the design changes."""

from pathlib import Path

from PIL import Image, ImageDraw

TEAL, WHITE = (10, 125, 116), (255, 255, 255)


def icon(size: int, path: Path, inset: float = 0.0) -> None:
    img = Image.new("RGB", (size, size), TEAL)
    d = ImageDraw.Draw(img)
    s = size * (1 - 2 * inset)  # maskable icons keep the pin inside the safe zone
    cx, top = size / 2, size * inset + s * 0.18
    r = s * 0.2
    d.ellipse([cx - r, top, cx + r, top + 2 * r], fill=WHITE)
    d.polygon(
        [(cx - r * 0.86, top + r * 1.5), (cx + r * 0.86, top + r * 1.5), (cx, top + s * 0.68)],
        fill=WHITE,
    )
    hole = r * 0.42
    d.ellipse([cx - hole, top + r - hole, cx + hole, top + r + hole], fill=TEAL)
    d.rounded_rectangle(
        [cx - s * 0.26, top + s * 0.62, cx + s * 0.26, top + s * 0.66], radius=s * 0.02, fill=WHITE
    )
    img.save(path)


if __name__ == "__main__":
    out = Path("public")
    icon(192, out / "icon-192.png")
    icon(512, out / "icon-512.png")
    icon(512, out / "icon-maskable-512.png", inset=0.1)
    icon(180, out / "apple-touch-icon.png")
