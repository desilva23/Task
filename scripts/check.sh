#!/usr/bin/env bash
# The one check: lint, format, tests. CI runs exactly this. Stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff check";        uv run --locked ruff check .
echo "== ruff format --check"; uv run --locked ruff format --check .
echo "== pytest";            uv run --locked pytest
