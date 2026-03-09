"""Camera tools — photo, scan room, video capture."""

from __future__ import annotations

from ..registry import Tool, ToolRegistry
from ...robot.client import Go2Robot
from ...robot import camera


def register_camera_tools(registry: ToolRegistry, robot: Go2Robot) -> None:
    """Register all camera MCP tools."""

    registry.register(Tool(
        name="click_photo",
        description="Capture a photo from the Go2's front camera.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _click_photo(robot),
        category="camera",
    ))

    registry.register(Tool(
        name="scan_room",
        description="Rotate 360 degrees and capture photos at multiple angles to survey the room.",
        parameters={
            "type": "object",
            "properties": {
                "num_angles": {"type": "integer", "description": "Number of angles to capture", "default": 6},
            },
        },
        handler=lambda num_angles=6: _scan_room(robot, num_angles),
        category="camera",
    ))


async def _click_photo(robot: Go2Robot) -> dict:
    frame, meta = await camera.capture_photo(robot)
    if frame is None:
        return {"error": "No camera frame available"}
    return {"status": "captured", **meta}


async def _scan_room(robot: Go2Robot, num_angles: int = 6) -> dict:
    captures = await camera.scan_room(robot, num_angles)
    return {
        "status": "completed",
        "captures": len(captures),
        "angles": [angle for _, angle in captures],
    }
