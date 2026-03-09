"""LiDAR data access via WebRTC.

The Go2 EDU Plus has a 4D LiDAR (L1 or L2) that provides
360-degree point clouds. go2_webrtc_connect includes a decoder.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class LidarData:
    """Container for a single LiDAR scan."""

    def __init__(self, points: np.ndarray, timestamp: float) -> None:
        self.points = points  # Nx3 (x, y, z) or Nx4 (x, y, z, intensity)
        self.timestamp = timestamp

    @property
    def num_points(self) -> int:
        return self.points.shape[0] if self.points is not None else 0

    def to_dict(self) -> dict:
        return {
            "num_points": self.num_points,
            "timestamp": self.timestamp,
        }
