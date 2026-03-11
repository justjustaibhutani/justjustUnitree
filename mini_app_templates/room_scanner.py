"""Room Scanner — 360-degree photo survey at current position.

Takes photos at 6 angles (every 60 degrees) with full sensor data.
"""

import json, math, os, sys, time
sys.path.insert(0, "/home/unitree/unitree_sdk2_python")

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_, SportModeState_

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/unitree/mini_apps/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

low, sport = {}, {}

def low_handler(msg):
    low["battery_v"] = round(msg.power_v, 2)
    low["battery_pct"] = msg.bms_state.soc
    low["foot_force"] = [msg.foot_force[i] for i in range(4)]
    low["motor_temps"] = [msg.motor_state[i].temperature for i in range(12)]
    low["imu_rpy"] = [round(msg.imu_state.rpy[i], 4) for i in range(3)]

def sport_handler(msg):
    sport["position"] = [round(msg.position[i], 4) for i in range(3)]

def safe():
    if low.get("battery_v", 30) < 24:
        print("ABORT: Low battery!")
        return False
    if max(low.get("motor_temps", [0])) > 75:
        print("COOLING: Waiting 30s...")
        time.sleep(30)
    return True

def capture(vc, name):
    result = vc.GetImageSample()
    if isinstance(result, tuple) and result[0] == 0 and result[1]:
        raw = bytes(result[1])
        path = os.path.join(OUTPUT_DIR, f"{name}.jpg")
        with open(path, "wb") as f:
            f.write(raw)
        print(f"  Photo: {name}.jpg ({len(raw)//1024}KB)")
        return path
    print(f"  Photo failed: {name}")
    return None

def main():
    print("=== ROOM SCANNER ===")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    ChannelFactoryInitialize(0, "eth0")
    sub1 = ChannelSubscriber("rt/lowstate", LowState_)
    sub1.Init(low_handler, 10)
    sub2 = ChannelSubscriber("rt/sportmodestate", SportModeState_)
    sub2.Init(sport_handler, 10)
    time.sleep(1.5)

    client = SportClient()
    client.SetTimeout(5.0)
    client.Init()
    time.sleep(1)

    vc = VideoClient()
    vc.SetTimeout(5.0)
    vc.Init()
    time.sleep(1)

    print(f"Battery: {low.get('battery_v', '?')}V")
    if not safe():
        return

    client.RecoveryStand()
    time.sleep(3)

    photos = []
    scans = []
    angles = ["0deg", "60deg", "120deg", "180deg", "240deg", "300deg"]

    for i, angle in enumerate(angles):
        if i > 0:
            print(f"  Rotating 60 degrees...")
            client.Move(0, 0, -0.8)
            time.sleep(0.75)  # ~60 degrees at 0.8 rad/s
            client.StopMove()
            time.sleep(0.5)

        p = capture(vc, f"scan_{angle}")
        if p:
            photos.append(p)

        scans.append({
            "angle": angle,
            "position": sport.get("position", [0, 0, 0])[:],
            "foot_force": low.get("foot_force", [0]*4)[:],
            "imu_rpy": low.get("imu_rpy", [0]*3)[:],
            "battery_v": low.get("battery_v", 0),
        })
        print(f"  [{angle}] pos=({sport.get('position', [0,0,0])[0]:.2f}, {sport.get('position', [0,0,0])[1]:.2f})")

    client.StandDown()
    time.sleep(2)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "room_scan",
        "photos": len(photos),
        "scans": scans,
    }
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nDone! {len(photos)} photos captured.")

if __name__ == "__main__":
    main()
