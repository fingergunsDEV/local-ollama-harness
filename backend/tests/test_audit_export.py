import json
import csv
import io
import pytest
from app.db.session_store import SessionStore


def test_audit_export_json_and_csv(store: SessionStore):
    session = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root="/tmp/test")
    sid = session["id"]

    audit_rec = {
        "session_id": sid,
        "actor": "user",
        "action_type": "session_create",
        "tool_name": None,
        "target": "workspace",
        "result": "success",
        "timestamp": "2026-10-21T12:00:00Z"
    }
    store.add_audit(audit_rec)

    # Test JSON Export
    json_str = store.export_audit_log(session_id=sid, format_type="json")
    data = json.loads(json_str)
    assert "audit_entries" in data
    assert len(data["audit_entries"]) >= 1
    assert data["audit_entries"][0]["session_id"] == sid

    # Test CSV Export
    csv_str = store.export_audit_log(session_id=sid, format_type="csv")
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) >= 2  # Header + row
    assert rows[0] == ["id", "created_at", "session_id", "actor", "action_type", "tool_name", "target", "result"]
    assert rows[1][2] == sid
    assert rows[1][3] == "user"
    assert rows[1][4] == "session_create"


def test_audit_filtering_query(store: SessionStore):
    rec1 = {"session_id": "s1", "actor": "user", "action_type": "file_read", "tool_name": "read", "target": "main.py", "result": "success", "timestamp": "2026-10-21T12:00:00Z"}
    rec2 = {"session_id": "s1", "actor": "agent", "action_type": "exec_command", "tool_name": "exec", "target": "pytest", "result": "error", "timestamp": "2026-10-21T12:01:00Z"}
    store.add_audit(rec1)
    store.add_audit(rec2)

    entries = store.audit_entries(query="main.py")
    assert len(entries) == 1
    assert entries[0]["target"] == "main.py"

    entries_error = store.audit_entries(query="error")
    assert len(entries_error) == 1
    assert entries_error[0]["result"] == "error"
