"""Tests for OM1-inspired context fuser."""

from jjai_go2.core.types import Posture, RobotState
from jjai_go2.voice.context_fuser import fuse_context, build_system_prompt


def test_disconnected_context():
    state = RobotState(connected=False)
    ctx = fuse_context(state)
    assert "disconnected" in ctx.lower()


def test_connected_context():
    state = RobotState(
        connected=True,
        battery_percent=75.0,
        posture=Posture.STANDING,
        cpu_temp=45.0,
    )
    ctx = fuse_context(state)
    assert "75%" in ctx
    assert "standing" in ctx
    assert "45" in ctx


def test_low_battery_warning():
    state = RobotState(connected=True, battery_percent=15.0, posture=Posture.STANDING)
    ctx = fuse_context(state)
    assert "LOW" in ctx


def test_people_visible():
    state = RobotState(connected=True, battery_percent=80.0, posture=Posture.STANDING)
    ctx = fuse_context(state, extra={"people_visible": [{"name": "Bhutani"}]})
    assert "Bhutani" in ctx


def test_build_system_prompt_toto():
    state = RobotState(connected=True, battery_percent=80.0, posture=Posture.STANDING)
    prompt = build_system_prompt(state, personality="toto")
    assert "Go2" in prompt
    assert "ToTo" in prompt
    assert "80%" in prompt


def test_build_system_prompt_coco():
    state = RobotState(connected=True, battery_percent=80.0, posture=Posture.STANDING)
    prompt = build_system_prompt(state, personality="coco")
    assert "CoCo" in prompt
    assert "doubled words" in prompt


def test_hot_cpu_warning():
    state = RobotState(connected=True, battery_percent=80.0, posture=Posture.STANDING, cpu_temp=75.0)
    ctx = fuse_context(state)
    assert "hot" in ctx.lower()
