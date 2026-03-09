"""Posture tools — stand, sit, balance, recovery. Go2-specific."""

from __future__ import annotations

from ..registry import Tool, ToolRegistry
from ...robot.client import Go2Robot
from ...robot import posture


def register_posture_tools(registry: ToolRegistry, robot: Go2Robot) -> None:
    """Register all posture MCP tools."""

    for name, desc, handler in [
        ("stand_up", "Stand up from any position.", lambda: posture.stand_up(robot)),
        ("sit_down", "Sit or lie down.", lambda: posture.sit_down(robot)),
        ("balance_stand", "Active balance mode — holds position against pushes.", lambda: posture.balance_stand(robot)),
        ("recovery_stand", "Recover from a fall. Safe to call anytime.", lambda: posture.recovery_stand(robot)),
        ("lie_down", "Lie flat on the ground.", lambda: posture.lie_down(robot)),
    ]:
        registry.register(Tool(
            name=name,
            description=desc,
            parameters={"type": "object", "properties": {}},
            handler=handler,
            category="posture",
        ))
