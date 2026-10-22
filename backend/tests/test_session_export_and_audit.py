import os
from pathlib import Path
import tempfile

# Set a valid WORKSPACE_ROOT in environment before app.main is imported
_temp_dir = tempfile.mkdtemp()
_workspace = Path(_temp_dir) / "workspace"
_workspace.mkdir(parents=True, exist_ok=True)
os.environ["WORKSPACE_ROOT"] = str(_workspace)

import pytest
from fastapi.testclient import TestClient

from app.main import app, Runtime


@pytest.fixture
def client(settings):
    # Ensure app runtime uses test settings and store inside TestClient context
    with TestClient(app) as test_client:
        runtime = Runtime(settings)
        app.state.runtime = runtime
        yield test_client


def test_session_export_and_fork(client, settings):
    store = app.state.runtime.store

    # Create a session
    res = client.post("/api/sessions", json={"model": "llama3.1:8b", "dry_run": True})
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Add messages
    m1 = store.add_message(session_id, "user", "Hello agent")
    m2 = store.add_message(session_id, "assistant", "Hello user")
    m3 = store.add_message(session_id, "user", "What is the capital of France?")

    # Test export markdown
    export_md = client.get(f"/api/sessions/{session_id}/export?format=markdown")
    assert export_md.status_code == 200
    assert "text/markdown" in export_md.headers["content-type"]
    assert "Session Export:" in export_md.text
    assert "Hello agent" in export_md.text

    # Test export json
    export_json = client.get(f"/api/sessions/{session_id}/export?format=json")
    assert export_json.status_code == 200
    data = export_json.json()
    assert data["session"]["id"] == session_id
    assert len(data["messages"]) == 3

    # Test fork up to m2
    fork_res = client.post(f"/api/sessions/{session_id}/fork", json={"up_to_message_id": m2})
    assert fork_res.status_code == 200
    forked_id = fork_res.json()["id"]
    assert forked_id != session_id

    # Verify forked session messages
    forked_get = client.get(f"/api/sessions/{forked_id}")
    assert forked_get.status_code == 200
    forked_msgs = forked_get.json()["messages"]
    assert len(forked_msgs) == 2
    assert forked_msgs[0]["content"] == "Hello agent"
    assert forked_msgs[1]["content"] == "Hello user"


def test_audit_filtering_and_csv_export(client, settings):
    audit_logger = app.state.runtime.audit
    # Add audit log entries with distinct session_ids
    audit_logger.log(
        session_id="s1_test",
        actor="user_unique",
        action_type="chat_unique",
        tool_name=None,
        target="prompt",
        result="success",
        dry_run=True,
    )
    audit_logger.log(
        session_id="s1_test",
        actor="agent_unique",
        action_type="write_file_unique",
        tool_name="write_file",
        target="test.txt",
        result="denied_unique",
        dry_run=False,
    )
    audit_logger.log(
        session_id="s2_test",
        actor="user_custom",
        action_type="custom_action_unique",
        tool_name=None,
        target=None,
        result="success",
        dry_run=True,
    )

    # Filter by actor
    res = client.get("/api/audit?actor=agent_unique")
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["actor"] == "agent_unique"
    assert entries[0]["action_type"] == "write_file_unique"

    # Filter by action_type
    res = client.get("/api/audit?action_type=custom_action_unique")
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["action_type"] == "custom_action_unique"

    # Filter by result
    res = client.get("/api/audit?result=denied_unique")
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["result"] == "denied_unique"

    # Test CSV export
    res = client.get("/api/audit?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "id,created_at,session_id,actor,action_type" in res.text
    assert "write_file_unique" in res.text
