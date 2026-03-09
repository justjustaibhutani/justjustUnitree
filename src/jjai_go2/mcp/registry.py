"""MCP tool registry — auto-discovers tools from the tools/ package.

Each tool is a dict with:
    name: str           - Tool name (e.g. "move_forward")
    description: str    - What it does (shown to LLM)
    parameters: dict    - JSON Schema for arguments
    handler: callable   - Async function to execute
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Coroutine[Any, Any, dict]]


class Tool:
    """A registered MCP tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: ToolHandler,
        category: str = "general",
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.category = category

    def to_schema(self) -> dict:
        """Convert to OpenAI function-calling schema."""
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Central registry of all MCP tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s (%s)", tool.name, tool.category)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    async def execute(self, name: str, args: dict) -> dict:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}

        try:
            result = await tool.handler(**args)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return {"error": str(e)}

    @property
    def tools(self) -> list[Tool]:
        """All registered tools."""
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        """All tool schemas for LLM function calling."""
        return [t.to_schema() for t in self._tools.values()]

    @property
    def count(self) -> int:
        return len(self._tools)
