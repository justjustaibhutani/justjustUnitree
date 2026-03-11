# Unitree Go2 EDU Plus — Complete Setup Guide

> **For**: Engineers at JJAI setting up a new Go2 EDU Plus for development
> **Last Updated**: 2026-03-11
> **Time Required**: ~45 minutes
> **Prerequisites**: Mac with USB-C port, USB-C Ethernet adapter, USB WiFi adapter (TP-Link AC600 or BrosTrend AC1L with Realtek rtl8812au chipset)

---

## Table of Contents
1. [Hardware Overview](#1-hardware-overview)
2. [Phase 1: Ethernet Connection (One-Time Bootstrap)](#2-phase-1-ethernet-connection)
3. [Phase 2: WiFi Adapter Setup (Permanent Wireless)](#3-phase-2-wifi-adapter-setup)
4. [Phase 3: Python 3.11 + Code Deployment](#4-phase-3-python-311--code-deployment)
5. [Phase 4: Verification](#5-phase-4-verification)
6. [Daily Development Workflow](#6-daily-development-workflow)
7. [Network Architecture](#7-network-architecture)
8. [Troubleshooting](#8-troubleshooting)
9. [Reference](#9-reference)

---

## 1. Hardware Overview

### Go2 EDU Plus Internals
| Component | IP Address | Access |
|-----------|-----------|--------|
| Jetson Orin NX (16GB) | 192.168.123.18 (internal) + WiFi IP (home network) | SSH: unitree/123 |
| MCU / Head Unit | 192.168.123.161 | Port 80, 9991 only (no SSH) |
| Internal Gateway | 192.168.123.1 | Configured but unresponsive |

### Jetson Specs
- **OS**: Ubuntu 20.04.5 LTS (focal), aarch64
- **Kernel**: 5.10.104-tegra
- **JetPack**: R35.3.1
- **RAM**: 16GB
- **Disk**: 469GB NVMe
- **Python**: 3.8.10 (system), 3.11.9 (built from source)

### USB Port Warning
The Go2's **external USB ports** (on the body) do NOT connect to the Jetson. They connect to the head unit/MCU. To access the Jetson's USB:
- The Jetson's USB port is accessible near the **rear Ethernet RJ45 port**
- If that doesn't work, you may need to open the Go2's top panel

---

## 2. Phase 1: Ethernet Connection

This is a one-time bootstrap to get WiFi set up. After Phase 2, you won't need ethernet again.

### 2.1 Physical Setup
1. Plug USB-C Ethernet adapter into Mac
2. Plug Ethernet cable from adapter into Go2's rear RJ45 port
3. Power on Go2, wait ~2 minutes for full boot

### 2.2 Configure Mac Ethernet
```bash
# Find your ethernet interface (look for the non-WiFi active interface)
ifconfig | grep -B5 "status: active" | grep -E "^[a-z]|inet |status"
# Usually en5, en6, en7, or en9 (NOT en0, that's WiFi)

# Set static IP (replace en9 with your interface)
sudo ifconfig en9 192.168.123.99 netmask 255.255.255.0 up

# Verify
ping -c 2 192.168.123.18
```

### 2.3 SSH into Jetson
```bash
ssh unitree@192.168.123.18
# Password: 123
```

### 2.4 Add Your SSH Key (passwordless access)
```bash
# From Mac
cat ~/.ssh/id_ed25519.pub | ssh unitree@192.168.123.18 \
  "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
# Password: 123
```

### 2.5 Give Jetson Internet (via Mac bridge)
The Jetson has no WiFi yet and no internet. Bridge through your Mac:

```bash
# On Mac: enable IP forwarding
sudo sysctl -w net.inet.ip.forwarding=1

# On Mac: set up NAT (replace en0 with your WiFi interface)
echo "nat on en0 from 192.168.123.0/24 to any -> (en0)" | sudo pfctl -ef -

# On Jetson: route through Mac
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S bash -c "ip route replace default via 192.168.123.99 dev eth0 && echo nameserver 8.8.8.8 > /etc/resolv.conf"'

# Verify
ssh unitree@192.168.123.18 'ping -c 2 google.com'
```

---

## 3. Phase 2: WiFi Adapter Setup

### 3.1 Requirements
- **USB WiFi adapter** with Realtek rtl8812au/rtl8811au chipset
- Tested: TP-Link AC600 (Archer T2U), BrosTrend AC1L
- The adapter must be plugged into the **Jetson's USB port** (near the ethernet RJ45), NOT the Go2's external USB ports

### 3.2 Verify Adapter Detected
```bash
ssh unitree@192.168.123.18 'lsusb'
# Should show something like:
# Bus 001 Device 003: ID 2357:0120 TP-Link 802.11ac WLAN Adapter

# Check kernel detected it
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S dmesg | tail -5'
# Should show: New USB device found, idVendor=2357 ... Product: 802.11ac WLAN Adapter
```

### 3.3 Build and Install Driver
```bash
# Install build dependencies (Jetson must have internet via Phase 1)
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S apt-get install -y build-essential dkms git'

# Clone the driver
ssh unitree@192.168.123.18 'cd /tmp && git clone https://github.com/aircrack-ng/rtl8812au.git'

# Build (uses existing kernel headers at /usr/src/linux-headers-5.10.104-tegra-ubuntu20.04_aarch64/)
ssh -t unitree@192.168.123.18 'cd /tmp/rtl8812au && echo "123" | sudo -S make -j$(nproc)'

# Install
ssh -t unitree@192.168.123.18 'cd /tmp/rtl8812au && echo "123" | sudo -S make install && echo "123" | sudo -S modprobe 88XXau'

# Verify wlan0 appeared
ssh unitree@192.168.123.18 'ip link show | grep wlan'
# Should show: wlan0
```

### 3.4 Connect to WiFi
```bash
# Scan for networks
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S nmcli dev wifi list ifname wlan0'

# Connect (replace SSID and PASSWORD with your network)
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S nmcli dev wifi connect "justjustai" password "Build@magic7" ifname wlan0'

# Check assigned IP
ssh unitree@192.168.123.18 'ip addr show wlan0 | grep "inet "'
# Note this IP — e.g., 192.168.1.5
```

### 3.5 Make Persistent Across Reboots
```bash
# Driver auto-load
ssh -t unitree@192.168.123.18 'echo "123" | sudo -S bash -c "echo 88XXau >> /etc/modules"'

# WiFi auto-connect (already done by nmcli, verify)
ssh unitree@192.168.123.18 'nmcli con show "justjustai" | grep autoconnect'
# Should show: connection.autoconnect: yes
```

### 3.6 Update SSH Config on Mac
Add to `~/.ssh/config`:
```
Host unitreedog
    HostName 192.168.1.5    # WiFi IP from step 3.4
    User unitree
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

Host unitreedog-eth
    HostName 192.168.123.18  # Internal IP (ethernet only)
    User unitree
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
```

### 3.7 Test WiFi SSH (unplug ethernet!)
```bash
# Unplug ethernet cable
ssh unitreedog 'echo "WiFi SSH works! $(hostname -I)"'
```

---

## 4. Phase 3: Python 3.11 + Code Deployment

### 4.1 Build Python 3.11 from Source
The Jetson ships with Python 3.8. Our codebase requires 3.11+ (asyncio.TaskGroup). The `deadsnakes` PPA does NOT have arm64 packages, so we build from source.

```bash
# Install build dependencies
ssh -t unitreedog 'echo "123" | sudo -S apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev liblzma-dev'

# Download, configure, build, install (~10 min)
ssh unitreedog 'cd /tmp && wget -q https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz && tar xzf Python-3.11.9.tgz && cd Python-3.11.9 && ./configure --enable-optimizations --prefix=/usr/local && make -j$(nproc)'

ssh -t unitreedog 'echo "123" | sudo -S make -C /tmp/Python-3.11.9 altinstall'

# Verify
ssh unitreedog 'python3.11 --version'
# Python 3.11.9
```

### 4.2 Deploy justjustUnitree
```bash
# From Mac
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.pytest_cache' --exclude '*.egg-info' \
  ~/Desktop/Bhutani\ Development/justjustUnitree/ \
  unitreedog:/home/unitree/justjustUnitree/
```

### 4.3 Create Venv and Install Dependencies
```bash
ssh unitreedog 'cd /home/unitree/justjustUnitree && python3.11 -m venv venv && source venv/bin/activate && pip install --upgrade pip'

# Install core dependencies
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && pip install fastapi uvicorn[standard] jinja2 python-multipart websockets numpy pyyaml psutil httpx'

# Install Unitree SDK from source (PyPI doesn't have arm64 wheels)
ssh unitreedog 'cd /home/unitree && git clone https://github.com/unitreerobotics/unitree_sdk2_python.git && cd unitree_sdk2_python && source /home/unitree/justjustUnitree/venv/bin/activate && CYCLONEDDS_HOME=/home/unitree/cyclonedds_ws/install/cyclonedds pip install -e .'

# Install justjustUnitree in editable mode
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && pip install -e ".[dev]"'
```

---

## 5. Phase 4: Verification

### 5.1 Run Tests
```bash
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && PYTHONPATH=src pytest tests/ -v'
# Expected: 36 passed
```

### 5.2 Test DDS Connection (Read Robot State)
```bash
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && python3 -c "
import time
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

ChannelFactoryInitialize(0, \"eth0\")

got = False
def cb(msg):
    global got
    if not got:
        got = True
        print(f\"Position: x={msg.position[0]:.3f} y={msg.position[1]:.3f} z={msg.position[2]:.3f}\")
        print(f\"Mode: {msg.mode}, Height: {msg.body_height:.3f}\")

sub = ChannelSubscriber(\"rt/sportmodestate\", SportModeState_)
sub.Init(cb, 10)
for _ in range(50):
    if got: break
    time.sleep(0.1)
print(\"DDS OK\" if got else \"DDS FAILED\")
"'
```

### 5.3 Test Motor Control (Stand Up + Down)
**Ensure the robot has clear space around it!**
```bash
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && python3 -c "
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

ChannelFactoryInitialize(0, \"eth0\")
client = SportClient()
client.SetTimeout(10.0)
client.Init()

print(\"Standing up...\")
client.StandUp()
time.sleep(3)
print(\"Standing down...\")
client.StandDown()
time.sleep(2)
print(\"EDU SDK verified!\")
"'
```

### 5.4 Test Dashboard
```bash
ssh unitreedog 'cd /home/unitree/justjustUnitree && source venv/bin/activate && python -m jjai_go2 --dashboard-only --port 5003 &'
# Open in browser: http://192.168.1.5:5003/unitreego2
```

---

## 6. Daily Development Workflow

### Start Coding
```bash
# SSH in (wireless, no cables)
ssh unitreedog

# Or run commands directly
ssh unitreedog 'cd justjustUnitree && source venv/bin/activate && python -m jjai_go2 --dashboard-only --port 5003'
```

### Deploy Code Changes
```bash
# From Mac — sync code to Jetson
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.pytest_cache' --exclude '*.egg-info' --exclude 'venv' \
  ~/Desktop/Bhutani\ Development/justjustUnitree/ \
  unitreedog:/home/unitree/justjustUnitree/

# Run tests
ssh unitreedog 'cd justjustUnitree && source venv/bin/activate && PYTHONPATH=src pytest tests/ -v'
```

### DDS Interface
All DDS commands from the Jetson use `eth0` (internal network to MCU). This works whether or not the ethernet cable to your Mac is connected — `eth0` is the Go2's internal bus, always active.

```python
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
ChannelFactoryInitialize(0, "eth0")  # Always use eth0 on the Jetson
```

---

## 7. Network Architecture

```
Home WiFi (192.168.1.x)
├── Mac (192.168.1.15)
│     └── ssh unitreedog ──────── WiFi ──────────┐
│                                                 │
├── Go2 External (192.168.1.17)                   │
│     └── WebRTC on port 9991                     │
│                                                 │
└── Jetson WiFi (192.168.1.5) ◄───────────────────┘
      │     └── TP-Link AC600 USB adapter (wlan0)
      │
      └── Go2 Internal Network (192.168.123.x, via eth0)
            ├── Jetson (192.168.123.18)
            ├── MCU (192.168.123.161) ← DDS sport commands go here
            └── Gateway (192.168.123.1) ← configured but unresponsive
```

**Key insight**: The Jetson has TWO network interfaces:
- `wlan0` (192.168.1.5) — WiFi to home network — for SSH, internet, dashboard
- `eth0` (192.168.123.18) — internal bus to MCU — for DDS motor control

Both are always active. No cables needed.

---

## 8. Troubleshooting

### Can't SSH over WiFi
```bash
# Check if Jetson is on WiFi
ping 192.168.1.5

# If not responding, connect via ethernet and check
ssh unitreedog-eth 'nmcli con show --active'
ssh unitreedog-eth 'nmcli dev wifi connect "justjustai" password "Build@magic7" ifname wlan0'
```

### WiFi Adapter Not Detected After Reboot
```bash
# SSH via ethernet
ssh unitreedog-eth

# Check if driver loaded
lsmod | grep 88XXau

# If not, reload
sudo modprobe 88XXau

# If modprobe fails, rebuild driver
cd /tmp/rtl8812au && sudo make install && sudo modprobe 88XXau
```

### DDS Not Receiving Robot State
```bash
# Check eth0 is up
ssh unitreedog 'ip addr show eth0'

# Check MCU is reachable
ssh unitreedog 'ping -c 2 192.168.123.161'

# Check CycloneDDS config
ssh unitreedog 'cat /home/unitree/cyclonedds_ws/cyclonedds.xml'
# Should show: <NetworkInterface name="eth0" .../>
```

### WiFi IP Changed (DHCP reassigned)
```bash
# Find new IP
ssh unitreedog-eth 'ip addr show wlan0 | grep "inet "'

# Update ~/.ssh/config on Mac with new IP
# Consider setting a static IP or DHCP reservation on your router
```

### Python 3.11 Not Found
```bash
# Check installation
which python3.11
# Should be /usr/local/bin/python3.11

# If missing, rebuild (see Phase 3, step 4.1)
```

### unitree_sdk2py Import Error (b2 module)
If you see `ImportError: cannot import name 'b2'`, fix the SDK init:
```bash
# On Mac (if running SDK locally)
# Edit: /path/to/site-packages/unitree_sdk2py/__init__.py
# Change: from . import idl, utils, core, rpc, go2, b2
# To:
from . import idl, utils, core, rpc, go2
try:
    from . import b2
except ImportError:
    b2 = None
```

---

## 9. Reference

### SSH Aliases
| Alias | Host | Use |
|-------|------|-----|
| `ssh unitreedog` | 192.168.1.5 | WiFi (daily use) |
| `ssh unitreedog-eth` | 192.168.123.18 | Ethernet (fallback) |

### File Locations on Jetson
```
/home/unitree/
├── justjustUnitree/          # Our codebase
│   ├── venv/                 # Python 3.11 virtualenv
│   ├── src/jjai_go2/         # Source code
│   ├── tests/                # 36 tests
│   └── config/go2.yaml       # Robot config
├── unitree_sdk2_python/      # Unitree SDK (editable install)
├── cyclonedds_ws/            # CycloneDDS 0.10.2 (pre-built)
│   ├── cyclonedds.xml        # DDS config (interface: eth0)
│   └── install/cyclonedds/   # CycloneDDS libraries
└── unitree/Odometer_service/ # Factory odometer service
```

### Credentials
| Service | Username | Password |
|---------|----------|----------|
| Jetson SSH | unitree | 123 |
| justjustai WiFi | - | Build@magic7 |
| Go2 AP hotspot | - | 00000000 |

### Available DDS Commands (EDU SDK)
| Command | Method | Description |
|---------|--------|-------------|
| damp | `Damp()` | Disable motors (go limp) |
| stand_up | `StandUp()` | Stand on all fours |
| stand_down | `StandDown()` | Lie down |
| move | `Move(vx, vy, vyaw)` | Velocity move (m/s, m/s, rad/s) |
| stop_move | `StopMove()` | Stop moving |
| balance_stand | `BalanceStand()` | Active balance |
| recovery | `RecoveryStand()` | Get up from fallen |
| walk_upright | `WalkUpright(bool)` | Walk on hind legs |
| back_flip | `BackFlip()` | Back flip |
| left_flip | `LeftFlip()` | Left flip |
| free_walk | `FreeWalk()` | Autonomous walking |
| cross_step | `CrossStep(bool)` | Cross-step dance |
| free_jump | `FreeJump(bool)` | Jump |
