import asyncio

import pytest

from app.safety.approval import ApprovalManager

@pytest.mark.asyncio
async def test_pending_approval_blocks_then_denies(store):
    session = store.create_session("fake", False, "/workspace")
    call = store.start_tool_call(session["id"], None, "write_file", {"path":"a.txt"}, False)
    manager = ApprovalManager(store)
    approval_id = await manager.request(session["id"], call, "write", "diff")
    waiter = asyncio.create_task(manager.wait(approval_id, 1))
    await asyncio.sleep(0)
    assert store.approval_status(approval_id) == "pending"
    await manager.resolve(approval_id, False, "user")
    decision = await waiter
    assert not decision.approved
    assert store.approval_status(approval_id) == "denied"

@pytest.mark.asyncio
async def test_remembered_action_is_scoped_to_session(store):
    one = store.create_session("fake", False, "/workspace"); two = store.create_session("fake", False, "/workspace")
    manager = ApprovalManager(store)
    approval_id = await manager.request(one["id"], "call", "write", "diff")
    await manager.resolve(approval_id, True, "user", remember=True, session_id=one["id"], action_type="write")
    assert manager.is_auto_approved(one["id"], "write")
    assert not manager.is_auto_approved(two["id"], "write")
