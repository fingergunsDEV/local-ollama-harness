import json
import pytest
from app.db.session_store import SessionStore


def test_session_export_markdown_and_json(store: SessionStore):
    session = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root="/tmp/test")
    sid = session["id"]

    store.add_message(sid, "user", "Hello agent")
    store.add_message(sid, "assistant", "Hello! How can I help?")

    # Test Markdown Export
    md_content = store.export_session(sid, format_type="markdown")
    assert f"# Session Transcript: {sid}" in md_content
    assert "**Model:** llama3.1:8b" in md_content
    assert "### USER" in md_content
    assert "Hello agent" in md_content
    assert "### ASSISTANT" in md_content
    assert "Hello! How can I help?" in md_content

    # Test JSON Export
    json_str = store.export_session(sid, format_type="json")
    json_data = json.loads(json_str)
    assert json_data["session"]["id"] == sid
    assert len(json_data["messages"]) == 2
    assert json_data["messages"][0]["content"] == "Hello agent"


def test_session_export_nonexistent(store: SessionStore):
    with pytest.raises(ValueError, match="Session missing-id not found"):
        store.export_session("missing-id", format_type="markdown")
