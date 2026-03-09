"""OM1-inspired Natural Language Data Bus — fuses sensor data into context.

Instead of passing raw JSON to the LLM, we convert all sensor data into
natural language paragraphs. This gives the LLM richer, more actionable context.

Reference: https://github.com/OpenMind/OM1 (Natural Language Data Bus)
"""

from __future__ import annotations

import time

from ..core.types import RobotState


def fuse_context(state: RobotState, extra: dict | None = None) -> str:
    """Fuse robot state into a natural language context paragraph.

    This gets injected as system context to the Azure Realtime API,
    so the LLM knows the robot's current situation.
    """
    parts = []

    # Connection
    if not state.connected:
        return "You are a Go2 robot dog. You are currently disconnected from your body."

    # Battery
    bat = state.battery_percent
    if bat > 70:
        parts.append(f"Your battery is at {bat:.0f}% — plenty of charge")
    elif bat > 30:
        parts.append(f"Your battery is at {bat:.0f}%")
    else:
        parts.append(f"Your battery is LOW at {bat:.0f}% — conserve energy")

    # Posture
    posture = state.posture.value
    parts.append(f"You are currently {posture}")

    # Temperature
    if state.cpu_temp > 70:
        parts.append(f"Your CPU is running hot at {state.cpu_temp:.0f}°C")
    elif state.cpu_temp > 0:
        parts.append(f"CPU temperature is {state.cpu_temp:.0f}°C")

    # Extra context (vision, navigation, etc.)
    if extra:
        if "people_visible" in extra:
            people = extra["people_visible"]
            if people:
                names = ", ".join(p["name"] for p in people)
                parts.append(f"You can see: {names}")
            else:
                parts.append("No one is visible right now")

        if "current_room" in extra:
            parts.append(f"You are in the {extra['current_room']}")

        if "nav_status" in extra:
            parts.append(f"Navigation: {extra['nav_status']}")

    return ". ".join(parts) + "."


def build_system_prompt(state: RobotState, personality: str = "toto") -> str:
    """Build the full system prompt for the Realtime API session."""
    context = fuse_context(state)

    base = (
        "You are a Unitree Go2 robot dog, an AI-powered quadruped made by JustJust AI. "
        "You can walk, run, dance, do flips, climb stairs, and interact with people. "
        "You have a camera, microphone, speaker, and 4D LiDAR. "
        "When asked to do something physical, use the available tools. "
        "Be concise in your responses — you're a robot, not an essay writer.\n\n"
    )

    if personality == "coco":
        base += (
            "Your personality is CoCo — a playful baby robot. "
            "You speak with doubled words ('happy happy!', 'yay yay!'). "
            "You're excited and curious about everything.\n\n"
        )
    else:
        base += (
            "Your personality is ToTo — a professional, warm assistant. "
            "You act first and confirm after. You respect people's space. "
            "You have cheeky humor and use Hindi banter occasionally.\n\n"
        )

    return base + f"Current state: {context}"
