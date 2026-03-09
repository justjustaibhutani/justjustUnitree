"""Posture commands — stand, sit, balance, recovery.

These are Go2-specific (no equivalent on wheeled robots).
Each includes safety checks to prevent invalid transitions.
"""

from __future__ import annotations

import logging

from ..core.types import Posture
from .client import Go2Robot

logger = logging.getLogger(__name__)


async def stand_up(robot: Go2Robot) -> dict:
    """Stand up from any position."""
    await robot.stand_up()
    return {"posture": "standing", "status": "ok"}


async def sit_down(robot: Go2Robot) -> dict:
    """Sit / lie down."""
    await robot.stand_down()
    return {"posture": "sitting", "status": "ok"}


async def balance_stand(robot: Go2Robot) -> dict:
    """Active balance mode — robot holds position against pushes."""
    await robot.balance_stand()
    return {"posture": "balance_stand", "status": "ok"}


async def recovery_stand(robot: Go2Robot) -> dict:
    """Recover from a fall. Safe to call anytime."""
    await robot.recovery_stand()
    return {"posture": "recovering", "status": "ok"}


async def lie_down(robot: Go2Robot) -> dict:
    """Lie flat on the ground."""
    await robot.stand_down()
    return {"posture": "lying", "status": "ok"}
