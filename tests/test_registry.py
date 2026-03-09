"""Tests for ServiceRegistry."""

import pytest
from jjai_go2.core.registry import ServiceRegistry


def test_register_and_get():
    reg = ServiceRegistry()
    reg.register("foo", 42)
    assert reg.get("foo") == 42


def test_get_typed():
    reg = ServiceRegistry()
    reg.register("name", "hello")
    assert reg.get("name", str) == "hello"


def test_get_typed_wrong_type():
    reg = ServiceRegistry()
    reg.register("name", "hello")
    with pytest.raises(TypeError):
        reg.get("name", int)


def test_get_missing():
    reg = ServiceRegistry()
    with pytest.raises(KeyError):
        reg.get("missing")


def test_has():
    reg = ServiceRegistry()
    reg.register("x", 1)
    assert reg.has("x")
    assert not reg.has("y")


def test_names():
    reg = ServiceRegistry()
    reg.register("a", 1)
    reg.register("b", 2)
    assert sorted(reg.names) == ["a", "b"]


def test_overwrite():
    reg = ServiceRegistry()
    reg.register("x", 1)
    reg.register("x", 2)
    assert reg.get("x") == 2
