"""Choose the model: GroqCloud when a key is configured, otherwise the fallbacks alone.

The key is read from the environment — Streamlit Community Cloud exports top-level secrets as
environment variables — or, for local runs outside Streamlit, from ``.streamlit/secrets.toml``.
"""

import os
import tomllib
from pathlib import Path

from graph.groq_client import GroqClient
from graph.model import NoModel

SECRETS = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def api_key(secrets_file: Path = SECRETS) -> str | None:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    if secrets_file.is_file():
        return tomllib.loads(secrets_file.read_text()).get("GROQ_API_KEY") or None
    return None


def make_model(secrets_file: Path = SECRETS):
    key = api_key(secrets_file)
    return GroqClient(key) if key else NoModel()
