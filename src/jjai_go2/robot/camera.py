"""Camera access via WebRTC video track.

The Go2's camera is fixed on the head (no pan/tilt servo).
To look around, rotate the robot body.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time

import numpy as np

from .client import Go2Robot

logger = logging.getLogger(__name__)


async def capture_photo(robot: Go2Robot) -> tuple[np.ndarray | None, dict]:
    """Capture a single photo from the Go2 camera.

    Returns (frame, metadata) where frame is a numpy BGR array.
    """
    frame = await robot.wait_for_frame(timeout=5.0)
    if frame is None:
        return None, {"error": "No camera frame available"}

    h, w = frame.shape[:2]
    return frame, {
        "width": w,
        "height": h,
        "timestamp": time.time(),
    }


async def scan_room(robot: Go2Robot, num_angles: int = 6) -> list[tuple[np.ndarray | None, float]]:
    """Rotate 360 degrees, capturing photos at intervals.

    Returns list of (frame, angle_deg) tuples.
    Since Go2 has no pan/tilt, we physically rotate the robot.
    """
    import math

    angle_per_step = 360.0 / num_angles
    captures = []

    for i in range(num_angles):
        # Capture at current angle
        frame = await robot.wait_for_frame(timeout=3.0)
        current_angle = i * angle_per_step
        captures.append((frame, current_angle))
        logger.info("Scan capture %d/%d at %.0f°", i + 1, num_angles, current_angle)

        if i < num_angles - 1:
            # Rotate to next position
            angle_rad = math.radians(angle_per_step)
            duration = angle_rad / 0.8  # rotation speed
            await robot.move(vx=0, vy=0, vyaw=0.8)
            await asyncio.sleep(duration)
            await robot.stop_move()
            await asyncio.sleep(0.5)  # Settle

    return captures


def frame_to_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    """Convert numpy frame to JPEG bytes."""
    try:
        import cv2
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()
    except ImportError:
        # Fallback without OpenCV
        logger.warning("OpenCV not available for JPEG encoding")
        return b""
