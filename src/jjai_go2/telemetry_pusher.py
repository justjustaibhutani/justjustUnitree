"""Momo telemetry push daemon — reads DDS + psutil, POSTs to dashboard.

Runs on Go2 Jetson. Pushes motor temps, battery, and system stats
to dashboard.justjust.ai every 10 seconds.

Usage:
    LD_LIBRARY_PATH=/home/unitree/cyclonedds_ws/install/cyclonedds/lib \
    python3 -m jjai_go2.telemetry_pusher

Or standalone:
    LD_LIBRARY_PATH=/home/unitree/cyclonedds_ws/install/cyclonedds/lib \
    python3 src/jjai_go2/telemetry_pusher.py
"""

import json
import os
import sys
import time
import threading
import logging
import urllib.request
import urllib.error

import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("momo-telemetry")

# --- Config ---
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://16.176.106.56")
AUTH_KEY = os.environ.get("MOMO_AUTH_KEY", "momo-telemetry-secret-key")
PUSH_INTERVAL = int(os.environ.get("PUSH_INTERVAL", "2"))
DDS_INTERFACE = os.environ.get("DDS_INTERFACE", "eth0")

# Motor name mapping (Go2 EDU Plus standard layout)
MOTOR_NAMES = [
    "FR_hip", "FR_thigh", "FR_calf",   # 0-2: Front Right
    "FL_hip", "FL_thigh", "FL_calf",   # 3-5: Front Left
    "RR_hip", "RR_thigh", "RR_calf",   # 6-8: Rear Right
    "RL_hip", "RL_thigh", "RL_calf",   # 9-11: Rear Left
]

# --- DDS State ---
_latest_lowstate = None
_lowstate_lock = threading.Lock()
_boot_time = time.time()


def init_dds():
    """Initialize DDS subscriber for LowState."""
    global _latest_lowstate
    try:
        from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
        from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

        ChannelFactoryInitialize(0, DDS_INTERFACE)

        def on_lowstate(msg: LowState_):
            global _latest_lowstate
            with _lowstate_lock:
                _latest_lowstate = msg

        sub = ChannelSubscriber("rt/lowstate", LowState_)
        sub.Init(on_lowstate, 10)
        log.info("DDS subscriber initialized on %s", DDS_INTERFACE)
        return True
    except Exception as e:
        log.error("Failed to init DDS: %s", e)
        return False


def read_jetson_temps():
    """Read Jetson thermal zones."""
    cpu_temp = None
    gpu_temp = None
    try:
        # Jetson Orin NX thermal zones
        for i in range(10):
            path = f"/sys/class/thermal/thermal_zone{i}/temp"
            type_path = f"/sys/class/thermal/thermal_zone{i}/type"
            if not os.path.exists(path):
                break
            with open(path) as f:
                temp = int(f.read().strip()) / 1000.0
            zone_type = ""
            if os.path.exists(type_path):
                with open(type_path) as f:
                    zone_type = f.read().strip().lower()
            if "cpu" in zone_type or "soc" in zone_type:
                cpu_temp = max(cpu_temp or 0, temp)
            elif "gpu" in zone_type:
                gpu_temp = max(gpu_temp or 0, temp)
            elif cpu_temp is None:
                cpu_temp = temp  # fallback: first zone is usually CPU
    except Exception:
        pass

    # Fallback to psutil
    if cpu_temp is None:
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if "cpu" in entry.label.lower() or "soc" in entry.label.lower():
                        cpu_temp = entry.current
                    elif "gpu" in entry.label.lower():
                        gpu_temp = entry.current
        except Exception:
            pass

    return cpu_temp, gpu_temp


def collect_telemetry():
    """Build telemetry payload from DDS + psutil."""
    payload = {
        "robot_id": "momo",
        "timestamp": time.time(),
        "auth_key": AUTH_KEY,
    }

    # Motor temps + battery from DDS
    with _lowstate_lock:
        ls = _latest_lowstate

    if ls is not None:
        import math
        motors = {}
        for i, name in enumerate(MOTOR_NAMES):
            ms = ls.motor_state[i]
            motors[name] = {
                "temp": int(ms.temperature),
                "q": round(math.degrees(ms.q), 2),        # angle in degrees
                "dq": round(math.degrees(ms.dq), 2),      # velocity deg/s
                "tau": round(ms.tau_est, 2),               # torque Nm
                "mode": int(ms.mode),
                "lost": int(ms.lost),
                "index": i,
            }
        payload["motors"] = motors

        # IMU
        try:
            imu = ls.imu_state
            payload["imu"] = {
                "rpy": [round(math.degrees(x), 2) for x in list(imu.rpy)],
                "gyro": [round(x, 3) for x in list(imu.gyroscope)],
                "accel": [round(x, 3) for x in list(imu.accelerometer)],
                "temp": int(imu.temperature),
            }
        except Exception:
            pass

        # Foot force
        try:
            payload["foot_force"] = [int(x) for x in list(ls.foot_force)[:4]]
        except Exception:
            pass

        # Power
        try:
            payload["power"] = {
                "voltage": round(float(ls.power_v), 2),
                "current": round(float(ls.power_a), 2),
            }
        except Exception:
            pass

        # Battery / BMS
        bms = ls.bms_state
        payload["battery"] = {
            "soc": int(bms.soc),
            "status": int(bms.status),
            "current": int(bms.current),
            "cycle": int(bms.cycle),
        }
        try:
            cell_vols = list(bms.cell_vol)
            if cell_vols and any(v > 0 for v in cell_vols):
                payload["battery"]["voltage"] = round(sum(cell_vols) / 1000.0, 2)
                payload["battery"]["cells"] = [round(v / 1000.0, 3) for v in cell_vols if v > 0]
        except Exception:
            pass
    else:
        payload["motors"] = None
        payload["battery"] = None

    # Jetson system stats
    cpu_temp, gpu_temp = read_jetson_temps()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    payload["jetson"] = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "ram_percent": mem.percent,
        "disk_percent": disk.percent,
        "cpu_temp": round(cpu_temp, 1) if cpu_temp else None,
        "gpu_temp": round(gpu_temp, 1) if gpu_temp else None,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }

    return payload


def push_telemetry(payload):
    """POST telemetry to dashboard."""
    url = f"{DASHBOARD_URL}/api/momo/telemetry"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Host": "dashboard.justjust.ai"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except urllib.error.URLError as e:
        log.warning("Push failed: %s", e.reason if hasattr(e, "reason") else e)
        return False
    except Exception as e:
        log.warning("Push failed: %s", e)
        return False


def main():
    log.info("Momo telemetry pusher starting")
    log.info("Dashboard: %s | Interval: %ds | DDS: %s", DASHBOARD_URL, PUSH_INTERVAL, DDS_INTERFACE)

    # Prime CPU percent (first call always returns 0)
    psutil.cpu_percent(interval=None)

    dds_ok = init_dds()
    if not dds_ok:
        log.warning("DDS init failed — will push Jetson stats only (no motor/battery data)")

    # Wait for first DDS message
    if dds_ok:
        log.info("Waiting for first DDS LowState...")
        for _ in range(50):
            with _lowstate_lock:
                if _latest_lowstate is not None:
                    break
            time.sleep(0.1)
        with _lowstate_lock:
            if _latest_lowstate is not None:
                log.info("DDS LowState received")
            else:
                log.warning("No DDS LowState after 5s — robot may not be running")

    push_count = 0
    fail_count = 0

    while True:
        try:
            payload = collect_telemetry()
            ok = push_telemetry(payload)
            if ok:
                push_count += 1
                fail_count = 0
                if push_count % 30 == 1:  # Log every ~5 min
                    batt = payload.get("battery", {})
                    soc = batt.get("soc", "?") if batt else "?"
                    log.info("Push #%d OK | Battery: %s%% | CPU: %s%%",
                             push_count, soc, payload["jetson"]["cpu_percent"])
            else:
                fail_count += 1
                if fail_count <= 3 or fail_count % 30 == 0:
                    log.warning("Push failed (%d consecutive)", fail_count)
        except Exception as e:
            log.error("Telemetry loop error: %s", e)

        time.sleep(PUSH_INTERVAL)


if __name__ == "__main__":
    main()
