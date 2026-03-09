"""Sensor data — battery, IMU, foot force, temperature.

Polls Go2 state and publishes to event bus.
"""

from __future__ import annotations

import asyncio
import logging
import time

import psutil

from ..core import EventBus, HealthStatus, Module, ServiceRegistry
from ..core.types import RobotState
from .client import Go2Robot

logger = logging.getLogger(__name__)


class SensorMonitor(Module):
    """Polls Go2 sensors and system stats, publishes to event bus."""

    @property
    def name(self) -> str:
        return "sensors"

    async def start(self, bus: EventBus, registry: ServiceRegistry) -> None:
        self._bus = bus
        self._robot = registry.get("go2_robot", Go2Robot)
        self._running = True

    async def run(self) -> None:
        while self._running:
            state = self._robot.get_state()

            # Enrich with system stats (runs on Jetson)
            state.cpu_temp = _get_cpu_temp()

            await self._bus.publish("robot/state", state)
            await asyncio.sleep(1.0)

    async def stop(self) -> None:
        self._running = False

    async def health_check(self) -> HealthStatus:
        if self._robot.connected:
            return HealthStatus.HEALTHY
        return HealthStatus.DEGRADED


def _get_cpu_temp() -> float:
    """Read CPU temperature. Works on Jetson and Linux."""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
    except Exception:
        pass
    # Fallback: try Jetson thermal zones
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return 0.0
