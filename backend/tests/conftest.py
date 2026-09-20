from pathlib import Path

import pytest

from app.config import Settings
from app.db.session_store import SessionStore
from app.safety.sandbox import WorkspaceSandbox


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    root = tmp_path / "workspace"; root.mkdir()
    return Settings(workspace_root=root, sqlite_path=tmp_path / "harness.db", audit_log_path=tmp_path / "audit.log", rate_limit_rpm=3, max_concurrent_requests=1, cooldown_trigger_count=2, cooldown_seconds=1, max_iterations=6, max_wall_clock_seconds=5, max_total_tokens_per_session=256, max_output_tokens_per_turn=64)

@pytest.fixture
def sandbox(settings: Settings) -> WorkspaceSandbox:
    return WorkspaceSandbox(settings)

@pytest.fixture
def store(settings: Settings) -> SessionStore:
    return SessionStore(settings.sqlite_path)
