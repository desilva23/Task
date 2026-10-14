"""Barcodes — the digits checked and a photo decoded (lld.md §8.5, FR-03).

No lookup and no page here: a barcode is an identifier, so what to do with one is the
catalogue's question, and how the photo was taken is the page's.
"""

import io

import zxingcpp
from PIL import Image, ImageOps, UnidentifiedImageError

from config import SCAN_MAX_SIDE_PX

F = zxingcpp.BarcodeFormat
RETAIL = (F.EAN13, F.EAN8, F.UPCA)  # product symbologies only — not a QR code or a label (EC-51)


def check_digit_ok(digits: str) -> bool:
    """GS1 check digit: weights 3, 1, 3, … from the right of the body. Catches every single-digit
    error and almost every swap of neighbours (EC-52)."""
    body = map(int, reversed(digits[:-1]))
    total = sum(n * (3 if i % 2 == 0 else 1) for i, n in enumerate(body))
    return (10 - total % 10) % 10 == int(digits[-1])


def normalise(digits: str) -> str | None:
    """The product code a scan or a typed entry stands for, or None if it is not one."""
    d = "".join(digits.split())
    if not d.isdigit() or len(d) not in (8, 12, 13) or not check_digit_ok(d):
        return None
    return "0" + d if len(d) == 12 else d  # UPC-A is EAN-13 with a leading zero


def decode(photo: bytes) -> list[str]:
    """Every distinct product code in a photo, in the order read. Anything unreadable — a corrupt
    or empty file, a blurred frame — is an empty list, never an exception (EC-49)."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(photo))).convert("L")
    except (UnidentifiedImageError, OSError, ValueError):
        return []
    img.thumbnail((SCAN_MAX_SIDE_PX, SCAN_MAX_SIDE_PX))
    found = zxingcpp.read_barcodes(img, formats=RETAIL)
    return list(dict.fromkeys(c for c in (normalise(b.text) for b in found) if c))
