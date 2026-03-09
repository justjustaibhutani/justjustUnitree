"""Movement tools — walk, strafe, rotate, stop."""

from __future__ import annotations

from ..registry import Tool, ToolRegistry
from ...robot.client import Go2Robot
from ...robot import motion


def register_movement_tools(registry: ToolRegistry, robot: Go2Robot) -> None:
    """Register all movement MCP tools."""

    registry.register(Tool(
        name="move_forward",
        description="Move the robot forward by a specified distance in meters.",
        parameters={
            "type": "object",
            "properties": {
                "distance": {"type": "number", "description": "Distance in meters", "default": 0.5},
                "speed": {"type": "number", "description": "Speed in m/s (0.1-1.0)", "default": 0.3},
            },
        },
        handler=lambda distance=0.5, speed=0.3: motion.move_forward(robot, distance, speed),
        category="movement",
    ))

    registry.register(Tool(
        name="move_backward",
        description="Move the robot backward by a specified distance.",
        parameters={
            "type": "object",
            "properties": {
                "distance": {"type": "number", "default": 0.5},
                "speed": {"type": "number", "default": 0.3},
            },
        },
        handler=lambda distance=0.5, speed=0.3: motion.move_backward(robot, distance, speed),
        category="movement",
    ))

    registry.register(Tool(
        name="move_left",
        description="Strafe the robot left. The Go2 can move laterally.",
        parameters={
            "type": "object",
            "properties": {
                "distance": {"type": "number", "default": 0.3},
                "speed": {"type": "number", "default": 0.3},
            },
        },
        handler=lambda distance=0.3, speed=0.3: motion.move_left(robot, distance, speed),
        category="movement",
    ))

    registry.register(Tool(
        name="move_right",
        description="Strafe the robot right.",
        parameters={
            "type": "object",
            "properties": {
                "distance": {"type": "number", "default": 0.3},
                "speed": {"type": "number", "default": 0.3},
            },
        },
        handler=lambda distance=0.3, speed=0.3: motion.move_right(robot, distance, speed),
        category="movement",
    ))

    registry.register(Tool(
        name="rotate",
        description="Rotate the robot in place. Positive angle = left, negative = right.",
        parameters={
            "type": "object",
            "properties": {
                "angle_deg": {"type": "number", "description": "Angle in degrees. + is left, - is right.", "default": 90},
                "speed": {"type": "number", "description": "Rotation speed in rad/s", "default": 0.8},
            },
        },
        handler=lambda angle_deg=90, speed=0.8: motion.rotate(robot, angle_deg, speed),
        category="movement",
    ))

    registry.register(Tool(
        name="stop",
        description="Emergency stop. Immediately halt all movement.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _stop(robot),
        category="movement",
    ))

    registry.register(Tool(
        name="get_status",
        description="Get robot status: battery, posture, position, temperature.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _get_status(robot),
        category="movement",
    ))


async def _stop(robot: Go2Robot) -> dict:
    await robot.stop_move()
    return {"status": "stopped"}


async def _get_status(robot: Go2Robot) -> dict:
    state = robot.get_state()
    return {
        "battery": round(state.battery_percent, 1),
        "posture": state.posture.value,
        "position": {"x": state.position[0], "y": state.position[1], "yaw": state.position[2]},
        "cpu_temp": round(state.cpu_temp, 1),
        "connected": state.connected,
    }
