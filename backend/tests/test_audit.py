from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient


def test_audit_export_endpoints(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))

    # Import app after environment variables are set
    from app.main import app

    with TestClient(app) as client:
        # Create a session to populate audit log
        res = client.post("/api/sessions", json={"model": "llama3.1:8b"})
        assert res.status_code == 200

        # Export audit as JSON
        res_json = client.get("/api/audit/export?format=json")
        assert res_json.status_code == 200
        data = res_json.json()
        assert "entries" in data
        assert len(data["entries"]) >= 1

        # Export audit as CSV
        res_csv = client.get("/api/audit/export?format=csv")
        assert res_csv.status_code == 200
        assert res_csv.headers["content-type"] == "text/csv; charset=utf-8"
        csv_text = res_csv.text
        assert "id,timestamp,session_id,actor,action_type" in csv_text
        assert "session_create" in csv_text
