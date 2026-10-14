"""FR-03 — a barcode's digits checked, and looked up exactly (lld.md §8.5). Decoding a camera
frame happens in the page and is proven in the browser tests."""

from functools import cache
from pathlib import Path

from services.barcode import check_digit_ok, normalise
from services.catalogue import Catalogue
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def store():
    return load_store(DEMO)


def barcode_of(name):
    return next(p.barcode for p in store().products.values() if p.name == name)


COKE = "Coca-Cola Classic"


class TestDigits:
    def test_fr_03_v_21_every_catalogue_barcode_is_a_valid_product_code(self):
        codes = [p.barcode for p in store().products.values() if p.barcode]
        assert codes and all(normalise(c) == c for c in codes)

    def test_fr_03_typed_digits_with_spaces_read_as_the_code(self):
        code = barcode_of(COKE)
        assert normalise(f" {code[0]} {code[1:7]} {code[7:]} ") == code

    def test_fr_03_upc_a_and_ean_8_are_product_codes(self):
        assert normalise("036000291452") == "0036000291452"  # UPC-A is EAN-13 with a leading 0
        assert normalise("96385074") == "96385074"
        assert check_digit_ok("5449000000996")

    def test_ec_52_a_failed_check_digit_or_a_wrong_length_is_not_a_barcode(self):
        code = barcode_of(COKE)
        wrong = code[:-1] + str((int(code[-1]) + 1) % 10)
        for typed in (wrong, code[:-1], code + "0", "20406348670X5", "", "   ", "12345678901234"):
            assert normalise(typed) is None, typed

    def test_ec_52_two_swapped_digits_are_caught(self):
        code = barcode_of(COKE)
        i = next(k for k in range(12) if code[k] != code[k + 1] and (k + 1) < 12)
        swapped = code[:i] + code[i + 1] + code[i] + code[i + 2 :]
        assert normalise(swapped) is None


class TestLookup:
    def test_fr_03_ec_50_the_lookup_is_exact(self):
        catalogue, code = Catalogue(store()), barcode_of(COKE)
        assert catalogue.by_barcode(code).name == COKE
        assert catalogue.by_barcode("5449000000996") is None  # valid, but not this catalogue
        assert catalogue.by_barcode(code[:8]) is None
