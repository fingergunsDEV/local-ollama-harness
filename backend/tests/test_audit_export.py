import pytest
from fastapi.testclient import TestClient


def test_audit_filtering_and_csv_export(tmp_path):
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

    # Log some audit entries
    audit_logger = app.state.runtime.audit
    audit_logger.log(
        session_id="s1",
        actor="user",
        action_type="session_create",
        tool_name=None,
        target="target1",
        result="success",
        dry_run=False,
    )
    audit_logger.log(
        session_id="s2",
        actor="agent",
        action_type="tool_call",
        tool_name="read_file",
        target="target2",
        result="denied",
        dry_run=True,
    )

    # Filter by session_id
    res_s1 = client.get("/api/audit?session_id=s1")
    assert res_s1.status_code == 200
    entries = res_s1.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["session_id"] == "s1"

    # Filter by actor
    res_actor = client.get("/api/audit?actor=agent")
    assert res_actor.status_code == 200
    entries = res_actor.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["actor"] == "agent"

    # Filter by action_type and result
    res_filtered = client.get("/api/audit?action_type=tool_call&result=denied")
    assert res_filtered.status_code == 200
    entries = res_filtered.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["tool_name"] == "read_file"

    # Export CSV
    res_csv = client.get("/api/audit?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    assert "id,session_id,actor,action_type,tool_name,target,result,created_at" in csv_text
    assert "s1,user,session_create" in csv_text
    assert "s2,agent,tool_call,read_file,target2,denied" in csv_text
