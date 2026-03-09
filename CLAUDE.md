# justjustUnitree — Unitree Go2 EDU Plus (U2) Robot Platform

> **Quick Start**: `python -m jjai_go2` or `python -m jjai_go2 --dashboard-only` for UI without robot.
>
> **Robot**: Unitree Go2 EDU Plus (U2) — Jetson Orin NX 100 TOPS, 4D LiDAR L2, RealSense D435i
>
> **Architecture**: Pure Python, no ROS2. WebRTC-first via `go2_webrtc_connect`. AsyncIO structured concurrency.

---

## System Overview

JJAI Go2 platform for the Unitree Go2 EDU Plus robot dog. Voice-controlled via Azure OpenAI Realtime API with 33 MCP tools. Dashboard at `dashboard.justjust.ai/unitreego2`.

### Key Design Choices (SOTA)
- **WebRTC-first** (`go2_webrtc_connect`) — no CycloneDDS, no jailbreak, works over WiFi
- **FastAPI + HTMX** — async-native, SSE streaming, no React build step
- **OM1-inspired NLDB** — sensor data fused into natural language context for LLM
- **asyncio.TaskGroup** — Python 3.11+ structured concurrency (replaces ROS2 nodes)
- **In-process MCP tools** — no subprocess, direct execution in voice agent

### Live URLs
| Service | URL |
|---------|-----|
| Go2 Dashboard | https://dashboard.justjust.ai/unitreego2 |
| Coding Stats | https://coding.justjust.ai |

---

## Directory Structure

```
justjustUnitree/
├── CLAUDE.md                    # THIS FILE
├── pyproject.toml               # pip install -e .
├── requirements.txt
├── deploy.sh                    # rsync to Go2
├── unitree_keys.env.template    # API key template
│
├── src/jjai_go2/                # Main package
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m jjai_go2
│   ├── config.py                # YAML + env config loading
│   │
│   ├── core/
│   │   ├── event_bus.py         # Async typed pub/sub (replaces ROS2 topics)
│   │   ├── module.py            # Module lifecycle (start/stop/health)
│   │   ├── registry.py          # Service registry (DI)
│   │   └── types.py             # RobotState, Posture, VoiceEvent, CommandResult
│   │
│   ├── robot/
│   │   ├── client.py            # Go2Robot — go2_webrtc_connect wrapper
│   │   ├── motion.py            # Timed moves (forward, backward, strafe, rotate)
│   │   ├── posture.py           # Stand, sit, balance, recovery, lie down
│   │   ├── tricks.py            # Dance, flip, hello — cooldown-protected
│   │   ├── camera.py            # Frame capture, room scan, JPEG encoding
│   │   ├── audio.py             # Bidirectional PCM audio bridge
│   │   ├── lidar.py             # LiDAR point cloud container
│   │   └── sensors.py           # SensorMonitor module (polls state + system stats)
│   │
│   ├── voice/
│   │   ├── agent.py             # VoiceAgent — Azure Realtime WebSocket + MCP dispatch
│   │   └── context_fuser.py     # OM1-style sensor→text fusion + personality prompts
│   │
│   ├── mcp/
│   │   ├── registry.py          # Tool/ToolRegistry with OpenAI schema export
│   │   └── tools/
│   │       ├── movement.py      # 7 tools
│   │       ├── posture.py       # 5 tools
│   │       ├── tricks.py        # 10 tools
│   │       ├── camera.py        # 2 tools
│   │       ├── system.py        # 3 tools
│   │       └── __init__.py      # register_all_tools()
│   │
│   ├── dashboard/
│   │   ├── app.py               # FastAPI routes + SSE + WebSocket + MJPEG
│   │   └── templates/
│   │       └── unitreego2.html  # Dark-theme HTMX dashboard
│   │
│   └── watchdog.py              # Module health monitoring + auto-restart
│
├── config/
│   └── go2.yaml                 # Robot config (IP, thresholds)
│
├── scripts/
│   ├── install.sh               # First-time Go2 setup
│   └── test_connection.py       # Verify WebRTC works
│
└── tests/                       # 36 tests across 6 files
    ├── test_event_bus.py
    ├── test_registry.py
    ├── test_config.py
    ├── test_mcp_tools.py
    ├── test_context_fuser.py
    └── test_dashboard.py
```

---

## Running

### Development (Mac, no robot)
```bash
# Install
pip install -e ".[dev]"

# Dashboard only (no robot connection)
python -m jjai_go2 --dashboard-only --port 5003

# Run tests
PYTHONPATH=src pytest tests/ -v
```

### On Go2 (Jetson)
```bash
# First-time setup
bash scripts/install.sh

# Normal start
python -m jjai_go2 --config config/go2.yaml --env ~/unitree_keys.env

# With specific IP
python -m jjai_go2 --ip 192.168.12.1
```

### Deploy to Go2
```bash
bash deploy.sh
```

---

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/unitreego2` | Dashboard HTML page (HTMX) |
| GET | `/unitreego2/api/status` | Robot state JSON |
| POST | `/unitreego2/api/command` | Execute command `{command, args}` |
| GET | `/unitreego2/api/voice-log` | Voice transcript entries |
| GET | `/unitreego2/api/stream/status` | SSE robot status stream |
| GET | `/unitreego2/api/stream/voice` | SSE voice transcript stream |
| GET | `/unitreego2/api/camera` | MJPEG camera stream |
| WS | `/unitreego2/ws` | WebSocket for commands |

---

## MCP Tools (33 total)

### Movement (7)
`move_forward`, `move_backward`, `move_left`, `move_right`, `rotate`, `stop`, `get_status`

### Posture (5)
`stand_up`, `sit_down`, `balance_stand`, `recovery_stand`, `lie_down`

### Tricks (10)
`dance`, `hello`, `stretch`, `wiggle_hips`, `shake_hand`, `front_flip`, `back_flip`, `walk_upright`, `cross_step`, `climb_stairs`

### Camera (2)
`click_photo`, `scan_room`

### System (3)
`get_battery`, `toggle_obstacle_avoidance`, `get_system_stats`

---

## Core Architecture

### EventBus (replaces ROS2 topics)
```python
bus = EventBus()
sub = bus.subscribe("robot/state", max_queue=10)  # Drop-oldest on overflow
await bus.publish("robot/state", robot_state)
msg = await sub.get()
```

### Module Lifecycle (replaces ROS2 nodes)
```python
class MyModule(Module):
    @property
    def name(self) -> str: return "my_module"
    async def start(self, bus, registry): ...
    async def run(self): ...   # Main loop
    async def stop(self): ...
    async def health_check(self) -> HealthStatus: ...
```

### ServiceRegistry (dependency injection)
```python
registry = ServiceRegistry()
registry.register("robot", robot)
robot = registry.get("robot", Go2Robot)
```

### Context Fuser (OM1-inspired)
All sensor data → natural language paragraph → LLM system context:
```
"Robot: connected, battery 73% (OK), posture standing, CPU temp 45°C.
 You see Bhutani in the living room."
```

---

## Configuration

### Priority: env vars > YAML > defaults

| Setting | Env Var | YAML Key | Default |
|---------|---------|----------|---------|
| Robot ID | `ROBOT_ID` | `robot_id` | `go2` |
| Robot IP | `ROBOT_IP` | `robot_ip` | `192.168.12.1` |
| Connection | `CONNECTION_MODE` | `connection_mode` | `sta_l` |
| Dashboard Port | `DASHBOARD_PORT` | `dashboard_port` | `5003` |
| Azure API Key | `AZURE_API_KEY` | `azure_api_key` | - |
| Azure Endpoint | `AZURE_ENDPOINT` | `azure_endpoint` | - |
| Azure Deployment | `AZURE_REALTIME_DEPLOYMENT` | `azure_realtime_deployment` | `gpt-4o-realtime` |

---

## Go2 Connection Modes

| Mode | IP | Description |
|------|-----|-------------|
| `sta_l` | 192.168.12.1 | Go2 connects to your WiFi (default) |
| `ap` | 192.168.12.1 | Connect to Go2's own hotspot |

The robot client falls back to **mock mode** if `go2_webrtc_connect` is not installed — allows development/testing on Mac without a robot.

---

## Reference Repos

| Repo | Stars | Use |
|------|-------|-----|
| [go2_webrtc_connect](https://github.com/legion1581/go2_webrtc_connect) | 265 | Primary robot interface |
| [OM1](https://github.com/OpenMind/OM1) | 2.7K | NLDB architecture patterns |
| [DimOS](https://github.com/dimensionalOS/dimos-unitree) | - | Skill architecture, spatial memory |
| [unitree-go2-mcp-server](https://github.com/lpigeon/unitree-go2-mcp-server) | 75 | MCP tool structure |
| [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) | 606 | Official Python SDK |
| [autonomy_stack_go2](https://github.com/robomechanics/autonomy_stack_go2) | 386 | CMU SLAM + navigation |

---

## Personalities

### ToTo — Professional Assistant
- Deeper, calmer voice. Hospitality-focused. Action-first.
- Cartesia voice ID: `a167e0f3-df7e-4d52-a9c3-f949145f52b7`

### CoCo — Baby Robot
- Higher, faster voice. Doubled words ("happy happy!"). Cocomelon-inspired.
- Cartesia voice ID: `95d51f79-c397-46f9-b49a-23763d3eaa2d`

---

## Phase Roadmap

- **Phase 1 (current)**: Base framework + Dashboard + Voice + MCP tools
- **Phase 2**: Face recognition (InsightFace), navigation (SLAM + Nav2)
- **Phase 3**: Personality system, cloud logging (S3 + DynamoDB)
- **Phase 4**: iOS app, follow-me, photographer, patrol modes

---

## Agent Session Tracking

All AI coding agents MUST follow the JJAI session protocol. See parent `CLAUDE.md` at `~/Desktop/CLAUDE.md` for full API reference.

```bash
# Quick start
/agent-session <task description>

# Manual
curl -X POST https://coding.justjust.ai/api/sessions \
  -H "X-API-Key: jjai-agent-x4trbWAD6Os6VPgk4V4gihlcddgIhbtM-UpMQZlCnBM" \
  -d '{"repo_name": "justjustUnitree", ...}'
```
