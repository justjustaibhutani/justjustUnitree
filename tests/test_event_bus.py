"""Tests for the EventBus — core pub/sub system."""

import asyncio
import pytest
from jjai_go2.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_subscribe():
    """Basic pub/sub works."""
    bus = EventBus()
    q = bus.subscribe("test/channel")

    await bus.publish("test/channel", {"msg": "hello"})

    data = await asyncio.wait_for(q.get(), timeout=1.0)
    assert data == {"msg": "hello"}


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """Multiple subscribers each get the message."""
    bus = EventBus()
    q1 = bus.subscribe("test/multi")
    q2 = bus.subscribe("test/multi")

    await bus.publish("test/multi", 42)

    assert await asyncio.wait_for(q1.get(), timeout=1.0) == 42
    assert await asyncio.wait_for(q2.get(), timeout=1.0) == 42


@pytest.mark.asyncio
async def test_drop_oldest_on_overflow():
    """Queue drops oldest when full (like ROS2 QoS KEEP_LAST)."""
    bus = EventBus()
    q = bus.subscribe("test/overflow", maxsize=2)

    await bus.publish("test/overflow", 1)
    await bus.publish("test/overflow", 2)
    await bus.publish("test/overflow", 3)  # Should drop 1

    first = await asyncio.wait_for(q.get(), timeout=1.0)
    assert first == 2  # Oldest (1) was dropped

    second = await asyncio.wait_for(q.get(), timeout=1.0)
    assert second == 3


@pytest.mark.asyncio
async def test_unsubscribe():
    """After unsubscribe, no more messages received."""
    bus = EventBus()
    q = bus.subscribe("test/unsub")
    bus.unsubscribe("test/unsub", q)

    await bus.publish("test/unsub", "should_not_receive")

    assert q.empty()


@pytest.mark.asyncio
async def test_channels():
    """Channels property lists active channels."""
    bus = EventBus()
    bus.subscribe("a/b")
    bus.subscribe("c/d")

    assert sorted(bus.channels) == ["a/b", "c/d"]


@pytest.mark.asyncio
async def test_stats():
    """Message count tracking."""
    bus = EventBus()
    bus.subscribe("stats/test")

    await bus.publish("stats/test", 1)
    await bus.publish("stats/test", 2)

    assert bus.stats()["stats/test"] == 2


@pytest.mark.asyncio
async def test_no_subscribers():
    """Publishing to channel with no subscribers is a no-op."""
    bus = EventBus()
    await bus.publish("nobody/listening", "data")
    # Should not raise
    assert bus.stats()["nobody/listening"] == 1
