from collections.abc import AsyncIterator

import pytest

from app.audit.logger import AuditLogger
from app.orchestrator import AgentOrchestrator
from app.safety.approval import ApprovalManager
from app.safety.rate_limiter import OllamaRateLimiter
from app.tools import ToolRegistry

class FakeOllama:
    def __init__(self): self.turn = 0
    async def health(self): return None
    async def chat(self, model: str, messages: list[dict], tools: list[dict]) -> AsyncIterator[dict]:
        self.turn += 1
        if self.turn == 1:
            yield {"type":"complete", "eval_count":1, "message":{"content":"I will find the requested file.", "tool_calls":[{"function":{"name":"keyword_search","arguments":{"query":"original"}}}]}}
        elif self.turn == 2:
            yield {"type":"complete", "eval_count":1, "message":{"content":"I will propose an edit.", "tool_calls":[{"function":{"name":"write_file","arguments":{"path":"fixture.txt","content":"changed\n"}}}]}}
        else:
            yield {"type":"complete", "eval_count":1, "message":{"content":"The requested change was denied; the file remains unchanged."}}

@pytest.mark.asyncio
async def test_agent_edit_is_denied_and_model_receives_result(settings, store):
    target = settings.workspace_root / "fixture.txt"; target.write_text("original\n")
    client = FakeOllama(); tools = ToolRegistry(settings); approvals = ApprovalManager(store)
    audit = AuditLogger(store, settings.audit_log_path)
    orchestrator = AgentOrchestrator(settings, store, client, tools, approvals, audit)
    session = store.create_session("fake", False, str(settings.workspace_root))
    events = []
    async for event in orchestrator.run(session["id"], "Change fixture"):
        events.append(event)
        if event["type"] == "approval_required":
            await approvals.resolve(event["approval_id"], False, "user")
    assert target.read_text() == "original\n"
    denied = [item for item in events if item["type"] == "tool_call_result"]
    assert denied[0]["name"] == "keyword_search"
    assert denied[1]["result"]["denied"] is True
    assert client.turn == 3
    assert any("denied" in message["content"] for message in store.messages(session["id"]) if message["role"] == "tool")


def test_parse_react_action_variations():
    # Direct JSON
    parsed = AgentOrchestrator._parse_react_action('{"action": "read_file", "arguments": {"path": "a.txt"}}')
    assert parsed == {"action": "read_file", "arguments": {"path": "a.txt"}}

    # Markdown code fence with json tag
    markdown_json = '```json\n{"action": "write_file", "arguments": {"path": "b.txt", "content": "hi"}}\n```'
    parsed_md = AgentOrchestrator._parse_react_action(markdown_json)
    assert parsed_md == {"action": "write_file", "arguments": {"path": "b.txt", "content": "hi"}}

    # Text preamble and markdown block
    preamble = 'Sure! Here is the action:\n```\n{"final": "Done writing files"}\n```'
    parsed_preamble = AgentOrchestrator._parse_react_action(preamble)
    assert parsed_preamble == {"final": "Done writing files"}

    # Plain text preamble with embedded JSON object
    text_embedded = 'I will execute this action: {"action": "list_files", "arguments": {"path": "."}}'
    parsed_embedded = AgentOrchestrator._parse_react_action(text_embedded)
    assert parsed_embedded == {"action": "list_files", "arguments": {"path": "."}}

    # Invalid input
    parsed_invalid = AgentOrchestrator._parse_react_action("I am not sending JSON here.")
    assert parsed_invalid == {"invalid": True}
