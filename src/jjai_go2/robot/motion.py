"""High-level motion commands — timed moves, distance-based travel.

Translates human-friendly commands (move forward 1 meter) into
velocity commands with timing.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .client import Go2Robot

logger = logging.getLogger(__name__)

# Default speeds (m/s and rad/s)
DEFAULT_WALK_SPEED = 0.3  # Conservative walk
DEFAULT_TROT_SPEED = 0.8  # Medium speed trot
DEFAULT_ROTATION_SPEED = 0.8  # rad/s


async def move_forward(robot: Go2Robot, distance: float = 0.5, speed: float = DEFAULT_WALK_SPEED) -> dict:
    """Move forward by estimated distance."""
    duration = abs(distance / speed)
    await robot.move(vx=speed, vy=0, vyaw=0)
    await asyncio.sleep(duration)
    await robot.stop_move()
    return {"distance": distance, "duration": round(duration, 2), "speed": speed}


async def move_backward(robot: Go2Robot, distance: float = 0.5, speed: float = DEFAULT_WALK_SPEED) -> dict:
    """Move backward by estimated distance."""
    duration = abs(distance / speed)
    await robot.move(vx=-speed, vy=0, vyaw=0)
    await asyncio.sleep(duration)
    await robot.stop_move()
    return {"distance": distance, "duration": round(duration, 2), "speed": speed}


async def move_left(robot: Go2Robot, distance: float = 0.3, speed: float = DEFAULT_WALK_SPEED) -> dict:
    """Strafe left. Go2 supports lateral movement."""
    duration = abs(distance / speed)
    await robot.move(vx=0, vy=speed, vyaw=0)
    await asyncio.sleep(duration)
    await robot.stop_move()
    return {"distance": distance, "duration": round(duration, 2)}


async def move_right(robot: Go2Robot, distance: float = 0.3, speed: float = DEFAULT_WALK_SPEED) -> dict:
    """Strafe right."""
    duration = abs(distance / speed)
    await robot.move(vx=0, vy=-speed, vyaw=0)
    await asyncio.sleep(duration)
    await robot.stop_move()
    return {"distance": distance, "duration": round(duration, 2)}


async def rotate(robot: Go2Robot, angle_deg: float = 90, speed: float = DEFAULT_ROTATION_SPEED) -> dict:
    """Rotate in place. Positive = counter-clockwise (left), negative = clockwise (right)."""
    import math
    angle_rad = math.radians(angle_deg)
    duration = abs(angle_rad / speed)
    direction = 1 if angle_deg > 0 else -1
    await robot.move(vx=0, vy=0, vyaw=direction * speed)
    await asyncio.sleep(duration)
    await robot.stop_move()
    return {"angle_deg": angle_deg, "duration": round(duration, 2)}
