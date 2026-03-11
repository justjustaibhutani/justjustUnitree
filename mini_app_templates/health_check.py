"""Health Check — Full sensor diagnostic report.

Reads all sensors, checks motor temps, battery, IMU, foot force, and generates a report.
"""

import json, os, sys, time
sys.path.insert(0, "/home/unitree/unitree_sdk2_python")

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_, SportModeState_

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/unitree/mini_apps/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

low, sport = {}, {}

def low_handler(msg):
    low["battery_v"] = round(msg.power_v, 2)
    low["battery_pct"] = msg.bms_state.soc
    low["foot_force"] = [msg.foot_force[i] for i in range(4)]
    low["motor_temps"] = [msg.motor_state[i].temperature for i in range(12)]
    low["motor_torques"] = [round(msg.motor_state[i].tau_est, 2) for i in range(12)]
    low["motor_speeds"] = [round(msg.motor_state[i].dq, 2) for i in range(12)]
    low["imu_rpy"] = [round(msg.imu_state.rpy[i], 4) for i in range(3)]
    low["imu_accel"] = [round(msg.imu_state.accelerometer[i], 3) for i in range(3)]
    low["imu_gyro"] = [round(msg.imu_state.gyroscope[i], 3) for i in range(3)]

def sport_handler(msg):
    sport["position"] = [round(msg.position[i], 4) for i in range(3)]
    sport["velocity"] = [round(msg.velocity[i], 3) for i in range(3)]
    sport["body_height"] = round(msg.body_height, 3)
    sport["mode"] = msg.mode
    sport["gait_type"] = msg.gait_type

MOTOR_NAMES = [
    "FR_hip", "FR_thigh", "FR_calf",
    "FL_hip", "FL_thigh", "FL_calf",
    "RR_hip", "RR_thigh", "RR_calf",
    "RL_hip", "RL_thigh", "RL_calf",
]

def main():
    print("=" * 50)
    print("MOMO HEALTH CHECK")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    ChannelFactoryInitialize(0, "eth0")
    sub1 = ChannelSubscriber("rt/lowstate", LowState_)
    sub1.Init(low_handler, 10)
    sub2 = ChannelSubscriber("rt/sportmodestate", SportModeState_)
    sub2.Init(sport_handler, 10)

    # Collect samples over 3 seconds
    print("\nCollecting sensor data (3 seconds)...")
    time.sleep(3)

    # Battery
    bat_v = low.get("battery_v", 0)
    bat_pct = low.get("battery_pct", 0)
    bat_status = "GOOD" if bat_v > 26 else "LOW" if bat_v > 24 else "CRITICAL"
    print(f"\n--- BATTERY ---")
    print(f"  Voltage: {bat_v}V")
    print(f"  Percentage: {bat_pct}%")
    print(f"  Status: {bat_status}")

    # Motors
    temps = low.get("motor_temps", [0]*12)
    torques = low.get("motor_torques", [0]*12)
    max_temp = max(temps)
    motor_status = "GOOD" if max_temp < 50 else "WARM" if max_temp < 65 else "HOT" if max_temp < 75 else "CRITICAL"
    print(f"\n--- MOTORS ---")
    print(f"  Max temperature: {max_temp}C ({motor_status})")
    for i, name in enumerate(MOTOR_NAMES):
        flag = " !!!" if temps[i] > 65 else ""
        print(f"  {name:12s}: {temps[i]:3d}C  torque={torques[i]:6.2f}Nm{flag}")

    # IMU
    rpy = low.get("imu_rpy", [0]*3)
    accel = low.get("imu_accel", [0]*3)
    print(f"\n--- IMU ---")
    print(f"  Roll:  {rpy[0]:7.4f} rad ({rpy[0]*57.3:.1f} deg)")
    print(f"  Pitch: {rpy[1]:7.4f} rad ({rpy[1]*57.3:.1f} deg)")
    print(f"  Yaw:   {rpy[2]:7.4f} rad ({rpy[2]*57.3:.1f} deg)")
    print(f"  Accel: x={accel[0]:.3f} y={accel[1]:.3f} z={accel[2]:.3f} m/s2")

    # Foot Force
    ff = low.get("foot_force", [0]*4)
    legs = ["FR", "FL", "RR", "RL"]
    print(f"\n--- FOOT FORCE ---")
    for i, leg in enumerate(legs):
        contact = "ground" if ff[i] > 10 else "air"
        print(f"  {leg}: {ff[i]:6.1f}N ({contact})")

    # Position
    pos = sport.get("position", [0]*3)
    vel = sport.get("velocity", [0]*3)
    print(f"\n--- ODOMETRY ---")
    print(f"  Position: x={pos[0]:.4f} y={pos[1]:.4f} z={pos[2]:.4f}")
    print(f"  Velocity: vx={vel[0]:.3f} vy={vel[1]:.3f} vyaw={vel[2]:.3f}")
    print(f"  Body height: {sport.get('body_height', 0):.3f}m")
    print(f"  Mode: {sport.get('mode', '?')}")

    # Overall
    issues = []
    if bat_status == "CRITICAL": issues.append("Battery critically low!")
    if motor_status in ["HOT", "CRITICAL"]: issues.append(f"Motor overheating! ({max_temp}C)")
    if all(f < 5 for f in ff): issues.append("No ground contact (in air?)")

    print(f"\n{'=' * 50}")
    print(f"OVERALL: {'HEALTHY' if not issues else 'ISSUES FOUND'}")
    if issues:
        for iss in issues:
            print(f"  WARNING: {iss}")
    else:
        print("  All systems nominal.")
    print(f"{'=' * 50}")

    # Save report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "health_check",
        "battery": {"voltage": bat_v, "percent": bat_pct, "status": bat_status},
        "motors": {
            "max_temp": max_temp,
            "status": motor_status,
            "temps": dict(zip(MOTOR_NAMES, temps)),
            "torques": dict(zip(MOTOR_NAMES, torques)),
        },
        "imu": {"roll": rpy[0], "pitch": rpy[1], "yaw": rpy[2], "accel": accel},
        "foot_force": dict(zip(legs, ff)),
        "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
        "overall": "healthy" if not issues else "issues",
        "issues": issues,
    }
    with open(os.path.join(OUTPUT_DIR, "data.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport saved to {OUTPUT_DIR}/data.json")

if __name__ == "__main__":
    main()
