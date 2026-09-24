from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox
from app.tools.search_tools import SearchTools


def test_keyword_search_respects_gitignore(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    search_tools = SearchTools(settings, sandbox)

    # Create tracked file and ignored file
    (tmp_path / ".gitignore").write_text("ignored.txt\nnode_modules/\n")
    (tmp_path / "tracked.txt").write_text("find_me_here")
    (tmp_path / "ignored.txt").write_text("find_me_here")

    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "pkg.txt").write_text("find_me_here")

    results = search_tools.keyword_search("find_me_here")
    found_paths = [r["path"] for r in results["results"]]

    assert "tracked.txt" in found_paths
    assert "ignored.txt" not in found_paths
    assert "node_modules/pkg.txt" not in found_paths
