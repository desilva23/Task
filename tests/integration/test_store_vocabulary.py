"""FR-04, AC-18 — the model may only choose categories, departments and allergens this store has.

Found live (Phase 6): gpt-oss read "something for a headache" well but invented the category
"over the counter" and the department "pharmacy", which matched nothing and filtered every
product out. The schema now offers only this store's names, so strict decoding cannot produce
another, and our validation rejects one anyway.
"""

import json
from functools import cache
from pathlib import Path

import pytest
from pydantic import ValidationError

from graph.groq_client import strict_schema
from graph.journey import Journey
from graph.model import FakeModel
from graph.services import Services
from models.llm import parsed_query_for
from validation import load_store

DEMO = Path(__file__).resolve().parents[2] / "data" / "SBY-DEMO-001"


@cache
def services():
    return Services.from_store(load_store(DEMO))


def test_the_schema_lists_only_this_stores_names():
    store = services().store
    schema = strict_schema(parsed_query_for(store))
    props = schema["properties"]
    names = {p.aisle_category for p in store.products.values()} | {
        p.department for p in store.products.values()
    }
    # either field accepts any real name; our code files each into the right one afterwards
    assert set(props["aisle_category"]["items"]["enum"]) == names
    assert set(props["department"]["items"]["enum"]) == names
    assert "Medicines" in props["aisle_category"]["items"]["enum"]
    assert set(props["dietary_required"]["items"]["enum"]) == {
        "gluten_free",
        "vegan",
        "vegetarian",
        "halal",
    }


def test_an_invented_category_is_rejected():
    with pytest.raises(ValidationError):
        parsed_query_for(services().store).model_validate({
            "items": ["pain reliever"], "department": ["pharmacy"], "aisle_category": [],
            "dietary_required": [], "exclude_allergens": [],
        })  # fmt: skip


def test_the_understand_node_sends_the_store_schema():
    seen = {}

    def spy(schema, system, user):
        seen["schema"] = schema
        return {"items": [], "department": [], "aisle_category": [], "dietary_required": [],
                "exclude_allergens": []}  # fmt: skip

    Journey(services(), FakeModel(understand=spy)).run_query(
        "v1", "I need something for a headache please"
    )
    assert seen["schema"] is services().query_model


def test_a_category_offers_its_products_when_the_item_phrase_finds_nothing():
    def headache(schema, system, user):
        return {"items": ["pain reliever"], "department": ["Health & Beauty"],
                "aisle_category": ["Medicines"], "dietary_required": [], "exclude_allergens": []}  # fmt: skip

    s = (
        Journey(services(), FakeModel(understand=headache))
        .run_query("v2", "I need something for a headache please")
        .state
    )
    offered = {
        services().catalogue.by_sku(k).aisle_category for row in s["candidates"] for k in row
    }
    assert offered == {"Medicines"} and s["term_status"] == ["ambiguous"]


def test_fr_04_the_model_is_told_to_choose_from_the_lists():
    def spy(schema, system, user):
        spy.system = system
        return {"items": [], "department": [], "aisle_category": [], "dietary_required": [],
                "exclude_allergens": []}  # fmt: skip

    Journey(services(), FakeModel(understand=spy)).run_query("v3", "something for my lunch please")
    assert "only" in spy.system and "allowed" in spy.system
    assert json.dumps("Medicines") not in spy.system  # names travel in the schema, not the prompt


def test_a_category_in_the_department_field_is_filed_correctly():
    """Found live: gpt-oss put the category "Medicines" under department, and Groq refused it."""
    from graph.nodes.understand import file_names

    parsed = parsed_query_for(services().store).model_validate({
        "items": ["headache tablets"], "department": ["Medicines"], "aisle_category": ["Household"],
        "dietary_required": [], "exclude_allergens": [],
    })  # fmt: skip
    filed = file_names(parsed.model_dump(), services().store)
    assert filed["aisle_category"] == ["Medicines"] and filed["department"] == ["Household"]
