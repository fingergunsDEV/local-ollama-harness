from pathlib import Path
import pytest

from app.config import Settings
from app.indexing.embeddings import LocalEmbeddings, cosine_similarity
from app.ollama_client import OllamaClient
from app.safety.rate_limiter import OllamaRateLimiter
from app.safety.sandbox import WorkspaceSandbox
from app.tools import ToolRegistry
from app.tools.search_tools import SearchTools


def test_search_tools_respects_ignores(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    settings = Settings(workspace_root=root, sqlite_path=tmp_path / "harness.db", audit_log_path=tmp_path / "audit.log")
    sandbox = WorkspaceSandbox(settings)

    # Create normal file, gitignored file, and harnessignored file
    (root / "visible.txt").write_text("secret_keyword_here", encoding="utf-8")
    ignored_dir = root / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.txt").write_text("secret_keyword_here", encoding="utf-8")
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")

    search_tools = SearchTools(settings, sandbox)
    results = search_tools.keyword_search(query="secret_keyword_here")["results"]

    paths = [r["path"] for r in results]
    assert "visible.txt" in paths
    assert "ignored/hidden.txt" not in paths


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3)) == 0.0
    assert cosine_similarity([], v1) == 0.0


@pytest.mark.asyncio
async def test_local_embeddings(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    settings = Settings(workspace_root=root, sqlite_path=tmp_path / "harness.db", audit_log_path=tmp_path / "audit.log")
    limiter = OllamaRateLimiter(settings)

    class DummyClient(OllamaClient):
        async def embed(self, model: str, prompt: str) -> list[float]:
            return [0.1, 0.2, 0.3]

    dummy = DummyClient(settings, limiter)
    emb = LocalEmbeddings(dummy)
    res = await emb.get_embedding("nomic-embed-text", "hello world")
    assert res == [0.1, 0.2, 0.3]

    empty = await emb.get_embedding("nomic-embed-text", "   ")
    assert empty == []

    matches = emb.search_vectors([0.1, 0.2, 0.3], [{"id": 1, "vector": [0.1, 0.2, 0.3]}, {"id": 2, "vector": [1.0, 0.0, 0.0]}], top_k=1)
    assert len(matches) == 1
    assert matches[0]["id"] == 1


def test_pre_mutation_snapshot(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    settings = Settings(workspace_root=root, sqlite_path=tmp_path / "harness.db", audit_log_path=tmp_path / "audit.log")
    registry = ToolRegistry(settings)

    target = root / "sample.txt"
    target.write_text("original content", encoding="utf-8")

    # Overwrite file with dry_run=False
    write_res = registry.files.write_file("sample.txt", "updated content", dry_run=False)
    assert write_res["applied"] is True
    assert "snapshot" in write_res

    snapshot_file = root / ".harness-snapshots" / write_res["snapshot"]
    assert snapshot_file.exists()
    assert snapshot_file.read_text(encoding="utf-8") == "original content"

    # Delete file with dry_run=False
    del_res = registry.files.delete_file("sample.txt", dry_run=False)
    assert del_res["applied"] is True
    assert "snapshot" in del_res
    del_snapshot = root / ".harness-snapshots" / del_res["snapshot"]
    assert del_snapshot.exists()
    assert del_snapshot.read_text(encoding="utf-8") == "updated content"
