"""Configuration loader — env vars + YAML."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    """All runtime configuration for JJAI Go2."""

    # Robot
    robot_id: str = "go2"
    robot_ip: str = "192.168.12.1"  # Go2 default AP IP
    connection_mode: str = "sta_l"  # sta_l (local WiFi) | ap (robot hotspot)

    # Azure OpenAI Voice
    azure_api_key: str = ""
    azure_endpoint: str = "bhuta-mht8rp1z-eastus2.cognitiveservices.azure.com"
    azure_realtime_deployment: str = "gpt-realtime-2025-08-28"

    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 5003

    # Google (vision)
    google_api_key: str = ""

    # Internals
    log_level: str = "INFO"
    watchdog_interval: float = 5.0

    @classmethod
    def load(cls, yaml_path: str | None = None, env_file: str | None = None) -> Config:
        """Load config from YAML + env vars. Env vars override YAML."""
        data: dict = {}

        # Load YAML if provided
        if yaml_path and Path(yaml_path).exists():
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}

        # Load env file if provided
        if env_file and Path(env_file).exists():
            _load_env_file(env_file)

        # Build config — env vars override yaml
        return cls(
            robot_id=os.getenv("ROBOT_ID", data.get("robot_id", cls.robot_id)),
            robot_ip=os.getenv("ROBOT_IP", data.get("robot_ip", cls.robot_ip)),
            connection_mode=data.get("connection_mode", cls.connection_mode),
            azure_api_key=os.getenv("AZURE_API_KEY", ""),
            azure_endpoint=os.getenv("AZURE_ENDPOINT", cls.azure_endpoint),
            azure_realtime_deployment=os.getenv(
                "AZURE_REALTIME_DEPLOYMENT", cls.azure_realtime_deployment
            ),
            dashboard_host=data.get("dashboard_host", cls.dashboard_host),
            dashboard_port=int(os.getenv("DASHBOARD_PORT", data.get("dashboard_port", cls.dashboard_port))),
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", data.get("log_level", cls.log_level)),
            watchdog_interval=float(data.get("watchdog_interval", cls.watchdog_interval)),
        )


def _load_env_file(path: str) -> None:
    """Parse a shell-style env file and set os.environ."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Handle 'export KEY="VALUE"' or 'KEY=VALUE'
            line = line.removeprefix("export ")
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
