import pytest
from app.db.session_store import SessionStore

def test_audit_entries_filtering(tmp_path):
    store = SessionStore(tmp_path / "test.db")
    s1 = store.create_session("model1", True, "/tmp")
    s2 = store.create_session("model2", False, "/tmp")

    store.add_audit({
        "session_id": s1["id"],
        "actor": "user",
        "action_type": "file_write",
        "tool_name": "write_file",
        "target": "foo.py",
        "result": "approved",
        "timestamp": "2026-01-01T00:00:00Z"
    })
    store.add_audit({
        "session_id": s2["id"],
        "actor": "agent",
        "action_type": "file_read",
        "tool_name": "read_file",
        "target": "bar.py",
        "result": "denied",
        "timestamp": "2026-01-01T00:01:00Z"
    })

    # Filter by actor
    user_entries = store.audit_entries(actor="user")
    assert len(user_entries) == 1
    assert user_entries[0]["actor"] == "user"

    # Filter by action_type
    read_entries = store.audit_entries(action_type="file_read")
    assert len(read_entries) == 1
    assert read_entries[0]["action_type"] == "file_read"

    # Filter by result
    denied_entries = store.audit_entries(result="denied")
    assert len(denied_entries) == 1
    assert denied_entries[0]["result"] == "denied"

    # Combined filter
    empty_entries = store.audit_entries(actor="user", result="denied")
    assert len(empty_entries) == 0
