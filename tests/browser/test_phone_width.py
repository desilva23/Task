"""AC-15, NFR-11 — the whole journey at 390 px, in a real (headless) browser.

Starts the page with the model off, drives a three-floor journey at 390 × 844, and measures:
no horizontal page scroll at any step, the floor plate within the viewport, and route markers
and labels big enough to read without zooming. The scan runs on Chromium's fake camera, fed a
frame showing a catalogued barcode — the real path from camera to product.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.photos import barcode_image

REPO = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 390, 844
MIN_MARKER_PX, MIN_LABEL_PX = 16, 11


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    if os.environ.get(
        "LOCATOR_URL"
    ):  # the deployed app — LOCATOR_URL=https://… pytest tests/browser
        yield os.environ["LOCATOR_URL"]
        return
    port = free_port()
    env = {**os.environ, "LOCATOR_MODEL": "off"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
         "--server.port", str(port), "--browser.gatherUsageStats", "false"],
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


def no_horizontal_scroll(page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_ac_15_nfr_11_the_journey_fits_a_phone(server):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, is_mobile=True)
        page.goto(server)
        page.get_by_label("What are you looking for?").wait_for(timeout=20000)
        assert no_horizontal_scroll(page), "landing page scrolls sideways"

        page.get_by_label("What are you looking for?").fill(
            "everyday shampoo, baked beans, bananas, salmon fillet"
        )
        page.get_by_role("button", name="Search").click()
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
            if size:  # markers on a floor tab not shown are not laid out
                assert size["width"] >= MIN_MARKER_PX, size
        labels = page.locator("svg[data-floor] [data-stop] text")
        sizes = labels.evaluate_all(
            "els => els.filter(e => e.getBoundingClientRect().height > 0)"
            ".map(e => e.getBoundingClientRect().height)"
        )
        assert sizes and min(sizes) >= MIN_LABEL_PX, sizes
        if os.environ.get("LOCATOR_SCREENSHOTS"):  # gate evidence, on request only
            out = REPO / "specs" / "008-page"
            page.screenshot(path=str(out / "phone-390.png"), full_page=True)
            plate.scroll_into_view_if_needed()
            plate.screenshot(path=str(out / "phone-390-plate.png"))
        browser.close()


def y4m(frame, path: Path) -> Path:
    """One still frame as a Y4M video — the format Chromium's fake camera plays on a loop."""
    grey = frame.convert("L")
    w, h = grey.size
    chroma = bytes([128]) * ((w // 2) * (h // 2))
    path.write_bytes(
        f"YUV4MPEG2 W{w} H{h} F30:1 Ip A1:1 C420jpeg\n".encode()
        + b"FRAME\n" + grey.tobytes() + chroma + chroma
    )  # fmt: skip
    return path


def test_ac_28_fr_03_a_camera_scan_finds_the_product_at_phone_width(server, tmp_path):
    """A-07 — a still photo from the browser's camera, read on the server."""
    from PIL import Image

    rows = (REPO / "data" / "SBY-DEMO-001" / "products.csv").read_text().splitlines()
    code = next(r.split(",")[4] for r in rows if r.split(",")[1] == "Coca-Cola Classic")
    frame = Image.new("RGB", (640, 480), (236, 232, 224))
    bars = barcode_image(code)
    frame.paste(bars, ((640 - bars.width) // 2, (480 - bars.height) // 2))
    camera = y4m(frame, tmp_path / "barcode.y4m")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-video-capture={camera}",
        ])  # fmt: skip
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT}, is_mobile=True, permissions=["camera"]
        )
        page = context.new_page()
        page.goto(server)
        page.get_by_label("What are you looking for?").wait_for(timeout=20000)
        assert page.locator("video").count() == 0, "the camera started before it was asked for"
        page.get_by_text("Scan a barcode").click()
        take = page.get_by_role("button", name="Take Photo")
        take.wait_for(timeout=20000)
        page.wait_for_timeout(1500)  # let the fake stream deliver frames
        take.click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)
        assert page.get_by_role("button", name="Add 1 available to basket").count() == 1
        assert no_horizontal_scroll(page), "the scan scrolls sideways"
        if os.environ.get("LOCATOR_SCREENSHOTS"):
            page.screenshot(path=str(REPO / "specs" / "010-barcode-scan" / "phone-390-scan.png"),
                            full_page=True)  # fmt: skip
        browser.close()
