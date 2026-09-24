from app.orchestrator import AgentOrchestrator


def test_parse_react_action_standard():
    raw = '{"action": "read_file", "arguments": {"path": "README.md"}}'
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"action": "read_file", "arguments": {"path": "README.md"}}


def test_parse_react_action_final():
    raw = '{"final": "Task completed successfully."}'
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"final": "Task completed successfully."}


def test_parse_react_action_markdown_code_fence():
    raw = """```json
{"action": "write_file", "arguments": {"path": "test.txt", "content": "hello"}}
```"""
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"action": "write_file", "arguments": {"path": "test.txt", "content": "hello"}}


def test_parse_react_action_markdown_code_fence_no_tag():
    raw = """```
{"action": "delete_file", "arguments": {"path": "test.txt"}}
```"""
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"action": "delete_file", "arguments": {"path": "test.txt"}}


def test_parse_react_action_surrounding_text():
    raw = """Here is the JSON action to run:
{"action": "read_file", "arguments": {"path": "main.py"}}
Hope this helps!"""
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"action": "read_file", "arguments": {"path": "main.py"}}


def test_parse_react_action_invalid():
    raw = "I don't know what tool to run."
    result = AgentOrchestrator._parse_react_action(raw)
    assert result == {"invalid": True}
