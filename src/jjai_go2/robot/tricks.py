"""Go2 tricks — dance, flip, hello, stretch, etc.

These are the fun quadruped-specific actions.
Each has a cooldown to prevent rapid repeated execution.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .client import Go2Robot

logger = logging.getLogger(__name__)

# Cooldowns prevent hammering tricks (seconds)
_last_trick: dict[str, float] = {}
TRICK_COOLDOWN = 3.0  # seconds between same trick


async def _with_cooldown(name: str, coro) -> dict:
    """Execute a trick with cooldown protection."""
    now = time.time()
    last = _last_trick.get(name, 0)
    if now - last < TRICK_COOLDOWN:
        remaining = TRICK_COOLDOWN - (now - last)
        return {"status": "cooldown", "retry_in": round(remaining, 1)}

    _last_trick[name] = now
    await coro
    return {"trick": name, "status": "ok"}


async def dance(robot: Go2Robot, style: int = 1) -> dict:
    """Dance routine. Style 1 or 2."""
    return await _with_cooldown("dance", robot.dance(style))


async def hello(robot: Go2Robot) -> dict:
    """Wave a paw in greeting."""
    return await _with_cooldown("hello", robot.hello())


async def stretch(robot: Go2Robot) -> dict:
    """Full body stretch."""
    return await _with_cooldown("stretch", robot.stretch())


async def wiggle_hips(robot: Go2Robot) -> dict:
    """Wiggle hips playfully."""
    return await _with_cooldown("wiggle_hips", robot.wiggle_hips())


async def shake_hand(robot: Go2Robot) -> dict:
    """Offer a paw to shake."""
    return await _with_cooldown("shake_hand", robot.hello())  # Same as hello for now


async def front_flip(robot: Go2Robot) -> dict:
    """Front flip. Requires open space!"""
    return await _with_cooldown("front_flip", robot.front_flip())


async def back_flip(robot: Go2Robot) -> dict:
    """Back flip."""
    return await _with_cooldown("back_flip", robot.back_flip())


async def walk_upright(robot: Go2Robot) -> dict:
    """Walk on hind legs."""
    return await _with_cooldown("walk_upright", robot.walk_upright())


async def cross_step(robot: Go2Robot) -> dict:
    """Fancy cross-step walk."""
    # Cross step via movement pattern
    await robot.move(vx=0.2, vy=0.1, vyaw=0.3)
    await asyncio.sleep(3)
    await robot.stop_move()
    return {"trick": "cross_step", "status": "ok"}


async def climb_stairs(robot: Go2Robot) -> dict:
    """Enable stair climbing mode."""
    await robot.climb_stairs()
    return {"trick": "climb_stairs", "status": "ok", "note": "Stair mode enabled. Send move commands to climb."}
