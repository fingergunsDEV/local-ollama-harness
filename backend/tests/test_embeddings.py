import pytest
from app.indexing.embeddings import LocalEmbeddings
from app.tools.search_tools import SearchTools
from app.tools import ToolRegistry


class DummyOllamaClient:
    async def embeddings(self, model: str, prompt: str) -> list[float]:
        # Return simple deterministic dummy vector based on presence of keywords
        prompt_lower = prompt.lower()
        if "python" in prompt_lower or "code" in prompt_lower:
            return [1.0, 0.0, 0.0]
        elif "javascript" in prompt_lower or "node" in prompt_lower:
            return [0.0, 1.0, 0.0]
        else:
            return [0.5, 0.5, 0.5]


@pytest.mark.asyncio
async def test_cosine_similarity():
    sim = LocalEmbeddings._cosine_similarity([1.0, 0.0], [1.0, 0.0])
    assert pytest.approx(sim) == 1.0

    sim_ortho = LocalEmbeddings._cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert pytest.approx(sim_ortho) == 0.0


@pytest.mark.asyncio
async def test_local_embeddings_indexing_and_search(settings, sandbox, store):
    client = DummyOllamaClient()
    embeddings = LocalEmbeddings(settings, sandbox, store, client)

    # Create dummy files in workspace
    py_file = sandbox.root / "main.py"
    py_file.write_text("def hello(): print('Python code')")

    js_file = sandbox.root / "app.js"
    js_file.write_text("console.log('JavaScript node app');")

    ok_py = await embeddings.index_file("main.py")
    assert ok_py is True

    ok_js = await embeddings.index_file("app.js")
    assert ok_js is True

    res = await embeddings.search("python code")
    assert res["count"] == 2
    assert res["results"][0]["path"] == "main.py"
    assert res["results"][0]["score"] > res["results"][1]["score"]


@pytest.mark.asyncio
async def test_search_tools_semantic_search(settings, sandbox, store):
    client = DummyOllamaClient()
    embeddings = LocalEmbeddings(settings, sandbox, store, client)

    file_a = sandbox.root / "file_a.txt"
    file_a.write_text("Python language file")
    await embeddings.index_file("file_a.txt")

    search_tools = SearchTools(settings, sandbox, embeddings=embeddings)
    res = await search_tools.semantic_search(query="python")
    assert res["count"] == 1
    assert res["results"][0]["path"] == "file_a.txt"


@pytest.mark.asyncio
async def test_tool_registry_semantic_search(settings):
    registry = ToolRegistry(settings)
    assert "semantic_search" in registry._handlers
