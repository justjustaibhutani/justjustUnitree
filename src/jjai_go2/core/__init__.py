"""Core framework — event bus, module lifecycle, service registry."""

from .event_bus import EventBus
from .module import HealthStatus, Module
from .registry import ServiceRegistry

__all__ = ["EventBus", "Module", "HealthStatus", "ServiceRegistry"]
