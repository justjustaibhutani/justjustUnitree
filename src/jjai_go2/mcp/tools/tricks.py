"""Trick tools — dance, flip, hello, stretch, etc. Go2-specific."""

from __future__ import annotations

from ..registry import Tool, ToolRegistry
from ...robot.client import Go2Robot
from ...robot import tricks


def register_trick_tools(registry: ToolRegistry, robot: Go2Robot) -> None:
    """Register all trick MCP tools."""

    registry.register(Tool(
        name="dance",
        description="Perform a dance routine. Style 1 (default) or 2.",
        parameters={
            "type": "object",
            "properties": {
                "style": {"type": "integer", "description": "Dance style (1 or 2)", "default": 1},
            },
        },
        handler=lambda style=1: tricks.dance(robot, style),
        category="tricks",
    ))

    for name, desc, handler in [
        ("hello", "Wave a paw in greeting.", lambda: tricks.hello(robot)),
        ("stretch", "Full body stretch.", lambda: tricks.stretch(robot)),
        ("wiggle_hips", "Wiggle hips playfully.", lambda: tricks.wiggle_hips(robot)),
        ("shake_hand", "Offer a paw to shake.", lambda: tricks.shake_hand(robot)),
        ("front_flip", "Front flip. Requires open space!", lambda: tricks.front_flip(robot)),
        ("back_flip", "Back flip.", lambda: tricks.back_flip(robot)),
        ("walk_upright", "Walk on hind legs.", lambda: tricks.walk_upright(robot)),
        ("cross_step", "Fancy cross-step walk.", lambda: tricks.cross_step(robot)),
        ("climb_stairs", "Enable stair climbing mode.", lambda: tricks.climb_stairs(robot)),
    ]:
        registry.register(Tool(
            name=name,
            description=desc,
            parameters={"type": "object", "properties": {}},
            handler=handler,
            category="tricks",
        ))
