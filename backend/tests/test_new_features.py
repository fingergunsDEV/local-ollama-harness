import pytest
from app.config import Settings
from app.indexing.embeddings import LocalSemanticIndexer, cosine_similarity
from app.tools import ToolRegistry


def test_batch_read_files(settings: Settings):
    workspace_dir = settings.workspace_root
    f1 = workspace_dir / "file1.txt"
    f2 = workspace_dir / "file2.txt"
    f1.write_text("Hello file 1", encoding="utf-8")
    f2.write_text("Hello file 2", encoding="utf-8")

    registry = ToolRegistry(settings)
    res = registry.execute("batch_read_files", {"paths": ["file1.txt", "file2.txt"]}, dry_run=False)
    assert res["count"] == 2
    assert len(res["files"]) == 2
    assert res["files"][0]["content"] == "Hello file 1"
    assert res["files"][1]["content"] == "Hello file 2"


def test_batch_read_files_with_error(settings: Settings):
    workspace_dir = settings.workspace_root
    f1 = workspace_dir / "file1.txt"
    f1.write_text("Hello file 1", encoding="utf-8")

    registry = ToolRegistry(settings)
    res = registry.execute("batch_read_files", {"paths": ["file1.txt", "nonexistent.txt"]}, dry_run=False)
    assert res["count"] == 2
    assert res["files"][0]["content"] == "Hello file 1"
    assert "error" in res["files"][1]


def test_create_directory_dry_run_and_live(settings: Settings):
    workspace_dir = settings.workspace_root
    registry = ToolRegistry(settings)

    # Dry run
    res_dry = registry.execute("create_directory", {"path": "new_folder"}, dry_run=True)
    assert res_dry["applied"] is False
    assert res_dry["dry_run"] is True
    assert not (workspace_dir / "new_folder").exists()

    # Live apply
    res_live = registry.execute("create_directory", {"path": "new_folder"}, dry_run=False)
    assert res_live["applied"] is True
    assert res_live["dry_run"] is False
    assert (workspace_dir / "new_folder").is_dir()

    # Re-creating fails
    with pytest.raises(FileExistsError):
        registry.execute("create_directory", {"path": "new_folder"}, dry_run=False)


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)
    assert cosine_similarity([], v1) == 0.0
