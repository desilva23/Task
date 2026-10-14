"""The page itself, driven headless with Streamlit's AppTest. The model is forced off, so these
never reach GroqCloud even with a key on the machine."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[2] / "app.py")


@pytest.fixture
def page(monkeypatch):
    monkeypatch.setenv("LOCATOR_MODEL", "off")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def search(at, query):
    at.text_input(key="query").input(query)
    at.button(key="search").click()
    at.run()
    assert not at.exception, at.exception
    return at


def page_text(at):
    return " ".join(
        str(e.value) for e in (*at.markdown, *at.caption, *at.info, *at.warning, *at.subheader)
    )


def test_c_04_the_page_shows_no_store_line(page):
    """The owner removed the store and synthetic-data line from the page (2026-10-14); the store
    files still declare themselves synthetic, which V-12 enforces at load."""
    text = page_text(page)
    assert "synthetic" not in text.lower() and "Demo Superstore" not in text


def test_ac_08_fr_21_fr_22_three_available_one_not_one_tap_adds_three(page):
    search(page, "bananas, baked beans, dental floss, diet coke")
    text = page_text(page)
    assert text.index("Available") < text.index("Not available")
    add = page.button(key="add_available")
    assert "3" in add.label
    add.click()
    page.run()
    assert len(page.session_state["basket"]) == 3


def test_fr_24_an_unavailable_item_can_be_added_but_is_left_out_of_the_route(page):
    search(page, "bananas, diet coke")
    page.button(key="add_available").click().run()
    diet_coke = next(b for b in page.button if b.key and b.key.startswith("add_one_"))
    diet_coke.click().run()
    assert len(page.session_state["basket"]) == 2
    page.button(key="plan_route").click().run()
    assert not page.exception, page.exception
    assert "left out of the route" in page_text(page)


def test_fr_05_a_question_is_asked_and_the_answer_carries_on(page):
    search(page, "milk")
    choice = page.radio(key="choose_0")
    choice.set_value(choice.options[1])
    page.button(key="answer").click().run()
    assert not page.exception, page.exception
    assert not [r for r in page.radio if r.key == "choose_0"]  # the question is gone
    assert "pick up" in page_text(page)  # a single product routes once chosen


def test_nfr_04_the_page_says_when_the_model_was_not_used(page):
    search(page, "Coca-Cola Classic")
    assert "plain wording" in page_text(page).lower()


def test_fr_19_step_free_is_one_toggle(page):
    page.toggle(key="step_free").set_value(True).run()
    search(page, "Everyday Shampoo")
    text = page_text(page)
    assert "lift" in text and "stairs" not in text
