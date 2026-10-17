import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_session_export_json_and_markdown(tmp_path, monkeypatch):
    from app.config import Settings
    from app.main import Runtime, app

    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    test_settings = Settings(
        workspace_root=ws,
        sqlite_path=tmp_path / "data" / "harness.db",
        audit_log_path=tmp_path / "data" / "audit.jsonl",
    )
    app.state.runtime = Runtime(test_settings)
    client = TestClient(app)

    # Create session
    create_res = client.post("/api/sessions", json={"model": "test-model", "dry_run": True})
    assert create_res.status_code == 200
    session_id = create_res.json()["id"]

    # Add messages directly to store
    store = app.state.runtime.store
    store.add_message(session_id, "user", "Hello agent!")
    store.add_message(session_id, "assistant", "Hello user, I am ready.")

    # Export JSON
    json_res = client.get(f"/api/sessions/{session_id}/export?format=json")
    assert json_res.status_code == 200
    data = json_res.json()
    assert data["session"]["id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "Hello agent!"

    # Export Markdown
    md_res = client.get(f"/api/sessions/{session_id}/export?format=markdown")
    assert md_res.status_code == 200
    assert "text/markdown" in md_res.headers["content-type"]
    md_text = md_res.text
    assert f"# Session Export: {session_id}" in md_text
    assert "### User" in md_text
    assert "Hello agent!" in md_text
    assert "### Assistant" in md_text
    assert "Hello user, I am ready." in md_text

    # Invalid format
    err_res = client.get(f"/api/sessions/{session_id}/export?format=xml")
    assert err_res.status_code == 400
