"""Bidirectional audio via WebRTC.

The Go2 has a built-in mic and speaker. WebRTC provides sendrecv audio.
This bridges Go2 audio ↔ Azure OpenAI Realtime API.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

logger = logging.getLogger(__name__)

# Audio format: 16-bit PCM, 16kHz, mono (Azure Realtime API format)
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


class AudioBridge:
    """Bridges Go2 WebRTC audio ↔ external consumers (voice agent).

    - Incoming: Go2 mic → buffer → voice agent reads
    - Outgoing: voice agent writes → buffer → Go2 speaker
    """

    def __init__(self, buffer_seconds: float = 30.0) -> None:
        max_samples = int(SAMPLE_RATE * buffer_seconds)
        self._input_buffer: deque[bytes] = deque(maxlen=max_samples)
        self._output_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._input_event = asyncio.Event()

    def on_audio_input(self, pcm_data: bytes) -> None:
        """Called by WebRTC when mic data arrives from Go2."""
        self._input_buffer.append(pcm_data)
        self._input_event.set()

    async def read_input(self, timeout: float = 1.0) -> bytes | None:
        """Read mic data. Returns None on timeout."""
        self._input_event.clear()
        try:
            await asyncio.wait_for(self._input_event.wait(), timeout)
            # Drain buffer
            chunks = list(self._input_buffer)
            self._input_buffer.clear()
            return b"".join(chunks)
        except asyncio.TimeoutError:
            return None

    async def write_output(self, pcm_data: bytes) -> None:
        """Queue audio to play on Go2 speaker."""
        try:
            self._output_queue.put_nowait(pcm_data)
        except asyncio.QueueFull:
            # Drop oldest
            try:
                self._output_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._output_queue.put_nowait(pcm_data)

    async def get_output(self) -> bytes:
        """Get next audio chunk to send to Go2 speaker."""
        return await self._output_queue.get()
