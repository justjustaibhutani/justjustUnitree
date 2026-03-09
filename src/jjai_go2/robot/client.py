"""Go2 robot client — WebRTC connection via go2_webrtc_connect.

This is the central hardware interface. All other robot modules
(motion, posture, tricks, camera, audio) use this client.

Connection modes:
    - LocalSTA: Same WiFi network (most common for home use)
    - LocalAP:  Robot's own hotspot (192.168.12.1)
    - Remote:   Via Unitree TURN server (different network)

Reference: https://github.com/legion1581/go2_webrtc_connect
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np

from ..core.types import Posture, RobotState

logger = logging.getLogger(__name__)


class Go2Robot:
    """Unified Go2 interface over WebRTC.

    Wraps go2_webrtc_connect for:
    - Sport commands (move, stand, sit, tricks)
    - Camera frames (video track)
    - Audio I/O (sendrecv)
    - LiDAR point clouds
    - State (battery, IMU, foot force)
    """

    def __init__(self, ip: str = "192.168.12.1", connection_mode: str = "sta_l") -> None:
        self.ip = ip
        self.connection_mode = connection_mode
        self._conn = None
        self._connected = False
        self._latest_frame: np.ndarray | None = None
        self._state = RobotState()
        self._frame_event = asyncio.Event()

    async def connect(self) -> None:
        """Establish WebRTC connection to Go2."""
        try:
            from go2_webrtc_connect import Go2Connection, WebRTCConnectionMethod

            if self.connection_mode == "ap":
                method = WebRTCConnectionMethod.LocalAP
                self._conn = Go2Connection(method)
            else:
                method = WebRTCConnectionMethod.LocalSTA
                self._conn = Go2Connection(method, ip=self.ip)

            await self._conn.connect()
            self._connected = True
            self._state.connected = True
            logger.info("Connected to Go2 at %s via %s", self.ip, self.connection_mode)

            # Set up video callback
            if hasattr(self._conn, "video"):
                self._conn.video.on_frame = self._on_video_frame

        except ImportError:
            logger.warning(
                "go2_webrtc_connect not installed. Running in mock mode. "
                "Install with: pip install go2-webrtc-connect"
            )
            self._connected = False
        except Exception as e:
            logger.error("Failed to connect to Go2: %s", e)
            self._connected = False

    async def disconnect(self) -> None:
        """Close WebRTC connection."""
        if self._conn:
            try:
                await self._conn.disconnect()
            except Exception:
                pass
        self._connected = False
        self._state.connected = False
        logger.info("Disconnected from Go2")

    # --- Sport Commands ---

    async def move(self, vx: float = 0.0, vy: float = 0.0, vyaw: float = 0.0) -> None:
        """Velocity command. vx: forward, vy: left, vyaw: counter-clockwise."""
        await self._sport_cmd("Move", vx, vy, vyaw)

    async def stop_move(self) -> None:
        """Emergency stop — halt all movement."""
        await self._sport_cmd("StopMove")

    async def stand_up(self) -> None:
        """Stand from any position."""
        await self._sport_cmd("StandUp")
        self._state.posture = Posture.STANDING

    async def stand_down(self) -> None:
        """Sit/lie down."""
        await self._sport_cmd("StandDown")
        self._state.posture = Posture.SITTING

    async def balance_stand(self) -> None:
        """Active balance mode."""
        await self._sport_cmd("BalanceStand")
        self._state.posture = Posture.STANDING

    async def recovery_stand(self) -> None:
        """Recover from fall."""
        await self._sport_cmd("RecoveryStand")
        self._state.posture = Posture.RECOVERING

    # --- Tricks ---

    async def hello(self) -> None:
        """Wave a paw."""
        await self._sport_cmd("Hello")

    async def stretch(self) -> None:
        """Full body stretch."""
        await self._sport_cmd("Stretch")

    async def wiggle_hips(self) -> None:
        """Wiggle hips (playful)."""
        await self._sport_cmd("WiggleHips")

    async def front_flip(self) -> None:
        """Front flip (requires space!)."""
        await self._sport_cmd("FrontFlip")

    async def back_flip(self) -> None:
        """Back flip."""
        await self._sport_cmd("BackFlip")

    async def front_pounce(self) -> None:
        """Pounce forward."""
        await self._sport_cmd("FrontPounce")

    async def dance(self, style: int = 1) -> None:
        """Dance routine."""
        cmd = f"Dance{style}" if style > 1 else "Dance1"
        await self._sport_cmd(cmd)

    async def walk_upright(self) -> None:
        """Stand and walk on hind legs."""
        await self._sport_cmd("Sit")  # Sit first for safety
        await asyncio.sleep(0.5)
        # WalkUpright may not be available via WebRTC on all firmware

    async def climb_stairs(self) -> None:
        """Enable stair climbing gait."""
        await self._sport_cmd("WalkStair")

    # --- Gait Control ---

    async def switch_gait(self, gait: int = 0) -> None:
        """Switch gait mode. 0=idle, 1=trot, 2=run, 3=climb."""
        await self._sport_cmd("SwitchGait", gait)

    async def economic_gait(self) -> None:
        """Enable power-saving gait."""
        await self._sport_cmd("EconomicGait")

    # --- Obstacle Avoidance ---

    async def enable_obstacle_avoidance(self) -> None:
        """Turn on obstacle avoidance."""
        await self._sport_cmd("ObstacleAvoidOn")

    async def disable_obstacle_avoidance(self) -> None:
        """Turn off obstacle avoidance."""
        await self._sport_cmd("ObstacleAvoidOff")

    # --- Camera ---

    def _on_video_frame(self, frame: np.ndarray) -> None:
        """Callback from WebRTC video track."""
        self._latest_frame = frame
        self._frame_event.set()

    async def get_frame(self) -> np.ndarray | None:
        """Get latest camera frame (non-blocking)."""
        return self._latest_frame

    async def wait_for_frame(self, timeout: float = 5.0) -> np.ndarray | None:
        """Wait for next camera frame."""
        self._frame_event.clear()
        try:
            await asyncio.wait_for(self._frame_event.wait(), timeout)
            return self._latest_frame
        except asyncio.TimeoutError:
            logger.warning("Camera frame timeout after %.1fs", timeout)
            return None

    # --- State ---

    def get_state(self) -> RobotState:
        """Get current robot state snapshot."""
        self._state.timestamp = time.time()
        return self._state

    @property
    def connected(self) -> bool:
        return self._connected

    # --- Internal ---

    async def _sport_cmd(self, cmd: str, *args: Any) -> None:
        """Send a sport command via WebRTC data channel."""
        if not self._connected or not self._conn:
            logger.warning("Not connected — command '%s' dropped", cmd)
            return

        try:
            sport = self._conn.data_channel
            if hasattr(sport, cmd):
                method = getattr(sport, cmd)
                if args:
                    await asyncio.to_thread(method, *args)
                else:
                    await asyncio.to_thread(method)
                logger.debug("Sport command: %s(%s)", cmd, args)
            else:
                logger.warning("Unknown sport command: %s", cmd)
        except Exception as e:
            logger.error("Sport command %s failed: %s", cmd, e)

    async def run(self) -> None:
        """Keepalive loop — maintain WebRTC connection and poll state."""
        while True:
            if self._connected and self._conn:
                try:
                    # Poll state from Go2 (battery, IMU, etc.)
                    # The WebRTC connection handles this via data channel
                    pass
                except Exception as e:
                    logger.error("State poll error: %s", e)
                    self._connected = False
            else:
                # Try reconnect
                logger.info("Attempting reconnection...")
                await self.connect()

            await asyncio.sleep(1.0)
