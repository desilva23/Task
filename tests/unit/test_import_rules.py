from pathlib import Path

import pytest

from tests.guards.imports import find_violations

REPO = Path(__file__).resolve().parents[2]


def plant(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


class TestBoundaryRules:
    """CONST-IV — the one-way import rules, proven against planted violations."""

    @pytest.mark.parametrize(
        "source, module",
        [
            ("import langgraph\n", "langgraph"),
            ("from langgraph.graph import StateGraph\n", "langgraph.graph"),
            ("import langchain\n", "langchain"),
            ("from langchain_core.messages import HumanMessage\n", "langchain_core.messages"),
            ("from langchain_groq import ChatGroq\n", "langchain_groq"),
            ("import streamlit as st\n", "streamlit"),
            ("import groq\n", "groq"),
            ("from openai import OpenAI\n", "openai"),
            ("import anthropic\n", "anthropic"),
        ],
    )
    def test_services_may_not_import_runtime(self, tmp_path, source, module):
        plant(tmp_path, "services/catalogue.py", source)
        assert find_violations(tmp_path) == [
            f"services/catalogue.py:1 services-no-runtime: {module}"
        ]

    def test_import_inside_a_function_is_caught(self, tmp_path):
        plant(tmp_path, "services/stock.py", "def f():\n    import streamlit\n")
        assert find_violations(tmp_path) == ["services/stock.py:2 services-no-runtime: streamlit"]

    def test_services_may_not_import_graph(self, tmp_path):
        plant(tmp_path, "services/routing.py", "from graph.state import JourneyState\n")
        assert find_violations(tmp_path) == [
            "services/routing.py:1 services-not-graph: graph.state"
        ]

    def test_relative_import_climbing_into_graph_is_caught(self, tmp_path):
        plant(tmp_path, "services/routing.py", "from .. import graph\n")
        assert find_violations(tmp_path) == ["services/routing.py:1 services-not-graph: graph"]

    def test_relative_import_within_services_is_allowed(self, tmp_path):
        plant(tmp_path, "services/routing.py", "from .storegraph import StoreGraph\n")
        assert find_violations(tmp_path) == []

    def test_a_name_that_only_starts_with_graph_is_allowed(self, tmp_path):
        plant(tmp_path, "services/routing.py", "import graphviz\n")
        assert find_violations(tmp_path) == []

    def test_graph_nodes_may_import_services(self, tmp_path):
        plant(tmp_path, "graph/nodes/availability.py", "from services.stock import Stock\n")
        assert find_violations(tmp_path) == []

    def test_streamlit_outside_ui_is_caught(self, tmp_path):
        plant(tmp_path, "config.py", "import streamlit\n")
        plant(tmp_path, "graph/build.py", "\n\nfrom streamlit import session_state\n")
        assert find_violations(tmp_path) == [
            "config.py:1 streamlit-only-in-ui: streamlit",
            "graph/build.py:3 streamlit-only-in-ui: streamlit",
        ]

    def test_streamlit_in_ui_and_app_is_allowed(self, tmp_path):
        plant(tmp_path, "app.py", "import streamlit as st\n")
        plant(tmp_path, "ui/results.py", "import streamlit as st\n")
        assert find_violations(tmp_path) == []

    def test_one_line_per_offending_statement(self, tmp_path):
        plant(tmp_path, "services/a.py", "import langgraph\nimport streamlit\n")
        assert find_violations(tmp_path) == [
            "services/a.py:1 services-no-runtime: langgraph",
            "services/a.py:2 services-no-runtime: streamlit",
        ]

    def test_tests_and_scripts_are_not_scanned(self, tmp_path):
        plant(tmp_path, "tests/test_x.py", "import streamlit\n")
        plant(tmp_path, "scripts/tool.py", "import streamlit\n")
        plant(tmp_path, ".venv/lib/streamlit/x.py", "import streamlit\n")
        assert find_violations(tmp_path) == []

    def test_the_repository_obeys_every_rule(self):
        assert find_violations(REPO) == []
