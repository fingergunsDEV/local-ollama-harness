import pytest
from fastapi.testclient import TestClient

from app.audit.logger import AuditLogger
from app.main import app, Runtime


@pytest.fixture
def audit_logger(store, tmp_path):
    return AuditLogger(store, tmp_path / "audit.log")


def test_audit_filtering_and_csv_export_db(settings, store, audit_logger):
    session = store.create_session("llama3.1:8b", True, str(settings.workspace_root))
    session_id = session["id"]

    audit_logger.log(
        session_id=session_id,
        actor="user",
        action_type="session_create",
        tool_name=None,
        target="root",
        result="success",
        dry_run=True,
    )
    audit_logger.log(
        session_id=session_id,
        actor="agent",
        action_type="file_read",
        tool_name="read_file",
        target="README.md",
        result="success",
        dry_run=True,
    )
    audit_logger.log(
        session_id=session_id,
        actor="user",
        action_type="exec_command",
        tool_name="exec",
        target="rm -rf /",
        result="denied",
        dry_run=True,
    )

    # Test filtering by action_type
    entries_read = store.audit_entries(session_id=session_id, action_type="file_read")
    assert len(entries_read) == 1
    assert entries_read[0]["action_type"] == "file_read"

    # Test filtering by result
    entries_denied = store.audit_entries(session_id=session_id, result="denied")
    assert len(entries_denied) == 1
    assert entries_denied[0]["target"] == "rm -rf /"

    # Test CSV export
    csv_out = store.export_audit_csv(session_id=session_id, result="denied")
    assert "timestamp,session_id,actor,action_type,tool_name,target,result" in csv_out
    assert "rm -rf /" in csv_out


def test_audit_export_api(settings, store, audit_logger):
    session = store.create_session("llama3.1:8b", True, str(settings.workspace_root))
    session_id = session["id"]

    audit_logger.log(
        session_id=session_id,
        actor="user",
        action_type="session_create",
        tool_name=None,
        target=None,
        result="success",
        dry_run=True,
    )

    with TestClient(app) as client:
        runtime = Runtime(settings)
        runtime.store = store
        app.state.runtime = runtime

        # Test GET /api/audit filtering
        res_audit = client.get(f"/api/audit?session_id={session_id}&action_type=session_create")
        assert res_audit.status_code == 200
        entries = res_audit.json()["entries"]
        assert len(entries) >= 1

        # Test GET /api/audit/export CSV
        res_csv = client.get(f"/api/audit/export?format=csv&session_id={session_id}")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "session_create" in res_csv.text

        # Test GET /api/audit/export JSON
        res_json = client.get(f"/api/audit/export?format=json&session_id={session_id}")
        assert res_json.status_code == 200
        assert "entries" in res_json.json()
