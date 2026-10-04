from app.db.session_store import SessionStore


def test_session_export_json_and_markdown(store: SessionStore, settings):
    session = store.create_session("llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    session_id = session["id"]

    store.add_message(session_id, "user", "Create a file named hello.txt")
    msg_id = store.add_message(session_id, "assistant", "Sure, creating hello.txt")
    call_id = store.start_tool_call(session_id, msg_id, "create_file", {"path": "hello.txt", "content": "hi"}, dry_run=True)
    store.finish_tool_call(call_id, {"applied": False, "dry_run": True}, "success")
    store.add_audit({
        "session_id": session_id,
        "actor": "user",
        "action_type": "chat",
        "result": "success",
        "timestamp": "2026-01-01T00:00:00Z"
    })

    export_json = store.export_session_json(session_id)
    assert export_json["session"]["id"] == session_id
    assert len(export_json["messages"]) == 2
    assert len(export_json["tool_calls"]) == 1
    assert len(export_json["audit_log"]) == 1

    export_md = store.export_session_markdown(session_id)
    assert f"# Session Export: {session_id}" in export_md
    assert "Create a file named hello.txt" in export_md
    assert "`create_file`" in export_md
