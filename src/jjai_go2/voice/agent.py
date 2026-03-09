"""Voice agent — Azure OpenAI Realtime API with MCP tool dispatch.

Architecture:
    Go2 Mic (WebRTC) → PCM → Azure Realtime WebSocket → response
                                        ↓
                                  MCP Tool Call
                                        ↓
                                 Go2Robot.method()
                                        ↓
                              CycloneDDS → Go2 Motors

The Realtime API handles STT + LLM + TTS in a single WebSocket connection.
Tool calls are dispatched to the MCP ToolRegistry (in-process, no subprocess).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

from ..core import EventBus, HealthStatus, Module, ServiceRegistry
from ..core.types import VoiceEvent
from ..mcp.registry import ToolRegistry
from ..robot.client import Go2Robot
from .context_fuser import build_system_prompt

logger = logging.getLogger(__name__)


class VoiceAgent(Module):
    """Always-on voice agent using Azure OpenAI Realtime API."""

    @property
    def name(self) -> str:
        return "voice"

    async def start(self, bus: EventBus, registry: ServiceRegistry) -> None:
        self._bus = bus
        self._robot = registry.get("go2_robot", Go2Robot)
        self._tools = registry.get("tool_registry", ToolRegistry)
        self._config = registry.get("config")
        self._ws = None
        self._running = True
        self._healthy = True

    async def run(self) -> None:
        """Main voice loop — connect and process events."""
        while self._running:
            try:
                await self._connect_and_run()
            except Exception as e:
                logger.error("Voice agent error: %s", e)
                self._healthy = False
                await asyncio.sleep(5)  # Retry after 5s

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    async def health_check(self) -> HealthStatus:
        if not self._config.azure_api_key:
            return HealthStatus.STOPPED  # No API key configured
        return HealthStatus.HEALTHY if self._healthy else HealthStatus.UNHEALTHY

    async def _connect_and_run(self) -> None:
        """Connect to Azure Realtime API and process events."""
        import websockets

        api_key = self._config.azure_api_key
        endpoint = self._config.azure_endpoint
        deployment = self._config.azure_realtime_deployment

        if not api_key:
            logger.info("No Azure API key — voice agent disabled")
            self._running = False
            return

        url = (
            f"wss://{endpoint}/openai/realtime"
            f"?api-version=2024-10-01-preview"
            f"&deployment={deployment}"
        )

        headers = {"api-key": api_key}

        logger.info("Connecting to Azure Realtime API...")

        async with websockets.connect(url, additional_headers=headers) as ws:
            self._ws = ws
            self._healthy = True
            logger.info("Connected to Azure Realtime API")

            # Configure session
            await self._configure_session(ws)

            # Process events
            async for message in ws:
                if not self._running:
                    break
                await self._handle_event(ws, json.loads(message))

    async def _configure_session(self, ws) -> None:
        """Send session configuration — tools, instructions, voice settings."""
        state = self._robot.get_state()
        system_prompt = build_system_prompt(state)

        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 800,
                },
                "tools": self._tools.schemas(),
            },
        }

        await ws.send(json.dumps(session_config))
        logger.info("Session configured with %d tools", self._tools.count)

    async def _handle_event(self, ws, event: dict) -> None:
        """Handle an event from the Realtime API."""
        event_type = event.get("type", "")

        if event_type == "response.audio_transcript.done":
            # Bot finished speaking — log transcript
            text = event.get("transcript", "")
            if text:
                await self._bus.publish("voice/transcript", VoiceEvent(
                    text=text, role="assistant"
                ))

        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcribed
            text = event.get("transcript", "")
            if text:
                await self._bus.publish("voice/transcript", VoiceEvent(
                    text=text, role="user"
                ))

        elif event_type == "response.function_call_arguments.done":
            # Tool call from LLM
            call_id = event.get("call_id", "")
            tool_name = event.get("name", "")
            args_str = event.get("arguments", "{}")

            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}

            logger.info("Tool call: %s(%s)", tool_name, args)

            # Publish to voice log
            await self._bus.publish("voice/transcript", VoiceEvent(
                text=f"{tool_name}({json.dumps(args)})",
                role="assistant",
                tool_call=tool_name,
            ))

            # Execute tool
            t0 = time.time()
            result = await self._tools.execute(tool_name, args)
            duration_ms = (time.time() - t0) * 1000
            logger.info("Tool %s completed in %.0fms: %s", tool_name, duration_ms, result)

            # Send result back to Realtime API
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result),
                },
            }))

            # Trigger response generation
            await ws.send(json.dumps({"type": "response.create"}))

        elif event_type == "error":
            error = event.get("error", {})
            logger.error("Realtime API error: %s", error.get("message", "unknown"))

        elif event_type == "session.created":
            logger.info("Realtime session created: %s", event.get("session", {}).get("id", ""))
