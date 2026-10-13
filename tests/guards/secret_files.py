"""The secrets rule: no file named ``.env`` or ``secrets.toml`` is tracked, at any depth."""

import subprocess
from pathlib import Path, PurePosixPath

SECRET_NAMES = {".env", "secrets.toml"}


class NotAWorkTree(RuntimeError):
    """Raised instead of passing when git cannot say what is tracked."""


def tracked_secret_files(root: Path) -> list[str]:
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NotAWorkTree(f"cannot list tracked files in {root}: {exc}") from exc
    tracked = [p for p in listing.decode().split("\0") if p]
    return sorted(p for p in tracked if PurePosixPath(p).name in SECRET_NAMES)
