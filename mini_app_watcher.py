"""Momo Mini Apps Watcher — polls S3 for pending scripts, runs them, uploads results.

Runs as a systemd service on the Go2 Jetson.
Polls s3://robot-detections/momo-apps/pending/ every 5 seconds.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mini_app_watcher")

S3_BUCKET = "robot-detections"
S3_REGION = "ap-southeast-2"
S3_PENDING = "momo-apps/pending/"
S3_COMPLETED = "momo-apps/completed/"
APPS_DIR = Path("/home/unitree/mini_apps")
VENV_PYTHON = "/home/unitree/justjustUnitree/venv/bin/python3"
POLL_INTERVAL = 5
DEFAULT_TIMEOUT = 300  # 5 minutes
MAX_LOG_UPLOAD_INTERVAL = 5  # upload log every 5s

# Dangerous patterns to block
BLOCKLIST = [
    "os.system(",
    "subprocess.Popen(",
    "subprocess.call(",
    "subprocess.run(",
    "eval(",
    "exec(",
    "rm -rf",
    "rmdir",
    "shutil.rmtree",
    "import socket",
    "import requests",
    "import urllib.request",
    "__import__",
    "compile(",
]

# Required safety patterns (at least one must be present)
SAFETY_PATTERNS = ["StandDown", "StopMove", "standdown", "stopmove"]


def get_s3():
    return boto3.client("s3", region_name=S3_REGION)


def validate_script(code: str) -> tuple[bool, str]:
    """Check script for dangerous patterns."""
    for pattern in BLOCKLIST:
        if pattern in code:
            return False, f"Blocked pattern found: {pattern}"

    if len(code) > 50_000:
        return False, f"Script too large: {len(code)} bytes (max 50KB)"

    # Only require safety cleanup if script uses movement commands
    uses_movement = any(cmd in code for cmd in ["Move(", "RecoveryStand(", "SportClient"])
    if uses_movement:
        has_safety = any(p in code for p in SAFETY_PATTERNS)
        if not has_safety:
            return False, "No safety cleanup found (StandDown or StopMove required)"

    return True, "OK"


def upload_log(s3, app_id: str, run_id: str, log_text: str):
    """Upload current log to S3."""
    key = f"momo-apps/apps/{app_id}/runs/{run_id}/log.txt"
    try:
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=log_text.encode())
    except Exception as e:
        log.warning(f"Failed to upload log: {e}")


def upload_results(s3, app_id: str, run_id: str, output_dir: Path):
    """Upload all result files (photos, data) to S3."""
    if not output_dir.exists():
        return 0

    count = 0
    for fpath in output_dir.rglob("*"):
        if fpath.is_file():
            rel = fpath.relative_to(output_dir)
            key = f"momo-apps/apps/{app_id}/runs/{run_id}/{rel}"
            content_type = "image/jpeg" if fpath.suffix == ".jpg" else "application/octet-stream"
            if fpath.suffix == ".json":
                content_type = "application/json"
            try:
                s3.upload_file(str(fpath), S3_BUCKET, key, ExtraArgs={"ContentType": content_type})
                count += 1
            except Exception as e:
                log.warning(f"Failed to upload {rel}: {e}")
    return count


def update_status(s3, app_id: str, run_id: str, status: dict):
    """Write status.json for this run."""
    key = f"momo-apps/apps/{app_id}/runs/{run_id}/status.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(status, default=str).encode(),
            ContentType="application/json",
        )
    except Exception as e:
        log.warning(f"Failed to update status: {e}")


def run_script(s3, job: dict) -> dict:
    """Execute a mini app script and collect results."""
    app_id = job["app_id"]
    run_id = job["run_id"]
    script = job["script"]
    timeout = job.get("timeout", DEFAULT_TIMEOUT)

    # Validate
    ok, reason = validate_script(script)
    if not ok:
        log.error(f"Script validation failed: {reason}")
        return {"status": "failed", "error": f"Validation: {reason}", "duration": 0}

    # Prepare dirs
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = APPS_DIR / f"{run_id}.py"
    output_dir = APPS_DIR / f"{run_id}_output"
    output_dir.mkdir(exist_ok=True)

    # Write script
    script_path.write_text(script)

    # Build env
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/home/unitree/cyclonedds_ws/install/cyclonedds/lib"
    env["PYTHONPATH"] = "/home/unitree/unitree_sdk2_python"
    env["OUTPUT_DIR"] = str(output_dir)

    log.info(f"Running {run_id} (timeout={timeout}s)")
    update_status(s3, app_id, run_id, {"status": "running", "started_at": time.time()})

    t0 = time.time()
    full_log = ""
    last_log_upload = 0

    try:
        proc = subprocess.Popen(
            [VENV_PYTHON, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(APPS_DIR),
        )

        while proc.poll() is None:
            # Read available output
            line = proc.stdout.readline()
            if line:
                text = line.decode("utf-8", errors="replace")
                full_log += text
                log.info(f"  [{run_id}] {text.rstrip()}")

            # Periodic log upload
            now = time.time()
            if now - last_log_upload > MAX_LOG_UPLOAD_INTERVAL:
                upload_log(s3, app_id, run_id, full_log)
                last_log_upload = now

            # Timeout check
            if now - t0 > timeout:
                log.warning(f"Timeout! Killing {run_id}")
                proc.send_signal(signal.SIGTERM)
                time.sleep(2)
                if proc.poll() is None:
                    proc.kill()
                full_log += f"\n[TIMEOUT after {timeout}s]\n"
                break

        # Read remaining output
        remaining = proc.stdout.read()
        if remaining:
            full_log += remaining.decode("utf-8", errors="replace")

        duration = round(time.time() - t0, 1)
        exit_code = proc.returncode or 0

        # Final log upload
        upload_log(s3, app_id, run_id, full_log)

        # Upload result files
        uploaded = upload_results(s3, app_id, run_id, output_dir)
        log.info(f"Run {run_id} done: exit={exit_code}, duration={duration}s, files={uploaded}")

        status = {
            "status": "completed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
            "duration": duration,
            "files_uploaded": uploaded,
            "finished_at": time.time(),
        }
        if exit_code != 0:
            status["error"] = f"Script exited with code {exit_code}"

        return status

    except Exception as e:
        duration = round(time.time() - t0, 1)
        full_log += f"\n[ERROR: {e}]\n{traceback.format_exc()}\n"
        upload_log(s3, app_id, run_id, full_log)
        return {"status": "failed", "error": str(e), "duration": duration}

    finally:
        # Cleanup local files
        try:
            script_path.unlink(missing_ok=True)
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir, ignore_errors=True)
        except Exception:
            pass


def process_job(s3, key: str):
    """Download and process a pending job."""
    try:
        body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
        job = json.loads(body)
    except Exception as e:
        log.error(f"Failed to read job {key}: {e}")
        return

    run_id = job.get("run_id", "unknown")
    app_id = job.get("app_id", "unknown")
    log.info(f"Processing job: app={app_id} run={run_id}")

    # Run the script
    result = run_script(s3, job)

    # Update status
    update_status(s3, app_id, run_id, result)

    # Move from pending to completed
    try:
        completed_key = f"{S3_COMPLETED}{os.path.basename(key)}"
        s3.copy_object(
            Bucket=S3_BUCKET,
            CopySource={"Bucket": S3_BUCKET, "Key": key},
            Key=completed_key,
        )
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
        log.info(f"Job {run_id} moved to completed/")
    except Exception as e:
        log.warning(f"Failed to move job: {e}")


def poll_loop():
    """Main polling loop."""
    s3 = get_s3()
    log.info("Momo Mini Apps Watcher started")
    log.info(f"Polling s3://{S3_BUCKET}/{S3_PENDING} every {POLL_INTERVAL}s")

    while True:
        try:
            resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PENDING)
            objects = resp.get("Contents", [])

            # Filter to .json files only
            jobs = [o for o in objects if o["Key"].endswith(".json")]

            if jobs:
                # Process oldest first
                jobs.sort(key=lambda x: x["LastModified"])
                log.info(f"Found {len(jobs)} pending job(s)")
                for obj in jobs:
                    process_job(s3, obj["Key"])

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        log.info("Watcher stopped")
