import subprocess
from pathlib import Path

import pytest

from tests.guards.secret_files import NotAWorkTree, tracked_secret_files

REPO = Path(__file__).resolve().parents[2]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def repo_with(root: Path, *files: str) -> Path:
    git(root, "init", "-q")
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("GROQ_API_KEY = 'not-a-real-key'\n")
        git(root, "add", "-f", rel)
    return root


class TestSecretFiles:
    """CONST-SECRETS — a secrets file can never be tracked in the public repository."""

    def test_tracked_env_is_caught(self, tmp_path):
        assert tracked_secret_files(repo_with(tmp_path, ".env")) == [".env"]

    def test_tracked_secrets_toml_is_caught_at_any_depth(self, tmp_path):
        root = repo_with(tmp_path, "app/.streamlit/secrets.toml", "deep/er/.env")
        assert tracked_secret_files(root) == ["app/.streamlit/secrets.toml", "deep/er/.env"]

    def test_an_example_file_is_not_flagged(self, tmp_path):
        assert (
            tracked_secret_files(repo_with(tmp_path, ".env.example", "secrets.toml.example")) == []
        )

    def test_outside_a_work_tree_it_fails_rather_than_passing(self, tmp_path):
        with pytest.raises(NotAWorkTree):
            tracked_secret_files(tmp_path)

    def test_the_repository_tracks_no_secrets_file(self):
        assert tracked_secret_files(REPO) == []

    @pytest.mark.parametrize("rel", [".env", ".streamlit/secrets.toml"])
    def test_the_repository_ignores_both_names(self, rel):
        result = subprocess.run(["git", "check-ignore", "-q", rel], cwd=REPO)
        assert result.returncode == 0, f"{rel} is not gitignored"
