import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from app.main import app, Runtime
from app.indexing.embeddings import LocalEmbeddingProvider


@pytest.mark.asyncio
async def test_audit_filtering_and_export(settings, store):
    app.state.runtime = Runtime(settings)
    store.add_audit({"session_id": "s1", "actor": "user", "action_type": "session_create", "tool_name": None, "target": None, "result": "success", "timestamp": "2026-01-01T00:00:00Z"})
    store.add_audit({"session_id": "s1", "actor": "agent", "action_type": "file_write", "tool_name": "write", "target": "test.txt", "result": "denied", "timestamp": "2026-01-01T00:01:00Z"})
    store.add_audit({"session_id": "s2", "actor": "user", "action_type": "dry_run_toggle", "tool_name": None, "target": None, "result": "success", "timestamp": "2026-01-01T00:02:00Z"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Filter by action_type
        res_act = await client.get("/api/audit?action_type=file_write")
        assert res_act.status_code == 200
        entries = res_act.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["action_type"] == "file_write"

        # Filter by result
        res_res = await client.get("/api/audit?result=denied")
        assert res_res.status_code == 200
        entries_res = res_res.json()["entries"]
        assert len(entries_res) == 1
        assert entries_res[0]["result"] == "denied"

        # Export JSON
        res_exp_json = await client.get("/api/audit/export?format=json")
        assert res_exp_json.status_code == 200
        assert res_exp_json.headers["content-type"].startswith("application/json")
        assert len(res_exp_json.json()["entries"]) >= 3

        # Export CSV
        res_exp_csv = await client.get("/api/audit/export?format=csv")
        assert res_exp_csv.status_code == 200
        assert res_exp_csv.headers["content-type"].startswith("text/csv")
        csv_text = res_exp_csv.text
        assert "id,created_at,session_id,actor,action_type,tool_name,target,result" in csv_text
        assert "file_write" in csv_text


@pytest.mark.asyncio
async def test_embed_file_endpoint(settings, sandbox, store):
    app.state.runtime = Runtime(settings)
    (settings.workspace_root / "sample.py").write_text("def hello():\n    return 'world'\n")

    mock_provider = AsyncMock(spec=LocalEmbeddingProvider)
    mock_provider.embed.side_effect = lambda input_data: [[0.1, 0.2, 0.3]] if isinstance(input_data, str) else [[0.1, 0.2, 0.3] for _ in input_data]

    with patch("app.main.LocalEmbeddingProvider", return_value=mock_provider):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/index/embed-file", json={"path": "sample.py", "model": "nomic-embed-text"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["path"] == "sample.py"
            assert data["chunks_indexed"] > 0
            assert data["model"] == "nomic-embed-text"
