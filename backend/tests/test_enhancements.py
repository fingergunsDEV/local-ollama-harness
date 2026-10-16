import json
import pytest
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.db.session_store import SessionStore
from app.indexing.embeddings import LocalEmbeddingProvider
from app.indexing.indexer import LocalIndexer
from app.tools import TOOL_SCHEMAS, ToolRegistry


def test_tool_schemas_contains_semantic_search():
    tool_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    assert "semantic_search" in tool_names


@pytest.mark.asyncio
async def test_tool_registry_semantic_search_execution(settings, sandbox, store):
    (settings.workspace_root / "test.txt").write_text("Local LLM Agent Harness")
    indexer = LocalIndexer(settings, sandbox, store)
    indexer.refresh()

    mock_provider = AsyncMock(spec=LocalEmbeddingProvider)
    mock_provider.embed.side_effect = lambda text: [[0.1, 0.2, 0.3]] if isinstance(text, str) else [[0.1, 0.2, 0.3] for _ in text]

    await indexer.generate_embeddings_for_file("test.txt", mock_provider)

    registry = ToolRegistry(settings, indexer=indexer)
    with patch("app.tools.search_tools.LocalEmbeddingProvider", return_value=mock_provider):
        res = registry.execute("semantic_search", {"query": "Harness", "top_k": 3}, dry_run=False)
        if hasattr(res, "__await__"):
            res = await res
        assert "results" in res
        assert len(res["results"]) > 0
        assert res["results"][0]["path"] == "test.txt"


def test_audit_filtering_in_store(store):
    store.add_audit({"session_id": "s1", "actor": "user", "action_type": "chat", "tool_name": None, "target": None, "result": "success", "dry_run": False, "timestamp": "2026-10-16T12:00:00Z"})
    store.add_audit({"session_id": "s1", "actor": "agent", "action_type": "write", "tool_name": "write_file", "target": "a.txt", "result": "success", "dry_run": True, "timestamp": "2026-10-16T12:01:00Z"})
    store.add_audit({"session_id": "s2", "actor": "agent", "action_type": "exec", "tool_name": "exec", "target": "ls", "result": "denied", "dry_run": False, "timestamp": "2026-10-16T12:02:00Z"})

    # Filter by actor
    user_audits = store.audit_entries(actor="user")
    assert len(user_audits) == 1
    assert user_audits[0]["actor"] == "user"

    # Filter by result
    denied_audits = store.audit_entries(result="denied")
    assert len(denied_audits) == 1
    assert denied_audits[0]["result"] == "denied"

    # Filter by session_id
    s1_audits = store.audit_entries(session_id="s1")
    assert len(s1_audits) == 2


def test_audit_and_session_export_endpoints(settings, store, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(settings.workspace_root))
    monkeypatch.setenv("SQLITE_PATH", str(settings.sqlite_path))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(settings.audit_log_path))

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        app.state.runtime.settings = settings
        app.state.runtime.store = store

        session = store.create_session("llama3", False, "/workspace")
        store.add_message(session["id"], "user", "Hello agent")
        store.add_message(session["id"], "assistant", "Hello! How can I help?")
        store.add_audit({"session_id": session["id"], "actor": "user", "action_type": "chat", "tool_name": None, "target": None, "result": "success", "dry_run": False, "timestamp": "2026-10-16T12:00:00Z"})

        # Test audit export JSON
        res_audit_json = client.get(f"/api/audit/export?format=json&session_id={session['id']}")
        assert res_audit_json.status_code == 200
        data_audit_json = res_audit_json.json()
        assert "entries" in data_audit_json
        assert len(data_audit_json["entries"]) == 1

        # Test audit export CSV
        res_audit_csv = client.get(f"/api/audit/export?format=csv&session_id={session['id']}")
        assert res_audit_csv.status_code == 200
        assert "text/csv" in res_audit_csv.headers["content-type"]
        assert "actor,action_type" in res_audit_csv.text

        # Test session export JSON
        res_sess_json = client.get(f"/api/sessions/{session['id']}/export?format=json")
        assert res_sess_json.status_code == 200
        sess_json = res_sess_json.json()
        assert sess_json["session"]["id"] == session["id"]
        assert len(sess_json["messages"]) == 2

        # Test session export Markdown
        res_sess_md = client.get(f"/api/sessions/{session['id']}/export?format=markdown")
        assert res_sess_md.status_code == 200
        assert "text/markdown" in res_sess_md.headers["content-type"]
        assert "# Session Transcript:" in res_sess_md.text
        assert "### User" in res_sess_md.text
