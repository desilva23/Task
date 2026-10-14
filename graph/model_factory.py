"""Choose the model: GroqCloud when a key is configured, otherwise the fallbacks alone.

The key is read from the environment — on Vercel, a project environment variable — or, for local
runs, from ``.streamlit/secrets.toml``, which is gitignored and kept for that one line.
"""

import os
import tomllib
from pathlib import Path

from config import MODEL_CALLS_PER_SESSION
from graph.groq_client import GroqClient
from graph.model import NoModel

SECRETS = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def api_key(secrets_file: Path = SECRETS) -> str | None:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    if secrets_file.is_file():
        return tomllib.loads(secrets_file.read_text()).get("GROQ_API_KEY") or None
    return None


def make_model(secrets_file: Path = SECRETS, budget: int = MODEL_CALLS_PER_SESSION):
    key = api_key(secrets_file)
    return GroqClient(key, budget=budget) if key and budget > 0 else NoModel()
