from app.tools.search_tools import SearchTools


def test_search_tools_honors_ignore_spec(settings, sandbox):
    (settings.workspace_root / ".gitignore").write_text("ignored.txt\n")
    (settings.workspace_root / ".harnessignore").write_text("private/\n")
    (settings.workspace_root / "visible.txt").write_text("findme_content")
    (settings.workspace_root / "ignored.txt").write_text("findme_content")
    private = settings.workspace_root / "private"
    private.mkdir()
    (private / "secret.txt").write_text("findme_content")

    search_tools = SearchTools(settings, sandbox)
    results = search_tools.keyword_search("findme_content")
    paths = {item["path"] for item in results["results"]}

    assert "visible.txt" in paths
    assert "ignored.txt" not in paths
    assert "private/secret.txt" not in paths
