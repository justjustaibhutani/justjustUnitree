"""Async typed pub/sub — replaces ROS2 topics.

Channels are string-named, data is Any. Subscribers get an asyncio.Queue
with configurable max size (drop-oldest on overflow, like ROS2 QoS depth).

Usage:
    bus = EventBus()
    q = bus.subscribe("robot/state", maxsize=1)  # latest-only
    await bus.publish("robot/state", RobotState(...))
    state = await q.get()
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Async pub/sub with drop-oldest overflow (like ROS2 QoS KEEP_LAST)."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._stats: dict[str, int] = defaultdict(int)

    async def publish(self, channel: str, data: Any) -> None:
        """Publish data to all subscribers of a channel. Non-blocking."""
        self._stats[channel] += 1
        for queue in self._subscribers[channel]:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                # Drop oldest, keep latest (like ROS2 depth=1)
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass

    def subscribe(self, channel: str, maxsize: int = 10) -> asyncio.Queue:
        """Subscribe to a channel. Returns a Queue to await on."""
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers[channel].append(q)
        logger.debug("Subscribed to %s (maxsize=%d)", channel, maxsize)
        return q

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        """Remove a subscription."""
        subs = self._subscribers.get(channel, [])
        if queue in subs:
            subs.remove(queue)

    @property
    def channels(self) -> list[str]:
        """All channels with at least one subscriber."""
        return [ch for ch, subs in self._subscribers.items() if subs]

    def stats(self) -> dict[str, int]:
        """Message count per channel since creation."""
        return dict(self._stats)
