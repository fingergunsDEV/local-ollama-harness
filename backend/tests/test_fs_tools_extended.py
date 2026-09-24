import pytest
from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox
from app.tools.fs_tools import FileTools


def test_move_file_dry_run_and_execution(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    src = tmp_path / "src.txt"
    src.write_text("hello world")

    # Dry run
    res_dry = files.move_file("src.txt", "dst.txt", dry_run=True)
    assert res_dry["dry_run"] is True
    assert res_dry["applied"] is False
    assert src.exists()

    # Live execution
    res_live = files.move_file("src.txt", "dst.txt", dry_run=False)
    assert res_live["applied"] is True
    assert not src.exists()
    assert (tmp_path / "dst.txt").read_text() == "hello world"


def test_copy_file_dry_run_and_execution(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    src = tmp_path / "original.txt"
    src.write_text("copy content")

    # Dry run
    res_dry = files.copy_file("original.txt", "copy.txt", dry_run=True)
    assert res_dry["dry_run"] is True
    assert res_dry["applied"] is False

    # Live execution
    res_live = files.copy_file("original.txt", "copy.txt", dry_run=False)
    assert res_live["applied"] is True
    assert src.exists()
    assert (tmp_path / "copy.txt").read_text() == "copy content"


def test_move_file_outside_sandbox_denied(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    files = FileTools(settings, sandbox)

    src = tmp_path / "file.txt"
    src.write_text("data")

    with pytest.raises((PermissionError, ValueError)):
        files.move_file("file.txt", "../outside.txt", dry_run=False)
