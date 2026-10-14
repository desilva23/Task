"""Photos for the scan tests: a barcode rendered by zxing-cpp, then put through what a phone
camera does to it — a larger frame, a tilt, blur, JPEG. Built per test, so no image is committed."""

import io

import numpy as np
import zxingcpp
from PIL import Image, ImageFilter

EAN13 = zxingcpp.BarcodeFormat.EAN13


def barcode_image(code: str, fmt=EAN13, scale: int = 3) -> Image.Image:
    rendered = zxingcpp.create_barcode(code, fmt).to_image(scale=scale, add_quiet_zones=True)
    return Image.fromarray(np.array(rendered)).convert("RGB")


def snapshot(*codes, size=(1280, 720), tilt=0.0, blur=0.0, fmt=EAN13, scale=3) -> bytes:
    """A JPEG frame holding each code side by side, as a camera would hand it over."""
    frame = Image.new("RGB", size, (236, 232, 224))
    x = 60
    for code in codes:
        bar = barcode_image(code, fmt, scale).rotate(tilt, expand=True, fillcolor="white")
        frame.paste(bar, (x, (size[1] - bar.height) // 2))
        x += bar.width + 60
    if blur:
        frame = frame.filter(ImageFilter.GaussianBlur(blur))
    out = io.BytesIO()
    frame.save(out, "JPEG", quality=85)
    return out.getvalue()


def blank(size=(1280, 720)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, "white").save(out, "JPEG")
    return out.getvalue()
