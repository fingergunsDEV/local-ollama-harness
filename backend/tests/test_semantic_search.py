import pytest
from app.config import Settings
from app.tools import TOOL_SCHEMAS, ToolRegistry


def test_semantic_search_tool_schema_and_registry(settings, store):
    registry = ToolRegistry(settings)

    # Verify tool schema is present in TOOL_SCHEMAS
    names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert "semantic_search" in names
    assert "semantic_search" in registry._handlers
