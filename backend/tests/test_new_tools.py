import pytest
from app.config import Settings
from app.indexing.embeddings import OllamaEmbeddings, cosine_similarity
from app.safety.sandbox import WorkspaceSandbox
from app.tools.fs_tools import FileTools
from app.tools.search_tools import SearchTools


def test_replace_in_file_dry_run(sandbox: WorkspaceSandbox, settings: Settings):
    files = FileTools(settings, sandbox)
    test_file = sandbox.root / "sample.txt"
    test_file.write_text("hello world\npython agent harness\nfoo bar\n")

    res = files.replace_in_file("sample.txt", "python agent", "awesome agent", dry_run=True)
    assert res["applied"] is False
    assert res["dry_run"] is True
    assert "awesome agent" in res["diff"]
    # File content remains unchanged in dry-run
    assert test_file.read_text() == "hello world\npython agent harness\nfoo bar\n"


def test_replace_in_file_live(sandbox: WorkspaceSandbox, settings: Settings):
    files = FileTools(settings, sandbox)
    test_file = sandbox.root / "sample.txt"
    test_file.write_text("hello world\npython agent harness\nfoo bar\n")

    res = files.replace_in_file("sample.txt", "python agent", "awesome agent", dry_run=False)
    assert res["applied"] is True
    assert res["dry_run"] is False
    assert test_file.read_text() == "hello world\nawesome agent harness\nfoo bar\n"


def test_replace_in_file_validation_errors(sandbox: WorkspaceSandbox, settings: Settings):
    files = FileTools(settings, sandbox)
    test_file = sandbox.root / "sample.txt"
    test_file.write_text("dup dup\nhello world\n")

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        files.replace_in_file("missing.txt", "a", "b", dry_run=True)

    # Empty old_string
    with pytest.raises(ValueError, match="old_string cannot be empty"):
        files.replace_in_file("sample.txt", "", "b", dry_run=True)

    # String not found
    with pytest.raises(ValueError, match="not found"):
        files.replace_in_file("sample.txt", "nonexistent", "b", dry_run=True)

    # Non-unique string
    with pytest.raises(ValueError, match="found 2 times"):
        files.replace_in_file("sample.txt", "dup", "b", dry_run=True)


def test_regex_search(sandbox: WorkspaceSandbox, settings: Settings):
    search = SearchTools(settings, sandbox)
    (sandbox.root / "file1.py").write_text("def hello_world():\n    return 42\n")
    (sandbox.root / "file2.txt").write_text("log entry: error 500\nlog entry: info 200\n")

    res = search.regex_search(pattern=r"def \w+\(\):", path=".")
    assert len(res["results"]) == 1
    assert res["results"][0]["path"] == "file1.py"

    res_filter = search.regex_search(pattern=r"log entry", path=".", file_pattern="*.txt")
    assert len(res_filter["results"]) == 2
    assert res_filter["results"][0]["path"] == "file2.txt"

    with pytest.raises(ValueError, match="invalid regex pattern"):
        search.regex_search(pattern="[invalid regex(")


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 1.0], [-1.0, -1.0]) == pytest.approx(-1.0)
    assert cosine_similarity([], []) == 0.0


@pytest.mark.asyncio
async def test_ollama_embeddings_search_similar(settings: Settings):
    class DummyClient:
        async def embed(self, model: str, texts: list[str]):
            # Mock vectors for "python code", "python async", "java class"
            mapping = {
                "python": [1.0, 0.0],
                "python async": [0.9, 0.1],
                "java class": [0.0, 1.0],
            }
            return [mapping.get(t, [0.5, 0.5]) for t in texts]

    embeddings = OllamaEmbeddings(settings, DummyClient()) # type: ignore
    docs = [
        {"id": 1, "content": "python async"},
        {"id": 2, "content": "java class"},
    ]
    results = await embeddings.search_similar("llama3", "python", docs, top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[0]["similarity"] > results[1]["similarity"]
