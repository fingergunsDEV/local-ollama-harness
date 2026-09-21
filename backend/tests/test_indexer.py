from app.indexing.indexer import LocalIndexer


import pytest

@pytest.mark.asyncio
async def test_indexer_honors_gitignore_and_harnessignore(settings, sandbox, store):
    (settings.workspace_root / ".gitignore").write_text("ignored.txt\n")
    (settings.workspace_root / ".harnessignore").write_text("private/\n")
    (settings.workspace_root / "visible.txt").write_text("visible")
    (settings.workspace_root / "ignored.txt").write_text("ignored")
    private = settings.workspace_root / "private"; private.mkdir(); (private / "secret.txt").write_text("secret")
    await LocalIndexer(settings, sandbox, store).refresh()
    with store._connect() as conn:
        paths = {row[0] for row in conn.execute("SELECT path FROM file_index")}
    assert "visible.txt" in paths
    assert "ignored.txt" not in paths
    assert "private/secret.txt" not in paths
