"""AC-15, NFR-11 — the whole journey at 390 px, in a real (headless) browser.

Serves the built Next.js page and the API from one local process with the model off (or targets
a deployed site through LOCATOR_URL), drives a three-floor journey at 390 × 844, and measures:
no horizontal page scroll at any step, the floor plate within the viewport, and route markers
and labels big enough to read without zooming. The scan tests feed Chromium's fake camera a
frame showing a barcode — the real path from camera to product, decoded on the phone.
"""

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
import zxingcpp
from PIL import Image
from playwright.sync_api import sync_playwright

from tests.photos import barcode_image

REPO = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 390, 844
MIN_MARKER_PX, MIN_LABEL_PX = 16, 11
SEARCH_LABEL = "What are you looking for?"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    if os.environ.get(
        "LOCATOR_URL"
    ):  # the deployed site — LOCATOR_URL=https://… pytest tests/browser
        yield os.environ["LOCATOR_URL"]
        return
    if not (REPO / "out" / "index.html").is_file():  # scripts/check.sh builds it first
        subprocess.run(["npm", "run", "build"], cwd=REPO, check=True, capture_output=True)
    port = free_port()
    env = {**os.environ, "LOCATOR_MODEL": "off", "LOCATOR_STATIC": str(REPO / "out")}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.index:app", "--port", str(port), "--log-level", "warning"],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    deadline = time.time() + 30
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.3)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(timeout=10)


def y4m(frame: Image.Image, path: Path) -> Path:
    """One still frame as a Y4M video — the format Chromium's fake camera plays on a loop."""
    grey = frame.convert("L")
    w, h = grey.size
    chroma = bytes([128]) * ((w // 2) * (h // 2))
    path.write_bytes(
        f"YUV4MPEG2 W{w} H{h} F30:1 Ip A1:1 C420jpeg\n".encode()
        + b"FRAME\n" + grey.tobytes() + chroma + chroma
    )  # fmt: skip
    return path


def frame_of(*images: Image.Image, size=(640, 480)) -> Image.Image:
    frame = Image.new("RGB", size, (236, 232, 224))
    x = (size[0] - sum(i.width for i in images) - 40 * (len(images) - 1)) // 2
    for img in images:
        frame.paste(img, (x, (size[1] - img.height) // 2))
        x += img.width + 40
    return frame


def barcode(name: str) -> str:
    rows = (REPO / "data" / "SBY-DEMO-001" / "products.csv").read_text().splitlines()
    return next(r.split(",")[4] for r in rows if r.split(",")[1] == name)


@contextmanager
def phone(server, camera: Path | None = None, camera_allowed: bool = True):
    args = ["--use-fake-device-for-media-stream"]
    if camera:
        args.append(f"--use-file-for-fake-video-capture={camera}")
    if camera_allowed:
        args.append("--use-fake-ui-for-media-stream")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=args)
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            is_mobile=True,
            permissions=["camera"] if camera_allowed else [],
        )
        page = context.new_page()
        page.dialogs = []
        page.on("dialog", lambda d: (page.dialogs.append(d.message), d.dismiss()))
        page.goto(server)
        page.get_by_label(SEARCH_LABEL).wait_for(timeout=20000)
        page.get_by_label("Which floor are you on?").wait_for(timeout=20000)
        yield page
        browser.close()


def no_horizontal_scroll(page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def search(page, query):
    page.get_by_label(SEARCH_LABEL).fill(query)
    page.get_by_role("button", name="Search", exact=True).click()


def test_ac_15_nfr_11_the_journey_fits_a_phone(server):
    with phone(server) as page:
        assert no_horizontal_scroll(page), "landing page scrolls sideways"
        search(page, "everyday shampoo, baked beans, bananas, salmon fillet")
        page.get_by_role("button", name="Add 4 available to basket").wait_for(timeout=20000)
        assert no_horizontal_scroll(page), "results scroll sideways"

        page.get_by_role("button", name="Add 4 available to basket").click()
        page.get_by_role("button", name="Plan my route").click()
        plate = page.locator("svg[data-floor]").first
        plate.wait_for(timeout=20000)
        assert no_horizontal_scroll(page), "route view scrolls sideways"

        box = plate.bounding_box()
        assert box["width"] <= WIDTH and box["width"] >= WIDTH * 0.8, box

        markers = page.locator("svg[data-floor] [data-stop] circle")
        assert markers.count() >= 1
        for i in range(markers.count()):
            size = markers.nth(i).bounding_box()
            if size:
                assert size["width"] >= MIN_MARKER_PX, size
        labels = page.locator("svg[data-floor] [data-stop] text")
        sizes = labels.evaluate_all(
            "els => els.filter(e => e.getBoundingClientRect().height > 0)"
            ".map(e => e.getBoundingClientRect().height)"
        )
        assert sizes and min(sizes) >= MIN_LABEL_PX, sizes
        page.get_by_role("tab", name="Floor 0").click()  # every floor the route touches is drawn
        page.locator("svg[data-floor='0']").wait_for(timeout=5000)
        if os.environ.get("LOCATOR_SCREENSHOTS"):  # gate evidence, on request only
            out = REPO / "specs" / "011-nextjs-vercel"
            page.screenshot(path=str(out / "phone-390-route.png"), full_page=True)


def test_c_04_ac_13_no_store_line_and_typed_markup_stays_text(server):
    with phone(server) as page:
        body = page.locator("body").inner_text()
        assert "synthetic" not in body.lower() and "Demo Superstore" not in body
        search(page, "<img src=x onerror=alert(1)><script>alert(2)</script>")
        shown = page.get_by_text("<img src=x").first  # the search is shown back …
        shown.wait_for(timeout=20000)
        assert "<script>" in shown.inner_text()  # … as text, not markup
        assert page.locator("main img, main script").count() == 0
        assert page.dialogs == []


def test_fr_05_a_choice_is_asked_and_answered_in_the_browser(server):
    with phone(server) as page:
        search(page, "milk")
        page.get_by_text("Which did you mean?").wait_for(timeout=20000)
        page.get_by_role("radio").nth(1).check()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("heading", name="Your route").wait_for(timeout=20000)
        assert page.get_by_text("Which did you mean?").count() == 0


def test_ac_28_fr_03_a_camera_scan_finds_the_product_at_phone_width(server, tmp_path):
    """A-07, EC-54 — the live camera, read on the phone; only the digits reach the server, and
    the camera stops at the first read, so a code is looked up once."""
    camera = y4m(frame_of(barcode_image(barcode("Coca-Cola Classic"))), tmp_path / "coke.y4m")
    with phone(server, camera) as page:
        assert page.locator("video").count() == 0, "the camera started before it was asked for"
        page.get_by_text("Scan a barcode").click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)
        assert page.locator("video").count() == 0, "the camera kept running after the read"
        assert page.get_by_role("button", name="Add 1 available to basket").count() == 1
        assert no_horizontal_scroll(page), "the scan scrolls sideways"
        if os.environ.get("LOCATOR_SCREENSHOTS"):
            page.screenshot(path=str(REPO / "specs" / "011-nextjs-vercel" / "phone-390-scan.png"),
                            full_page=True)  # fmt: skip


def test_ec_51_ec_49_a_qr_code_is_not_read_and_the_page_says_what_to_try(server, tmp_path):
    qr = barcode_image(barcode("Coca-Cola Classic"), zxingcpp.BarcodeFormat.QRCode, scale=8)
    with phone(server, y4m(frame_of(qr), tmp_path / "qr.y4m")) as page:
        page.get_by_text("Scan a barcode").click()
        page.get_by_text("No barcode read yet").wait_for(timeout=20000)
        assert page.get_by_text("In stock").count() == 0


def test_ec_53_two_barcodes_in_view_are_never_chosen_between(server, tmp_path):
    two = frame_of(barcode_image(barcode("Coca-Cola Classic"), scale=2),
                   barcode_image(barcode("Diet Coke"), scale=2), size=(800, 480))  # fmt: skip
    with phone(server, y4m(two, tmp_path / "two.y4m")) as page:
        page.get_by_text("Scan a barcode").click()
        page.get_by_text("more than one barcode").wait_for(timeout=20000)
        assert (
            page.get_by_text("In stock").count() == 0 and page.get_by_text("Sold out").count() == 0
        )


def test_ec_48_ac_28_camera_declined_typed_digits_still_find_it(server):
    with phone(server, camera_allowed=False) as page:
        page.get_by_text("Scan a barcode").click()
        page.get_by_text("The camera isn't available here").wait_for(timeout=20000)
        page.get_by_label("Or type the numbers under the barcode").fill(
            barcode("Coca-Cola Classic")
        )
        page.get_by_role("button", name="Look up").click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)


def test_ec_41_a_refresh_keeps_the_basket_and_the_start_point(server):
    with phone(server) as page:
        page.get_by_label("Which floor are you on?").select_option("1")
        search(page, "bananas, baked beans")
        page.get_by_role("button", name="Add 2 available to basket").click()
        page.get_by_role("heading", name="Basket (2)").wait_for(timeout=5000)
        page.reload()
        page.get_by_role("heading", name="Basket (2)").wait_for(timeout=20000)
        assert page.get_by_label("Which floor are you on?").input_value() == "1"
