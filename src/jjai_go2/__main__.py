"""Main entry point — boots all modules with asyncio.TaskGroup.

Usage:
    python -m jjai_go2
    python -m jjai_go2 --config config/go2.yaml
    python -m jjai_go2 --ip 192.168.1.100 --dashboard-only
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

import uvicorn

from .config import Config
from .core import EventBus, ServiceRegistry
from .dashboard.app import app as dashboard_app, init_dashboard
from .mcp.registry import ToolRegistry
from .mcp.tools.camera import register_camera_tools
from .mcp.tools.movement import register_movement_tools
from .mcp.tools.posture import register_posture_tools
from .mcp.tools.system import register_system_tools
from .mcp.tools.tricks import register_trick_tools
from .robot.client import Go2Robot
from .robot.sensors import SensorMonitor
from .voice.agent import VoiceAgent
from .watchdog import Watchdog

logger = logging.getLogger("jjai_go2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JJAI Go2 Robot OS")
    parser.add_argument("--config", default="config/go2.yaml", help="Config YAML path")
    parser.add_argument("--env", default=None, help="Env file path (e.g. ~/unitree_keys.env)")
    parser.add_argument("--ip", default=None, help="Go2 IP address (overrides config)")
    parser.add_argument("--dashboard-only", action="store_true", help="Run only the dashboard")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port (overrides config)")
    parser.add_argument("--log-level", default=None, help="Log level")
    return parser.parse_args()


async def boot(args: argparse.Namespace) -> None:
    """Boot all modules using structured concurrency."""

    # Load config
    config = Config.load(yaml_path=args.config, env_file=args.env)
    if args.ip:
        config.robot_ip = args.ip
    if args.port:
        config.dashboard_port = args.port
    if args.log_level:
        config.log_level = args.log_level

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("=== JJAI Go2 Robot OS v0.1.0 ===")
    logger.info("Robot ID: %s | IP: %s", config.robot_id, config.robot_ip)

    # Core infrastructure
    bus = EventBus()
    registry = ServiceRegistry()
    registry.register("config", config)
    registry.register("event_bus", bus)

    # Robot client
    robot = Go2Robot(ip=config.robot_ip, connection_mode=config.connection_mode)
    registry.register("go2_robot", robot)

    # MCP tools
    tool_registry = ToolRegistry()
    register_movement_tools(tool_registry, robot)
    register_posture_tools(tool_registry, robot)
    register_trick_tools(tool_registry, robot)
    register_camera_tools(tool_registry, robot)
    register_system_tools(tool_registry, robot)
    registry.register("tool_registry", tool_registry)
    logger.info("Registered %d MCP tools", tool_registry.count)

    # Dashboard
    init_dashboard(bus, registry)

    if args.dashboard_only:
        logger.info("Dashboard-only mode — skipping robot connection")
        config_uvicorn = uvicorn.Config(
            dashboard_app,
            host=config.dashboard_host,
            port=config.dashboard_port,
            log_level="info",
        )
        server = uvicorn.Server(config_uvicorn)
        await server.serve()
        return

    # Connect to Go2
    logger.info("Connecting to Go2 at %s...", config.robot_ip)
    await robot.connect()

    # Build module list
    sensors = SensorMonitor()
    voice = VoiceAgent()

    modules = [sensors, voice]
    for m in modules:
        await m.start(bus, registry)

    # Watchdog
    watchdog = Watchdog(modules, bus, registry)

    logger.info("All modules started. Dashboard at http://0.0.0.0:%d/unitreego2", config.dashboard_port)

    # Run everything concurrently
    async with asyncio.TaskGroup() as tg:
        # Robot WebRTC keepalive
        tg.create_task(robot.run())

        # Modules
        for m in modules:
            tg.create_task(m.run())

        # Watchdog
        tg.create_task(watchdog.run())

        # Dashboard (uvicorn)
        uvicorn_config = uvicorn.Config(
            dashboard_app,
            host=config.dashboard_host,
            port=config.dashboard_port,
            log_level="warning",
        )
        server = uvicorn.Server(uvicorn_config)
        tg.create_task(server.serve())


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Handle graceful shutdown
    loop = asyncio.new_event_loop()

    def shutdown_handler():
        logger.info("Shutting down...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        loop.run_until_complete(boot(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown complete")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
