import pytest

from app.tools.fs_tools import FileTools


def test_list_files_pattern_and_create_directory(settings, sandbox):
    fs = FileTools(settings, sandbox)

    (settings.workspace_root / "src").mkdir()
    (settings.workspace_root / "src" / "main.py").write_text("print('main')", encoding="utf-8")
    (settings.workspace_root / "src" / "styles.css").write_text("body {}", encoding="utf-8")

    # Pattern filtering
    py_files = fs.list_files(".", depth=3, pattern="*.py")
    paths = [e["path"] for e in py_files["entries"]]
    assert "src/main.py" in paths
    assert "src/styles.css" not in paths

    # Create directory dry-run
    dry_res = fs.create_directory("src/components", dry_run=True)
    assert dry_res["applied"] is False
    assert dry_res["dry_run"] is True
    assert not (settings.workspace_root / "src" / "components").exists()

    # Create directory live
    live_res = fs.create_directory("src/components", dry_run=False)
    assert live_res["applied"] is True
    assert (settings.workspace_root / "src" / "components").is_dir()
