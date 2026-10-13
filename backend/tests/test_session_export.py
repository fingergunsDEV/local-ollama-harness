import pytest
from fastapi.testclient import TestClient

from app.main import app, Runtime


def test_session_export_and_forking_db(settings, store):
    session = store.create_session("llama3.1:8b", True, str(settings.workspace_root))
    session_id = session["id"]

    m1 = store.add_message(session_id, "user", "Please check files.")
    m2 = store.add_message(session_id, "assistant", "I will run list_files.")

    tool_id = store.start_tool_call(session_id, m2, "list_files", {"path": "."}, True)
    store.finish_tool_call(tool_id, {"files": ["README.md"]}, "completed")

    # Test JSON export
    exported_json = store.export_session_json(session_id)
    assert exported_json is not None
    assert exported_json["session"]["id"] == session_id
    assert len(exported_json["messages"]) == 2
    assert len(exported_json["tool_calls"]) == 1

    # Test Markdown export
    exported_md = store.export_session_markdown(session_id)
    assert exported_md is not None
    assert f"# Session Transcript: {session_id}" in exported_md
    assert "Please check files." in exported_md
    assert "list_files" in exported_md

    # Test Fork session
    forked = store.fork_session(session_id, until_message_id=m1)
    assert forked is not None
    assert forked["id"] != session_id
    forked_messages = store.messages(forked["id"])
    assert len(forked_messages) == 1
    assert forked_messages[0]["content"] == "Please check files."


def test_session_export_and_forking_api(settings, store):
    session = store.create_session("llama3.1:8b", True, str(settings.workspace_root))
    session_id = session["id"]
    msg_id = store.add_message(session_id, "user", "Hello local agent.")

    with TestClient(app) as client:
        runtime = Runtime(settings)
        runtime.store = store
        app.state.runtime = runtime

        # Test Markdown export endpoint
        res_md = client.get(f"/api/sessions/{session_id}/export?format=markdown")
        assert res_md.status_code == 200
        assert "text/markdown" in res_md.headers["content-type"]
        assert "Hello local agent." in res_md.text

        # Test JSON export endpoint
        res_json = client.get(f"/api/sessions/{session_id}/export?format=json")
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["session"]["id"] == session_id
        assert len(data["messages"]) == 1

        # Test Fork session endpoint
        res_fork = client.post(f"/api/sessions/{session_id}/fork", json={"until_message_id": msg_id})
        assert res_fork.status_code == 200
        fork_data = res_fork.json()
        assert fork_data["id"] != session_id
        assert fork_data["model"] == "llama3.1:8b"
