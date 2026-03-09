"""Shared data types used across modules."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Posture(Enum):
    """Go2 body posture states."""
    UNKNOWN = "unknown"
    STANDING = "standing"
    SITTING = "sitting"
    LYING = "lying"
    WALKING = "walking"
    RUNNING = "running"
    RECOVERING = "recovering"


@dataclass
class RobotState:
    """Snapshot of Go2 state — published to 'robot/state' channel."""
    battery_percent: float = 0.0
    posture: Posture = Posture.UNKNOWN
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)  # x, y, yaw
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)  # vx, vy, vyaw
    imu_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)  # roll, pitch, yaw
    foot_force: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # FL, FR, RL, RR
    cpu_temp: float = 0.0
    connected: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class VoiceEvent:
    """Voice transcript event — published to 'voice/transcript' or 'voice/response'."""
    text: str
    role: str  # "user" or "assistant"
    tool_call: str | None = None  # MCP tool name if this triggered a tool
    timestamp: float = field(default_factory=time.time)


@dataclass
class CommandResult:
    """Result of an MCP tool execution."""
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
