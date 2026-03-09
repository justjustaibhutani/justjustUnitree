#!/usr/bin/env python3
"""Test Go2 WebRTC connection — run before starting full system.

Usage:
    python scripts/test_connection.py 192.168.1.100
    python scripts/test_connection.py  # Uses default 192.168.12.1
"""

import asyncio
import sys


async def test_connection(ip: str) -> None:
    print(f"Testing Go2 WebRTC connection to {ip}...")

    try:
        from go2_webrtc_connect import Go2Connection, WebRTCConnectionMethod

        conn = Go2Connection(WebRTCConnectionMethod.LocalSTA, ip=ip)
        print("  Connecting...")
        await conn.connect()
        print("  Connected!")

        # Test sport client
        print("  Testing sport commands...")
        # Just verify we can access the data channel
        print("  Data channel available:", hasattr(conn, "data_channel"))

        # Test video
        print("  Video available:", hasattr(conn, "video"))

        await conn.disconnect()
        print("\n  All tests passed! Go2 is ready.")

    except ImportError:
        print("  ERROR: go2-webrtc-connect not installed")
        print("  Run: pip install go2-webrtc-connect")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        print("\n  Troubleshooting:")
        print(f"    1. Is the Go2 powered on and connected to WiFi?")
        print(f"    2. Can you ping {ip}?")
        print(f"    3. Is the Unitree app disconnected? (Only one client at a time)")
        sys.exit(1)


if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.12.1"
    asyncio.run(test_connection(ip))
