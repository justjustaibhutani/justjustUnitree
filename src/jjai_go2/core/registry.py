"""Service registry — dependency injection for modules.

Modules register services during start(), other modules look them up.
Replaces ROS2's node-to-node topic discovery with explicit registration.

Usage:
    registry = ServiceRegistry()
    registry.register("go2_robot", robot_instance)
    robot = registry.get("go2_robot", Go2Robot)
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceRegistry:
    """Simple typed service locator."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service. Overwrites if already registered."""
        self._services[name] = service
        logger.debug("Registered service: %s (%s)", name, type(service).__name__)

    def get(self, name: str, expected_type: type[T] | None = None) -> T:
        """Get a service by name. Raises KeyError if not found."""
        service = self._services.get(name)
        if service is None:
            raise KeyError(f"Service not registered: {name}")
        if expected_type and not isinstance(service, expected_type):
            raise TypeError(
                f"Service {name} is {type(service).__name__}, expected {expected_type.__name__}"
            )
        return service

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    @property
    def names(self) -> list[str]:
        """All registered service names."""
        return list(self._services.keys())
