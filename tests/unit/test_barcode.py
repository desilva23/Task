"""FR-03 — reading a barcode: the digits checked, and a photo decoded (lld.md §8.5)."""

from functools import cache
from pathlib import Path

import zxingcpp

from services.barcode import check_digit_ok, decode, normalise
from services.catalogue import Catalogue
from tests.photos import blank, snapshot
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


class TestPhotos:
    def test_fr_03_a_photo_of_a_barcode_reads_back_its_code(self):
        code = barcode_of(COKE)
        assert decode(snapshot(code)) == [code]

    def test_fr_03_a_tilted_soft_photo_still_reads(self):
        code = barcode_of(COKE)
        assert decode(snapshot(code, tilt=8, blur=1.2)) == [code]

    def test_fr_03_a_photo_taken_sideways_reads(self):
        code = barcode_of(COKE)
        assert decode(snapshot(code, size=(720, 1280), tilt=90)) == [code]

    def test_ec_49_a_huge_photo_is_shrunk_and_still_reads(self):
        code = barcode_of(COKE)
        assert decode(snapshot(code, size=(6000, 4000), scale=12)) == [code]

    def test_ec_49_no_barcode_reads_as_nothing_never_an_error(self):
        for photo in (blank(), b"", b"not an image", b"\xff\xd8\xff\xe0" + b"\x00" * 64):
            assert decode(photo) == []

    def test_ec_49_a_blurred_barcode_is_never_read_as_another_code(self):
        code = barcode_of(COKE)
        for radius in (3, 6, 12):
            assert set(decode(snapshot(code, blur=radius))) <= {code}

    def test_ec_51_a_qr_code_is_not_a_product_barcode(self):
        qr = snapshot(barcode_of(COKE), fmt=zxingcpp.BarcodeFormat.QRCode, scale=8)
        assert decode(qr) == []

    def test_ec_53_two_codes_are_both_reported_and_one_code_twice_is_one(self):
        a, b = barcode_of(COKE), barcode_of("Diet Coke")
        assert sorted(decode(snapshot(a, b, size=(1400, 600), scale=2))) == sorted([a, b])
        assert decode(snapshot(a, a, size=(1400, 600), scale=2)) == [a]


class TestLookup:
    def test_fr_03_ec_50_the_lookup_is_exact(self):
        catalogue, code = Catalogue(store()), barcode_of(COKE)
        assert catalogue.by_barcode(code).name == COKE
        assert catalogue.by_barcode("5449000000996") is None  # valid, but not this catalogue
        assert catalogue.by_barcode(code[:8]) is None
