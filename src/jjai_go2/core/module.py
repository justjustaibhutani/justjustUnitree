"""Module lifecycle protocol — every subsystem implements this.

Replaces ROS2 Node with a simpler async-native interface.
Watchdog calls health_check() to monitor, stop()+start() to restart.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .registry import ServiceRegistry


class HealthStatus(enum.Enum):
    """Module health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Working but not optimal
    UNHEALTHY = "unhealthy"  # Needs restart
    STOPPED = "stopped"


class Module(ABC):
    """Base class for all JJAI Go2 subsystem modules.

    Lifecycle:
        init → start(bus, registry) → run() → stop()
                                        ↑
                            watchdog restarts if unhealthy
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique module name for logging and watchdog."""

    @abstractmethod
    async def start(self, bus: EventBus, registry: ServiceRegistry) -> None:
        """Initialize the module. Called once at boot, or on restart."""

    @abstractmethod
    async def run(self) -> None:
        """Main loop. Runs as an asyncio task. Should loop forever."""

    @abstractmethod
    async def stop(self) -> None:
        """Graceful shutdown. Release resources."""

    async def health_check(self) -> HealthStatus:
        """Return current health. Override for custom checks."""
        return HealthStatus.HEALTHY
