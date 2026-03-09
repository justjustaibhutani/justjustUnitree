"""Watchdog — monitors module health, restarts on failure.

Inspired by brain's node_watchdog.py but operates on in-process
Module instances instead of pgrep-based process monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time

import psutil

from .core import EventBus, HealthStatus, Module, ServiceRegistry

logger = logging.getLogger(__name__)

MAX_RESTARTS = 10
RESTART_WINDOW = 300  # 5 minutes


class Watchdog(Module):
    """Monitors all modules, restarts unhealthy ones, logs system stats."""

    def __init__(self, modules: list[Module], bus: EventBus, registry: ServiceRegistry) -> None:
        self._modules = modules
        self._bus = bus
        self._registry = registry
        self._restart_counts: dict[str, list[float]] = {}  # name -> [timestamps]
        self._disabled: set[str] = set()
        self._interval = 5.0
        self._running = True

    @property
    def name(self) -> str:
        return "watchdog"

    async def start(self, bus: EventBus, registry: ServiceRegistry) -> None:
        pass  # Already initialized in __init__

    async def run(self) -> None:
        """Main watchdog loop — check health every 5 seconds."""
        logger.info("Watchdog started, monitoring %d modules", len(self._modules))

        while self._running:
            for module in self._modules:
                if module.name in self._disabled:
                    continue

                try:
                    status = await asyncio.wait_for(module.health_check(), timeout=3.0)
                except (asyncio.TimeoutError, Exception) as e:
                    status = HealthStatus.UNHEALTHY
                    logger.warning("Health check failed for %s: %s", module.name, e)

                if status == HealthStatus.UNHEALTHY:
                    await self._restart_module(module)

            # Log system stats
            await self._log_stats()
            await asyncio.sleep(self._interval)

    async def stop(self) -> None:
        self._running = False

    async def health_check(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    async def _restart_module(self, module: Module) -> None:
        """Restart a failed module with backoff logic."""
        name = module.name
        now = time.time()

        # Track restarts
        if name not in self._restart_counts:
            self._restart_counts[name] = []
        self._restart_counts[name].append(now)

        # Clean old entries
        self._restart_counts[name] = [
            t for t in self._restart_counts[name] if now - t < RESTART_WINDOW
        ]

        # Check if we've exceeded max restarts
        if len(self._restart_counts[name]) >= MAX_RESTARTS:
            logger.error(
                "Module %s exceeded %d restarts in %ds — DISABLED",
                name, MAX_RESTARTS, RESTART_WINDOW,
            )
            self._disabled.add(name)
            return

        logger.warning("Restarting module: %s (restart #%d)", name, len(self._restart_counts[name]))

        try:
            await module.stop()
        except Exception:
            pass

        try:
            await module.start(self._bus, self._registry)
        except Exception as e:
            logger.error("Failed to restart %s: %s", name, e)

    async def _log_stats(self) -> None:
        """Log system stats to event bus."""
        stats = {
            "cpu_percent": psutil.cpu_percent(),
            "ram_percent": psutil.virtual_memory().percent,
            "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 2),
            "disk_percent": psutil.disk_usage("/").percent,
            "timestamp": time.time(),
        }
        await self._bus.publish("system/stats", stats)
