"""AC-15, NFR-11 — the whole journey at 390 px, in a real (headless) browser.

Serves the built Next.js page and the API from one local process with the model off (or targets
a deployed site through LOCATOR_URL), drives a three-floor journey at 390 × 844, and measures:
the page never scrolls, across or down, at any step; the floor plate fills the width; and route
markers and labels are big enough to read without zooming. The scan tests feed Chromium's fake camera a
frame showing a barcode — the real path from camera to product, decoded on the phone. The voice
tests stand a scripted recogniser in for the browser's own, which a headless browser cannot run.
"""

import json
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


# The browser's speech recogniser, scripted: it "hears" HEARD word by word, or fails with FAIL.
# A blank HEARD ends having heard nothing; NONE removes the recogniser, as in Firefox.
FAKE_RECOGNISER = """
(() => {
  const script = %s;
  if (script.none) { delete window.SpeechRecognition; delete window.webkitSpeechRecognition; return; }
  class Fake {
    start() {
      window.__voice = { lang: this.lang, starts: (window.__voice?.starts ?? 0) + 1 };
      const words = script.heard.split(" ").filter(Boolean);
      let said = [];
      const step = () => {
        if (script.fail) { this.onerror?.({ error: script.fail }); return this.onend?.(); }
        if (!words.length || this.stopped) return this.onend?.();
        said.push(words.shift());
        const last = !words.length;
        this.onresult?.({ results: { length: 1, 0: { isFinal: last, length: 1,
          0: { transcript: said.join(" ") } } } });
        setTimeout(step, 120);
      };
      setTimeout(step, 120);
    }
    stop() { this.stopped = true; }
    abort() {}
  }
  window.SpeechRecognition = Fake;
  window.webkitSpeechRecognition = Fake;
})();
"""


@contextmanager
def phone(
    server, camera: Path | None = None, camera_allowed: bool = True, voice: dict | None = None
):
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
        if voice is not None:
            context.add_init_script(FAKE_RECOGNISER % json.dumps({"heard": "", **voice}))
        page = context.new_page()
        page.dialogs = []
        page.on("dialog", lambda d: (page.dialogs.append(d.message), d.dismiss()))
        page.goto(server)
        page.get_by_label(SEARCH_LABEL).wait_for(timeout=20000)
        page.get_by_role("button", name="Where you are").wait_for(timeout=20000)
        yield page
        browser.close()


def no_page_scroll(page) -> bool:
    """NFR-11 — the page fits the screen both ways; only a list or the map moves, in its frame."""
    return page.evaluate(
        "(() => { const d = document.documentElement, b = document.body;"
        " return d.scrollWidth <= innerWidth && d.scrollHeight <= innerHeight"
        " && b.scrollHeight <= innerHeight; })()"
    )


def search(page, query):
    box = page.get_by_label(SEARCH_LABEL)
    box.fill(query)
    box.press("Enter")  # Enter searches what was typed; the suggestion list may cover the button


def set_place(page, level: str, spot: str | None = None, step_free: bool | None = None):
    page.get_by_role("button", name="Where you are").click()
    page.get_by_label("Which floor are you on?").select_option(level)
    if spot:
        page.get_by_label("Where on that floor?").select_option(label=spot)
    if step_free is not None:
        page.get_by_label("Step-free route (lifts, no stairs)").set_checked(step_free)
    page.get_by_role("button", name="Done").click()


def test_ac_15_nfr_11_the_journey_fits_a_phone(server):
    with phone(server) as page:
        assert no_page_scroll(page), "landing page scrolls"
        search(page, "everyday shampoo, baked beans, bananas, salmon fillet")
        page.get_by_role("button", name="Add 4 available to basket").wait_for(timeout=20000)
        assert no_page_scroll(page), "results scroll the page"

        page.get_by_role("button", name="Add 4 available to basket").click()
        page.get_by_role("tab", name="Basket (4)").click()
        assert no_page_scroll(page), "the basket scrolls the page"
        page.get_by_role("button", name="Plan my route").click()
        plate = page.locator("svg[data-floor]").first
        plate.wait_for(timeout=20000)
        assert no_page_scroll(page), "the route scrolls the page"

        box = plate.bounding_box()
        assert box["width"] <= WIDTH and box["width"] >= WIDTH * 0.8, box
        # measured in one pass, before a step can switch the floor shown
        sizes = plate.evaluate(
            """svg => ({
              circles: [...svg.querySelectorAll('[data-stop] circle')]
                .map(e => e.getBoundingClientRect().width),
              texts: [...svg.querySelectorAll('[data-stop] text')]
                .map(e => e.getBoundingClientRect().height).filter(h => h > 0),
            })"""
        )
        assert sizes["circles"] and min(sizes["circles"]) >= MIN_MARKER_PX, sizes
        assert sizes["texts"] and min(sizes["texts"]) >= MIN_LABEL_PX, sizes

        page.get_by_role("button", name="Next", exact=True).click()
        assert no_page_scroll(page), "a step scrolls the page"
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
        page.get_by_role("button", name="Show route").click(timeout=20000)
        page.get_by_role("heading", name="Your route").wait_for(timeout=20000)
        assert page.get_by_text("Which did you mean?").count() == 0


def test_ac_28_fr_03_a_camera_scan_finds_the_product_at_phone_width(server, tmp_path):
    """A-07, EC-54 — the live camera, read on the phone; only the digits reach the server, and
    the camera stops at the first read, so a code is looked up once."""
    camera = y4m(frame_of(barcode_image(barcode("Coca-Cola Classic"))), tmp_path / "coke.y4m")
    with phone(server, camera) as page:
        assert page.locator("video").count() == 0, "the camera started before it was asked for"
        page.get_by_role("button", name="Scan a barcode").click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)
        assert page.locator("video").count() == 0, "the camera kept running after the read"
        assert page.get_by_role("button", name="Add 1 available to basket").count() == 1
        assert no_page_scroll(page), "the scan scrolls the page"
        if os.environ.get("LOCATOR_SCREENSHOTS"):
            page.screenshot(path=str(REPO / "specs" / "011-nextjs-vercel" / "phone-390-scan.png"),
                            full_page=True)  # fmt: skip


def test_ec_51_ec_49_a_qr_code_is_not_read_and_the_page_says_what_to_try(server, tmp_path):
    qr = barcode_image(barcode("Coca-Cola Classic"), zxingcpp.BarcodeFormat.QRCode, scale=8)
    with phone(server, y4m(frame_of(qr), tmp_path / "qr.y4m")) as page:
        page.get_by_role("button", name="Scan a barcode").click()
        page.get_by_text("No barcode read yet").wait_for(timeout=20000)
        assert page.get_by_text("In stock").count() == 0


def test_ec_53_two_barcodes_in_view_are_never_chosen_between(server, tmp_path):
    two = frame_of(barcode_image(barcode("Coca-Cola Classic"), scale=2),
                   barcode_image(barcode("Diet Coke"), scale=2), size=(800, 480))  # fmt: skip
    with phone(server, y4m(two, tmp_path / "two.y4m")) as page:
        page.get_by_role("button", name="Scan a barcode").click()
        page.get_by_text("more than one barcode").wait_for(timeout=20000)
        assert (
            page.get_by_text("In stock").count() == 0 and page.get_by_text("Sold out").count() == 0
        )


def test_ec_48_ac_28_camera_declined_typed_digits_still_find_it(server):
    with phone(server, camera_allowed=False) as page:
        page.get_by_role("button", name="Scan a barcode").click()
        page.get_by_text("The camera isn't available here").wait_for(timeout=20000)
        page.get_by_label("Or type the numbers under the barcode").fill(
            barcode("Coca-Cola Classic")
        )
        page.get_by_role("button", name="Look up").click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)


def test_ec_41_a_refresh_keeps_the_basket_and_the_start_point(server):
    with phone(server) as page:
        set_place(page, "1")
        search(page, "bananas, baked beans")
        page.get_by_role("button", name="Add 2 available to basket").click()
        page.get_by_role("tab", name="Basket (2)").wait_for(timeout=5000)
        page.reload()
        page.get_by_role("tab", name="Basket (2)").click(timeout=20000)
        page.get_by_role("heading", name="Basket (2)").wait_for(timeout=5000)
        assert "Floor 1" in page.get_by_role("button", name="Where you are").inner_text()


MIC = "Speak your search"


def test_ac_30_fr_27_ec_64_a_spoken_request_runs_the_search_it_heard(server):
    """The words fill the box as they are heard and the search runs on them when the shopper
    stops — the same search as typing them, and still in the box to correct."""
    with phone(server, voice={"heard": "coca cola classic"}) as page:
        page.get_by_role("button", name=MIC).click()
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)
        assert page.get_by_label(SEARCH_LABEL).input_value() == "coca cola classic"
        assert page.evaluate("window.__voice") == {"lang": "en-GB", "starts": 1}
        page.get_by_role("button", name="Show route").wait_for(timeout=20000)  # as typed: routed
        assert page.get_by_text("Didn't catch that").count() == 0
        assert no_page_scroll(page), "the microphone scrolls the page"


def test_ec_62_ac_30_no_recogniser_no_microphone_and_typing_still_works(server):
    with phone(server, voice={"none": True}) as page:
        assert page.get_by_role("button", name=MIC).count() == 0
        search(page, "coca cola classic")
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)


def test_ec_61_ac_30_microphone_declined_says_so_and_typing_still_works(server):
    with phone(server, voice={"fail": "not-allowed"}) as page:
        page.get_by_role("button", name=MIC).click()
        page.get_by_text("The microphone isn't available here").wait_for(timeout=20000)
        search(page, "coca cola classic")
        page.get_by_text("Classic 500ml — In stock").wait_for(timeout=20000)


def test_ec_63_nothing_heard_runs_no_search(server):
    with phone(server, voice={"fail": "no-speech"}) as page:
        page.get_by_role("button", name=MIC).click()
        page.get_by_text("Didn't catch that").wait_for(timeout=20000)
        assert page.get_by_text("In stock").count() == 0
    with phone(server, voice={"heard": ""}) as page:  # ended without a word, and no error
        page.get_by_role("button", name=MIC).click()
        page.get_by_text("Didn't catch that").wait_for(timeout=20000)
        assert page.get_by_label(SEARCH_LABEL).input_value() == ""


def test_fr_27_the_microphone_is_red_while_recording_and_a_second_tap_stops_it(server):
    """FR-27 — a long request, stopped early: the button turns red while it records, turns back
    on the second tap, and the search runs on the words heard so far."""
    words = "coca cola classic and some words nobody will hear"
    with phone(server, voice={"heard": words}) as page:
        page.get_by_role("button", name=MIC).click()
        mic = page.get_by_role("button", name="Stop listening")
        page.wait_for_function(
            "document.querySelector('button.mic').getAttribute('aria-pressed') === 'true'"
        )
        red, green, blue = map(int, mic.evaluate(
            "b => getComputedStyle(b).backgroundColor.match(/\\d+/g).slice(0, 3)"))  # fmt: skip
        assert red > 180 and green < 100 and blue < 100, (red, green, blue)
        page.wait_for_function(
            "document.querySelector('input[type=search]').value.split(' ').length >= 3"
        )
        mic.click()
        page.get_by_role("button", name=MIC).wait_for(timeout=5000)
        heard = page.get_by_label(SEARCH_LABEL).input_value()
        assert heard.startswith("coca cola classic") and heard != words


def suggestions(page) -> list[str]:
    page.get_by_role("listbox", name="Suggestions").wait_for(timeout=5000)
    return page.get_by_role("option").all_inner_texts()


def test_ac_31_fr_28_typing_suggests_and_a_suggestion_finds_that_product(server):
    with phone(server) as page:
        box = page.get_by_label(SEARCH_LABEL)
        box.press_sequentially("bre")
        shown = suggestions(page)
        assert 1 <= len(shown) <= 6 and all("Bread" in s or "Loaf" in s for s in shown[:3]), shown
        assert no_page_scroll(page), "the suggestions scroll the page"
        page.get_by_role("option", name="White Bread Medium Sliced 800g").click()
        page.get_by_text("White Bread Medium Sliced 800g — In stock").wait_for(timeout=20000)
        assert page.get_by_text("Which did you mean?").count() == 0
        assert box.input_value() == "White Bread Medium Sliced 800g"


def test_ec_67_ac_31_after_a_comma_only_the_item_being_typed_is_replaced(server):
    with phone(server) as page:
        box = page.get_by_label(SEARCH_LABEL)
        box.press_sequentially("bananas, baked be")
        first = suggestions(page)[0]
        box.press("ArrowDown")
        box.press("Enter")  # the highlighted suggestion, not the half-typed word
        assert box.input_value() == f"bananas, {first.split('Sold out')[0].strip()}"
        page.get_by_role("button", name="Add 2 available to basket").wait_for(timeout=20000)


def test_ec_65_ec_66_no_list_for_one_letter_or_a_product_not_sold_here(server):
    with phone(server) as page:
        box = page.get_by_label(SEARCH_LABEL)
        box.press_sequentially("b")
        assert page.get_by_role("listbox").count() == 0
        box.fill("")
        box.press_sequentially("pepsi")  # in the catalogue, not sold at this branch
        page.wait_for_timeout(300)
        assert page.get_by_role("listbox").count() == 0
        box.fill("")
        box.press_sequentially("diet co")
        assert any("Diet Coke" in s and "Sold out" in s for s in suggestions(page))
        box.fill("pepsi")
        box.press("Enter")  # typing on and searching still works: "not sold here", as before
        page.get_by_text("Not sold at this store").wait_for(timeout=20000)


def test_ac_32_fr_27_a_spoken_list_without_and_is_split_and_can_be_undone(server):
    with phone(server, voice={"heard": "milk bread chicken"}) as page:
        page.get_by_role("button", name=MIC).click()
        page.get_by_text("Searched as: milk · bread · chicken").wait_for(timeout=20000)
        page.get_by_text("Which did you mean?").wait_for(timeout=20000)
        page.get_by_role("button", name="Search “milk bread chicken” as one item").click()
        page.get_by_text("We don't recognise").wait_for(timeout=20000)
        assert page.get_by_label(SEARCH_LABEL).input_value() == '"milk bread chicken"'
        assert page.get_by_text("Searched as:").count() == 0
