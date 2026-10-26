import os
from pathlib import Path
import tempfile

_temp_dir = tempfile.mkdtemp()
_workspace = Path(_temp_dir) / "workspace"
_workspace.mkdir(parents=True, exist_ok=True)
os.environ["WORKSPACE_ROOT"] = str(_workspace)

import pytest
from fastapi.testclient import TestClient

from app.indexing.indexer import LocalIndexer
from app.main import app, Runtime
from app.safety.allowlist import CommandAllowlist, CommandDenied


@pytest.fixture
def client(settings):
    with TestClient(app) as test_client:
        runtime = Runtime(settings)
        app.state.runtime = runtime
        yield test_client


def test_indexer_get_status(settings, sandbox, store):
    indexer = LocalIndexer(settings, sandbox, store)
    indexer.refresh()
    status = indexer.get_status()

    assert "total_files_indexed" in status
    assert "total_embeddings" in status
    assert "embedded_files_count" in status
    assert "max_files_limit" in status
    assert status["max_files_limit"] == settings.max_files_indexed


def test_index_status_endpoint(client):
    response = client.get("/api/index/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_files_indexed" in data
    assert "total_embeddings" in data
    assert "embedded_files_count" in data


def test_command_allowlist_obfuscation_rejection(settings, sandbox):
    allowlist = CommandAllowlist(settings, sandbox)

    # Allowed command
    assert allowlist.validate(["git", "status"]) == ["git", "status"]

    # Obfuscated / subshell expansions must be denied
    with pytest.raises(CommandDenied, match="obfuscated escapes"):
        allowlist.validate(["git", "log", "\\x41\\x42"])

    with pytest.raises(CommandDenied, match="obfuscated escapes"):
        allowlist.validate(["git", "log", "${PATH}"])

    with pytest.raises(CommandDenied, match="obfuscated escapes"):
        allowlist.validate(["git", "log", "$(id)"])

    with pytest.raises(CommandDenied, match="metacharacters"):
        allowlist.validate(["git", "log", "`whoami`"])
