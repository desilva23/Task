"""Root conftest: every test session enforces traceability (constitution Principle III)."""

pytest_plugins = ["tests.guards.trace_plugin"]
