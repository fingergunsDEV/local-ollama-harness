import pytest
from fastapi.testclient import TestClient


def test_audit_export_json_and_csv(sandbox, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(sandbox.root))
    monkeypatch.setenv("SQLITE_PATH", str(sandbox.root / "harness.db"))
    from app.main import app, Runtime
    from app.config import get_settings

    app.state.runtime = Runtime(get_settings())

    client = TestClient(app)
    # Log an audit entry
    rt = app.state.runtime
    rt.audit.log(
        session_id="test-session-123",
        actor="user",
        action_type="test_action",
        tool_name="read_file",
        target="foo.txt",
        result="success",
        dry_run=True,
    )

    # Export JSON
    json_res = client.get("/api/audit/export?format=json")
    assert json_res.status_code == 200
    data = json_res.json()
    assert "entries" in data
    assert any(e["action_type"] == "test_action" for e in data["entries"])

    # Export CSV
    csv_res = client.get("/api/audit/export?format=csv")
    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"].startswith("text/csv")
    csv_text = csv_res.text
    assert "id,session_id,actor,action_type" in csv_text
    assert "test_action" in csv_text
    assert "foo.txt" in csv_text
