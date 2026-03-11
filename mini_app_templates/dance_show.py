"""Dance Show — Choreographed trick sequence with photos.

Performs: Hello, Stretch, Dance1, Dance2, and captures photos between.
"""

import json, os, sys, time
sys.path.insert(0, "/home/unitree/unitree_sdk2_python")

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/unitree/mini_apps/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

low = {}
def low_handler(msg):
    low["battery_v"] = round(msg.power_v, 2)
    low["motor_temps"] = [msg.motor_state[i].temperature for i in range(12)]

def capture(vc, name):
    result = vc.GetImageSample()
    if isinstance(result, tuple) and result[0] == 0 and result[1]:
        raw = bytes(result[1])
        path = os.path.join(OUTPUT_DIR, f"{name}.jpg")
        with open(path, "wb") as f:
            f.write(raw)
        print(f"  Photo: {name}.jpg")
        return path
    return None

def main():
    print("=== MOMO DANCE SHOW ===")

    ChannelFactoryInitialize(0, "eth0")
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(low_handler, 10)
    time.sleep(1.5)

    client = SportClient()
    client.SetTimeout(5.0)
    client.Init()
    time.sleep(1)

    vc = VideoClient()
    vc.SetTimeout(5.0)
    vc.Init()
    time.sleep(1)

    bat = low.get("battery_v", 30)
    print(f"Battery: {bat}V")
    if bat < 24:
        print("ABORT: Low battery!")
        return

    client.RecoveryStand()
    time.sleep(3)

    photos = []
    tricks_done = []

    # Opening photo
    p = capture(vc, "opening")
    if p: photos.append(p)

    # Hello
    print("\n1. Hello wave!")
    client.Hello()
    time.sleep(3)
    tricks_done.append("hello")
    p = capture(vc, "after_hello")
    if p: photos.append(p)

    # Stretch
    print("\n2. Big stretch!")
    client.Stretch()
    time.sleep(4)
    tricks_done.append("stretch")

    # Dance 1
    print("\n3. Dance routine 1!")
    client.Dance1()
    time.sleep(6)
    tricks_done.append("dance1")
    p = capture(vc, "after_dance1")
    if p: photos.append(p)

    # Check temps
    max_t = max(low.get("motor_temps", [0]))
    if max_t > 70:
        print(f"  Motors warm ({max_t}C), cooling 10s...")
        time.sleep(10)

    # Dance 2
    print("\n4. Dance routine 2!")
    client.Dance2()
    time.sleep(6)
    tricks_done.append("dance2")
    p = capture(vc, "after_dance2")
    if p: photos.append(p)

    # Bow (sit then stand)
    print("\n5. Take a bow!")
    client.StandDown()
    time.sleep(2)
    client.RecoveryStand()
    time.sleep(3)
    tricks_done.append("bow")

    # Final photo
    p = capture(vc, "finale")
    if p: photos.append(p)

    client.StandDown()
    time.sleep(2)
    print("\nShow complete! Momo takes a rest.")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "dance_show",
        "tricks": tricks_done,
        "photos": len(photos),
        "battery_end": low.get("battery_v", 0),
        "max_motor_temp": max(low.get("motor_temps", [0])),
    }
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

if __name__ == "__main__":
    main()
