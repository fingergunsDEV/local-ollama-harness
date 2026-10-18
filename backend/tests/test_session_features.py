import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app, Runtime


@pytest.mark.asyncio
async def test_session_export_markdown_and_json(settings, store):
    app.state.runtime = Runtime(settings)
    sess = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    m1_id = store.add_message(sess["id"], role="user", content="Hello world")
    m2_id = store.add_message(sess["id"], role="assistant", content="Hi there!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Markdown export
        resp_md = await client.get(f"/api/sessions/{sess['id']}/export?format=markdown")
        assert resp_md.status_code == 200
        assert resp_md.headers["content-type"].startswith("text/markdown")
        md_text = resp_md.text
        assert f"# Session Export: {sess['id']}" in md_text
        assert "Hello world" in md_text
        assert "Hi there!" in md_text

        # JSON export
        resp_json = await client.get(f"/api/sessions/{sess['id']}/export?format=json")
        assert resp_json.status_code == 200
        assert resp_json.headers["content-type"].startswith("application/json")
        data = resp_json.json()
        assert data["session"]["id"] == sess["id"]
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Hello world"


@pytest.mark.asyncio
async def test_session_fork(settings, store):
    app.state.runtime = Runtime(settings)
    sess = store.create_session(model="llama3.1:8b", dry_run=True, workspace_root=str(settings.workspace_root))
    m1_id = store.add_message(sess["id"], role="user", content="First message")
    m2_id = store.add_message(sess["id"], role="assistant", content="First response")
    m3_id = store.add_message(sess["id"], role="user", content="Second message")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Fork at m2_id
        resp_fork = await client.post(f"/api/sessions/{sess['id']}/fork", json={"message_id": m2_id})
        assert resp_fork.status_code == 200
        fork_data = resp_fork.json()
        new_sess_id = fork_data["session"]["id"]
        assert new_sess_id != sess["id"]
        assert fork_data["copied_messages"] == 2

        # Check messages of new session
        resp_get = await client.get(f"/api/sessions/{new_sess_id}")
        assert resp_get.status_code == 200
        msgs = resp_get.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["content"] == "First message"
        assert msgs[1]["content"] == "First response"

        # Invalid message ID
        resp_invalid = await client.post(f"/api/sessions/{sess['id']}/fork", json={"message_id": "non-existent"})
        assert resp_invalid.status_code == 400

        # Invalid session ID
        resp_bad_sess = await client.post("/api/sessions/non-existent-sess/fork", json={"message_id": m1_id})
        assert resp_bad_sess.status_code == 404
