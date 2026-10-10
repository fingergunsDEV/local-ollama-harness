from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


class ApprovalStore(Protocol):
    def create_approval(self, session_id: str, tool_call_id: str, action_type: str, diff_or_plan: str) -> str: ...
    def resolve_approval(self, approval_id: str, status: str, resolved_by: str) -> None: ...
    def approval_status(self, approval_id: str) -> str: ...


@dataclass
class ApprovalDecision:
    approval_id: str
    approved: bool
    remember_for_session: bool = False


class ApprovalManager:
    """Coordinates durable SQLite approval records with in-memory waiters for live runs."""

    def __init__(self, store: ApprovalStore) -> None:
        self.store = store
        self._events: dict[str, asyncio.Event] = {}
        self._remembered: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    def is_auto_approved(self, session_id: str, action_type: str) -> bool:
        return action_type in self._remembered.get(session_id, set())

    async def request(self, session_id: str, tool_call_id: str, action_type: str, plan: str) -> str:
        approval_id = self.store.create_approval(session_id, tool_call_id, action_type, plan)
        async with self._lock:
            self._events[approval_id] = asyncio.Event()
        return approval_id

    async def wait(self, approval_id: str, timeout: float) -> ApprovalDecision:
        async with self._lock:
            event = self._events.setdefault(approval_id, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            return ApprovalDecision(approval_id, False)
        status = self.store.approval_status(approval_id)
        return ApprovalDecision(approval_id, status == "approved")

    async def resolve(self, approval_id: str, approved: bool, resolved_by: str, remember: bool = False, session_id: str | None = None, action_type: str | None = None) -> None:
        self.store.resolve_approval(approval_id, "approved" if approved else "denied", resolved_by)
        if approved and remember and session_id and action_type:
            self._remembered.setdefault(session_id, set()).add(action_type)
        async with self._lock:
            self._events.setdefault(approval_id, asyncio.Event()).set()
