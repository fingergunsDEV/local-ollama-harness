from app.tools.fs_tools import FileTools
from app.tools import ToolRegistry


def test_dry_run_produces_diff_and_keeps_files_unchanged(settings, sandbox):
    target = settings.workspace_root / "note.txt"; target.write_text("before\n")
    files = FileTools(settings, sandbox)
    outcome = files.write_file("note.txt", "after\n", dry_run=True)
    assert outcome["dry_run"] and not outcome["applied"]
    assert "-before" in outcome["diff"] and "+after" in outcome["diff"]
    assert target.read_text() == "before\n"

def test_write_limit_rejects_oversized_content(settings, sandbox):
    settings.max_file_write_bytes = 3
    files = FileTools(settings, sandbox)
    try: files.create_file("big.txt", "1234", dry_run=True)
    except Exception as exc: assert "MAX_FILE_WRITE_BYTES" in str(exc)
    else: raise AssertionError("expected size limit")

def test_snapshot_restore_is_user_controlled_and_workspace_scoped(settings, sandbox):
    target = settings.workspace_root / "note.txt"; target.write_text("before\n")
    tools = ToolRegistry(settings)
    snapshot = tools.snapshot("session", "note.txt")
    target.write_text("after\n")
    restored = tools.restore_snapshot(snapshot or "", "note.txt")
    assert restored["restored"] and target.read_text() == "before\n"
