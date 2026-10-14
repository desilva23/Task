"""The barcode scan (FR-03, hld.md §3.5): a still photo from the camera, or the digits typed.

The camera starts when its widget is drawn, so it is drawn only once the shopper turns the scan
on — nobody who never scans is asked for camera permission. The typed digits sit beside it and
are the same lookup when the camera is declined, missing or cannot start (EC-48).
"""

import streamlit as st

from services.barcode import decode
from ui.text import md
from ui.view import PhotoLatch, scan_choice


def scan() -> str | None:
    """The code to look up on this run, or None."""
    if not st.toggle("Scan a barcode", key="scan_on"):
        return None
    ss = st.session_state
    latch = ss.setdefault("scan_latch", PhotoLatch())
    photo = st.camera_input("Photograph the barcode", key="scan_photo")
    code = None
    if photo is not None and latch.new(photo.getvalue()):
        code, ss.scan_notice = scan_choice(decode(photo.getvalue()))  # photo read, then dropped
    if ss.get("scan_notice"):
        st.warning(md(ss.scan_notice))
    with st.form("scan_form", border=False):
        digits = st.text_input(
            "Or type the numbers under the barcode",
            key="scan_digits",
            max_chars=20,
            placeholder="13 digits",
        )
        typed = st.form_submit_button("Look up", key="scan_lookup", width="stretch")
    if typed and digits.strip():
        ss.scan_notice = None
        return digits
    return code
