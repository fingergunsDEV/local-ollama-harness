import pytest

def test_export_session_json_and_markdown(settings, store):
    session = store.create_session("llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    session_id = session["id"]

    msg_id = store.add_message(session_id, "user", "Hello, write a hello world script.")
    store.add_message(session_id, "assistant", "Sure, here is the script.")

    tool_call_id = store.start_tool_call(session_id, msg_id, "write_file", {"path": "hello.py", "content": "print('hello')"}, dry_run=True)
    store.finish_tool_call(tool_call_id, {"status": "proposed_diff"}, "finished")

    approval_id = store.create_approval(session_id, tool_call_id, "file_write", "diff content")

    exported_json = store.export_session(session_id, fmt="json")
    assert exported_json["session"]["id"] == session_id
    assert len(exported_json["messages"]) == 2
    assert len(exported_json["tool_calls"]) == 1
    assert len(exported_json["approvals"]) == 1

    exported_md = store.export_session(session_id, fmt="markdown")
    assert f"# Session Transcript: {session_id}" in exported_md
    assert "write_file" in exported_md
    assert "file_write" in exported_md
