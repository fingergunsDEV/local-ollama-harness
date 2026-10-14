import json
import pytest
from app.db.session_store import SessionStore


def test_session_export_and_fork(settings, store):
    session = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    session_id = session["id"]

    msg1_id = store.add_message(session_id, "user", "Hello agent")
    msg2_id = store.add_message(session_id, "assistant", "Hello! How can I help?")
    msg3_id = store.add_message(session_id, "user", "Write a python script")

    # Test export markdown
    md_export = store.export_session(session_id, format_type="markdown")
    assert f"# Session Export: {session_id}" in md_export
    assert "Hello agent" in md_export
    assert "Write a python script" in md_export

    # Test export JSON
    json_export = store.export_session(session_id, format_type="json")
    assert isinstance(json_export, dict)
    assert json_export["session"]["id"] == session_id
    assert len(json_export["messages"]) == 3

    # Test fork up to msg2
    forked = store.fork_session(session_id, up_to_message_id=msg2_id)
    forked_id = forked["id"]
    forked_msgs = store.messages(forked_id)

    assert forked_id != session_id
    assert len(forked_msgs) == 2
    assert forked_msgs[0]["content"] == "Hello agent"
    assert forked_msgs[1]["content"] == "Hello! How can I help?"


def test_advanced_audit_filtering(settings, store):
    session = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    session_id = session["id"]

    store.add_audit({
        "session_id": session_id,
        "actor": "user",
        "action_type": "file_write",
        "tool_name": "overwrite_file",
        "target": "test.txt",
        "result": "success",
        "timestamp": "2026-03-30T10:00:00Z",
    })
    store.add_audit({
        "session_id": session_id,
        "actor": "user",
        "action_type": "command_exec",
        "tool_name": "execute_command",
        "target": "ls",
        "result": "denied",
        "timestamp": "2026-03-30T11:00:00Z",
    })

    # Filter by action_type
    entries = store.audit_entries(session_id=session_id, action_type="file_write")
    assert len(entries) == 1
    assert entries[0]["tool_name"] == "overwrite_file"

    # Filter by result
    entries = store.audit_entries(session_id=session_id, result="denied")
    assert len(entries) == 1
    assert entries[0]["tool_name"] == "execute_command"

    # Filter by date range
    entries = store.audit_entries(date_from="2026-03-30T10:30:00Z")
    assert len(entries) == 1
    assert entries[0]["action_type"] == "command_exec"
