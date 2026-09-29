import pytest
from app.config import Settings
from app.safety.sandbox import WorkspaceSandbox
from app.tools.search_tools import SearchTools


def test_regex_search(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    search_tools = SearchTools(settings, sandbox)

    file_a = tmp_path / "a.py"
    file_a.write_text("def process_data(value):\n    return value * 2\n", encoding="utf-8")

    file_b = tmp_path / "b.txt"
    file_b.write_text("This is process_data in plain text.\n", encoding="utf-8")

    # Test regex search for function def
    res = search_tools.keyword_search("def\\s+process_data", path=".", is_regex=True)
    assert len(res["results"]) == 1
    assert res["results"][0]["path"] == "a.py"

    # Test extension filter
    res_py = search_tools.keyword_search("process_data", path=".", file_pattern=".py")
    assert len(res_py["results"]) == 1
    assert res_py["results"][0]["path"] == "a.py"


def test_invalid_regex(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    sandbox = WorkspaceSandbox(settings)
    search_tools = SearchTools(settings, sandbox)

    with pytest.raises(ValueError, match="invalid regex pattern"):
        search_tools.keyword_search("[unclosed_bracket", path=".", is_regex=True)
