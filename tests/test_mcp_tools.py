"""Tests for MCP tool registry."""

import pytest
from jjai_go2.mcp.registry import Tool, ToolRegistry


@pytest.mark.asyncio
async def test_register_and_execute():
    reg = ToolRegistry()

    async def greet(name: str = "world") -> dict:
        return {"greeting": f"hello {name}"}

    reg.register(Tool(
        name="greet",
        description="Say hello",
        parameters={"type": "object", "properties": {"name": {"type": "string"}}},
        handler=greet,
    ))

    result = await reg.execute("greet", {"name": "Go2"})
    assert result == {"greeting": "hello Go2"}


@pytest.mark.asyncio
async def test_unknown_tool():
    reg = ToolRegistry()
    result = await reg.execute("nonexistent", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_tool_error_handling():
    reg = ToolRegistry()

    async def failing_tool() -> dict:
        raise RuntimeError("boom")

    reg.register(Tool(
        name="fail",
        description="Always fails",
        parameters={"type": "object", "properties": {}},
        handler=failing_tool,
    ))

    result = await reg.execute("fail", {})
    assert "error" in result
    assert "boom" in result["error"]


def test_schemas():
    reg = ToolRegistry()
    reg.register(Tool(
        name="test",
        description="Test tool",
        parameters={"type": "object", "properties": {}},
        handler=lambda: None,
    ))

    schemas = reg.schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "test"
    assert schemas[0]["type"] == "function"


def test_count():
    reg = ToolRegistry()
    assert reg.count == 0

    reg.register(Tool(name="a", description="", parameters={}, handler=lambda: None))
    reg.register(Tool(name="b", description="", parameters={}, handler=lambda: None))
    assert reg.count == 2
