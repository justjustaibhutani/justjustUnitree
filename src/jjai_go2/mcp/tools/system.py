"""System tools — battery, status, obstacle avoidance, restart."""

from __future__ import annotations

import psutil

from ..registry import Tool, ToolRegistry
from ...robot.client import Go2Robot


def register_system_tools(registry: ToolRegistry, robot: Go2Robot) -> None:
    """Register all system MCP tools."""

    registry.register(Tool(
        name="get_battery",
        description="Get current battery level percentage.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _get_battery(robot),
        category="system",
    ))

    registry.register(Tool(
        name="toggle_obstacle_avoidance",
        description="Enable or disable obstacle avoidance.",
        parameters={
            "type": "object",
            "properties": {
                "enable": {"type": "boolean", "description": "True to enable, False to disable", "default": True},
            },
        },
        handler=lambda enable=True: _toggle_obstacle(robot, enable),
        category="system",
    ))

    registry.register(Tool(
        name="get_system_stats",
        description="Get system resource usage: CPU, RAM, disk, temperature.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _get_system_stats(robot),
        category="system",
    ))


async def _get_battery(robot: Go2Robot) -> dict:
    state = robot.get_state()
    return {"battery_percent": round(state.battery_percent, 1)}


async def _toggle_obstacle(robot: Go2Robot, enable: bool) -> dict:
    if enable:
        await robot.enable_obstacle_avoidance()
    else:
        await robot.disable_obstacle_avoidance()
    return {"obstacle_avoidance": "enabled" if enable else "disabled"}


async def _get_system_stats(robot: Go2Robot) -> dict:
    state = robot.get_state()
    return {
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 1),
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "cpu_temp": round(state.cpu_temp, 1),
        "battery": round(state.battery_percent, 1),
    }
