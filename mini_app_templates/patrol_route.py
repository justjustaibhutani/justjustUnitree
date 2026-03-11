"""Patrol Route — Walk a square pattern, photograph each corner.

Walks a 1m x 1m square, taking photos and sensor readings at each corner.
"""

import json, math, os, sys, time
sys.path.insert(0, "/home/unitree/unitree_sdk2_python")

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.obstacles_avoid.obstacles_avoid_client import ObstaclesAvoidClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_, SportModeState_

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/unitree/mini_apps/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

low, sport = {}, {}
def low_handler(msg):
    low["battery_v"] = round(msg.power_v, 2)
    low["foot_force"] = [msg.foot_force[i] for i in range(4)]
    low["motor_temps"] = [msg.motor_state[i].temperature for i in range(12)]

def sport_handler(msg):
    sport["position"] = [round(msg.position[i], 4) for i in range(3)]

def safe():
    if low.get("battery_v", 30) < 24:
        print("ABORT: Low battery!")
        return False
    if max(low.get("motor_temps", [0])) > 75:
        print("COOLING 30s...")
        time.sleep(30)
    return True

def move(client, vx, vy, vyaw, dur, desc):
    print(f"  -> {desc}")
    client.Move(vx, vy, vyaw)
    time.sleep(dur)
    client.StopMove()
    time.sleep(0.8)

def capture(vc, name):
    result = vc.GetImageSample()
    if isinstance(result, tuple) and result[0] == 0 and result[1]:
        raw = bytes(result[1])
        path = os.path.join(OUTPUT_DIR, f"{name}.jpg")
        with open(path, "wb") as f:
            f.write(raw)
        print(f"  Photo: {name}.jpg ({len(raw)//1024}KB)")
        return path
    return None

def main():
    print("=== PATROL ROUTE (1m square) ===")
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

    oa = ObstaclesAvoidClient()
    oa.SetTimeout(5.0)
    oa.Init()
    oa.SwitchSet(True)
    print("Obstacle avoidance ON")

    if not safe():
        return

    client.RecoveryStand()
    time.sleep(3)

    photos = []
    waypoints = []
    corners = ["start", "corner_1", "corner_2", "corner_3"]
    t0 = time.time()

    for i, corner in enumerate(corners):
        print(f"\n--- {corner.upper()} ---")
        if not safe():
            break

        # Move to next corner
        if i == 1:
            move(client, 0.2, 0, 0, 5, "forward 1m")
        elif i == 2:
            move(client, 0, 0, -0.8, 1.57, "turn right 90")
            move(client, 0.2, 0, 0, 5, "forward 1m")
        elif i == 3:
            move(client, 0, 0, -0.8, 1.57, "turn right 90")
            move(client, 0.2, 0, 0, 5, "forward 1m")

        # Capture
        p = capture(vc, corner)
        if p: photos.append(p)

        pos = sport.get("position", [0, 0, 0])
        waypoints.append({
            "name": corner,
            "x": pos[0], "y": pos[1],
            "battery": low.get("battery_v", 0),
            "foot_force": low.get("foot_force", [0]*4)[:],
        })
        print(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f})")

    # Return home
    print("\n--- RETURNING HOME ---")
    move(client, 0, 0, -0.8, 1.57, "turn right 90")
    move(client, 0.2, 0, 0, 5, "forward 1m")
    move(client, 0, 0, -0.8, 1.57, "face original direction")

    p = capture(vc, "home")
    if p: photos.append(p)

    client.StandDown()
    time.sleep(2)
    duration = round(time.time() - t0, 1)

    # Calculate total distance
    total_dist = sum(
        math.sqrt((waypoints[i]["x"] - waypoints[i-1]["x"])**2 +
                   (waypoints[i]["y"] - waypoints[i-1]["y"])**2)
        for i in range(1, len(waypoints))
    )

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "patrol_route",
        "duration_s": duration,
        "total_distance_m": round(total_dist, 2),
        "photos": len(photos),
        "waypoints": waypoints,
    }
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nPatrol complete! {len(photos)} photos, {total_dist:.1f}m, {duration}s")

if __name__ == "__main__":
    main()
