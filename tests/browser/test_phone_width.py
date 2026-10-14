"""AC-15, NFR-11 — the whole journey at 390 px, in a real (headless) browser.

Starts the page with the model off, drives a three-floor journey at 390 × 844, and measures:
no horizontal page scroll at any step, the floor plate within the viewport, and route markers
and labels big enough to read without zooming.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 390, 844
MIN_MARKER_PX, MIN_LABEL_PX = 16, 11


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
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
