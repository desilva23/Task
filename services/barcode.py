"""Barcodes — the digits checked (lld.md §8.5, FR-03).

Decoding happens on the phone, in the page; the server receives digits only and checks them
again here, because the page is not trusted to have decoded honestly. No lookup here either: a
barcode is an identifier, so what to do with one is the catalogue's question.
"""


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
