import pytest
from fastapi.testclient import TestClient


def test_session_export_json_and_markdown(sandbox, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(sandbox.root))
    monkeypatch.setenv("SQLITE_PATH", str(sandbox.root / "harness.db"))
    from app.main import app, Runtime
    from app.config import get_settings

    app.state.runtime = Runtime(get_settings())

    client = TestClient(app)
    # Create session
    create_res = client.post("/api/sessions", json={"model": "test-model", "dry_run": True})
    assert create_res.status_code == 200
    session_id = create_res.json()["id"]

    # Add messages
    rt = app.state.runtime
    rt.store.add_message(session_id, "user", "Hello agent")
    rt.store.add_message(session_id, "assistant", "Hello user")

    # Export JSON
    json_res = client.get(f"/api/sessions/{session_id}/export?format=json")
    assert json_res.status_code == 200
    data = json_res.json()
    assert data["session"]["id"] == session_id
    assert len(data["messages"]) == 2

    # Export Markdown
    md_res = client.get(f"/api/sessions/{session_id}/export?format=md")
    assert md_res.status_code == 200
    assert md_res.headers["content-type"].startswith("text/markdown")
    md_text = md_res.text
    assert f"# Session Export: {session_id}" in md_text
    assert "### USER" in md_text
    assert "Hello agent" in md_text
