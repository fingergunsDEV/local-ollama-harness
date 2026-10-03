from pathlib import Path
import pytest
from app.config import Settings
from app.tools import ToolRegistry

def test_list_and_restore_snapshots(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    settings = Settings(
        workspace_root=root,
        sqlite_path=tmp_path / "harness.db",
        audit_log_path=tmp_path / "audit.log",
        rate_limit_rpm=3,
        max_concurrent_requests=1,
        cooldown_trigger_count=2,
        cooldown_seconds=1,
        max_iterations=6,
        max_wall_clock_seconds=5,
        max_total_tokens_per_session=256,
        max_output_tokens_per_turn=64
    )
    tools = ToolRegistry(settings)

    # Create a target file
    target = root / "sample.txt"
    target.write_text("v1 content", encoding="utf-8")

    # Take snapshot
    snap_id = tools.snapshot("sess-100", "sample.txt")
    assert snap_id is not None

    # Modify file
    target.write_text("v2 content", encoding="utf-8")

    # List snapshots
    snapshots = tools.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0]["snapshot_id"] == snap_id
    assert snapshots[0]["session_id"] == "sess-100"
    assert snapshots[0]["original_filename"] == "sample.txt"

    # Restore snapshot
    res = tools.restore_snapshot(snap_id, "sample.txt")
    assert res["restored"] is True
    assert target.read_text(encoding="utf-8") == "v1 content"
