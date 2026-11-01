import os
from pathlib import Path
import tempfile

# Set a valid WORKSPACE_ROOT in environment before app.main is imported
_temp_dir = tempfile.mkdtemp()
_workspace = Path(_temp_dir) / "workspace"
_workspace.mkdir(parents=True, exist_ok=True)
os.environ["WORKSPACE_ROOT"] = str(_workspace)

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, Runtime
from app.safety.sandbox import WorkspaceSandbox
from app.tools.fs_tools import FileTools


@pytest.fixture
def client(settings):
    with TestClient(app) as test_client:
        runtime = Runtime(settings)
        app.state.runtime = runtime
        yield test_client


def test_patch_file_dry_run(settings):
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    # Create a test file
    sample = settings.workspace_root / "sample.py"
    sample.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    result = files.patch_file(
        path="sample.py",
        search="return 'world'",
        replace="return 'universe'",
        dry_run=True,
    )

    assert result["applied"] is False
    assert result["dry_run"] is True
    assert result["action"] == "patch"
    assert "-    return 'world'" in result["diff"]
    assert "+    return 'universe'" in result["diff"]
    # Verify file was NOT modified
    assert sample.read_text(encoding="utf-8") == "def hello():\n    return 'world'\n"


def test_patch_file_live_success(settings):
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    sample = settings.workspace_root / "sample_live.py"
    sample.write_text("x = 10\ny = 20\n", encoding="utf-8")

    result = files.patch_file(
        path="sample_live.py",
        search="y = 20",
        replace="y = 42",
        dry_run=False,
    )

    assert result["applied"] is True
    assert result["dry_run"] is False
    assert result["action"] == "patch"
    assert sample.read_text(encoding="utf-8") == "x = 10\ny = 42\n"


def test_patch_file_target_mismatch(settings):
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    sample = settings.workspace_root / "mismatch.txt"
    sample.write_text("foo bar baz\nfoo bar 123\n", encoding="utf-8")

    # Target not found
    with pytest.raises(ValueError, match="search block not found"):
        files.patch_file("mismatch.txt", "nonexistent string", "new")

    # Ambiguous target (occurs multiple times)
    with pytest.raises(ValueError, match="patch must be unique"):
        files.patch_file("mismatch.txt", "foo bar", "new")

    # Empty search string
    with pytest.raises(ValueError, match="search string cannot be empty"):
        files.patch_file("mismatch.txt", "", "new")


def test_list_snapshots_and_restore(client, settings):
    # Create a test file in workspace
    doc = settings.workspace_root / "doc.txt"
    doc.write_text("Original content version 1", encoding="utf-8")

    # Tool registry snapshot method
    tools = app.state.runtime.tools
    snapshot_id = tools.snapshot("test-session", "doc.txt")
    assert snapshot_id is not None

    # Test GET /api/snapshots
    res = client.get("/api/snapshots")
    assert res.status_code == 200
    snapshots = res.json()["snapshots"]
    assert len(snapshots) >= 1
    found = next((s for s in snapshots if s["id"] == snapshot_id), None)
    assert found is not None
    assert found["size"] > 0
    assert "created_at" in found

    # Overwrite doc.txt
    doc.write_text("Overwritten content version 2", encoding="utf-8")
    assert doc.read_text(encoding="utf-8") == "Overwritten content version 2"

    # Test POST /api/snapshots/restore
    restore_res = client.post("/api/snapshots/restore", json={
        "snapshot_id": snapshot_id,
        "path": "doc.txt"
    })
    assert restore_res.status_code == 200
    assert restore_res.json()["restored"] is True
    assert doc.read_text(encoding="utf-8") == "Original content version 1"
