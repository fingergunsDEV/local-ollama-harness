import pytest
from app.db.session_store import SessionStore

def test_session_export_json_and_markdown(tmp_path):
    store = SessionStore(tmp_path / "test.db")
    session = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root="/tmp/ws")
    m1 = store.add_message(session["id"], "user", "Hello agent")
    m2 = store.add_message(session["id"], "assistant", "Hello user")

    # Export JSON
    data_json = store.export_session(session["id"], format_type="json")
    assert data_json["session"]["id"] == session["id"]
    assert len(data_json["messages"]) == 2
    assert data_json["messages"][0]["content"] == "Hello agent"

    # Export Markdown
    data_md = store.export_session(session["id"], format_type="markdown")
    assert f"# Session Export: {session['id']}" in data_md
    assert "### USER" in data_md
    assert "Hello agent" in data_md
    assert "### ASSISTANT" in data_md
    assert "Hello user" in data_md

def test_session_fork(tmp_path):
    store = SessionStore(tmp_path / "test.db")
    session = store.create_session(model="llama3.1:8b", dry_run=False, workspace_root="/tmp/ws")
    m1 = store.add_message(session["id"], "user", "Msg 1")
    m2 = store.add_message(session["id"], "assistant", "Msg 2")
    m3 = store.add_message(session["id"], "user", "Msg 3")

    # Fork up to m2
    forked = store.fork_session(session["id"], from_message_id=m2)
    assert forked["id"] != session["id"]
    forked_messages = store.messages(forked["id"])
    assert len(forked_messages) == 2
    assert forked_messages[0]["content"] == "Msg 1"
    assert forked_messages[1]["content"] == "Msg 2"

    # Fork full
    forked_full = store.fork_session(session["id"])
    assert len(store.messages(forked_full["id"])) == 3
