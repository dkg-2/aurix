import os
import json
import redis
import subprocess
import time
import threading
import psutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
QUEUE_NAME = "aurix_scan_queue"
MAX_CONCURRENT_WORKERS = int(os.getenv("MAX_WORKERS", "3"))

# --- Resource Thresholds (Safety Rails for AWS) ---
MAX_MEMORY_PERCENT = int(os.getenv("MAX_MEMORY_PERCENT", "85"))  # Pause if RAM exceeds this
MAX_CPU_PERCENT = int(os.getenv("MAX_CPU_PERCENT", "90"))        # Pause if CPU exceeds this
HEALTH_CHECK_INTERVAL = 10  # seconds between resource checks

# Thread-safe tracking of active workers
active_workers = {}  # {scan_id: {"process": Popen, "started_at": float}}
workers_lock = threading.Lock()

# --- Webhook Helper (so listener can mark FAILED if worker crashes) ---
WEBHOOK_PROGRESS_URL = os.getenv("AURIX_PROGRESS_WEBHOOK_URL", "")
WEBHOOK_TOKEN = os.getenv("AURIX_WEBHOOK_TOKEN", "aurix-dev-token")

def _post_progress(scan_id, status, message=""):
    """Send a lightweight status update to Bhavya's backend."""
    if not WEBHOOK_PROGRESS_URL:
        return
    try:
        import requests
        requests.post(WEBHOOK_PROGRESS_URL, json={
            "scan_id": scan_id, "status": status, "message": message
        }, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WEBHOOK_TOKEN}"
        }, timeout=10)
    except Exception:
        pass  # Non-critical


def check_system_health():
    """Returns True if the system has enough resources to accept a new job."""
    try:
        mem = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=1)
        
        if mem > MAX_MEMORY_PERCENT:
            print(f"[HEALTH] WARNING: Memory at {mem}% (limit: {MAX_MEMORY_PERCENT}%). Pausing intake.")
            return False
        if cpu > MAX_CPU_PERCENT:
            print(f"[HEALTH] WARNING: CPU at {cpu}% (limit: {MAX_CPU_PERCENT}%). Pausing intake.")
            return False
        return True
    except Exception:
        return True  # If psutil fails, don't block — optimistic


def reap_finished_workers():
    """Cleans up workers that have finished. Detects crashed workers and sends FAILED webhook."""
    with workers_lock:
        finished = []
        for scan_id, info in active_workers.items():
            proc = info["process"]
            retcode = proc.poll()  # Non-blocking check
            if retcode is not None:
                elapsed = round(time.time() - info["started_at"], 1)
                if retcode == 0:
                    print(f"[REAPER] Worker {scan_id} completed successfully in {elapsed}s.")
                else:
                    print(f"[REAPER] Worker {scan_id} CRASHED (exit code {retcode}) after {elapsed}s.")
                    # Capture stderr for debugging
                    try:
                        stderr = proc.stderr.read().decode("utf-8", errors="replace")[-500:]
                        print(f"[REAPER] Last stderr: {stderr}")
                    except Exception:
                        pass
                    # Notify backend that this scan failed
                    _post_progress(scan_id, "FAILED", f"Worker crashed with exit code {retcode}")
                finished.append(scan_id)
        for scan_id in finished:
            del active_workers[scan_id]


def detect_stuck_workers(timeout_minutes=15):
    """Kills workers that have been running longer than the timeout (stuck scans)."""
    with workers_lock:
        now = time.time()
        stuck = []
        for scan_id, info in active_workers.items():
            elapsed_min = (now - info["started_at"]) / 60
            if elapsed_min > timeout_minutes:
                print(f"[WATCHDOG] Worker {scan_id} has been running for {elapsed_min:.1f} min. KILLING.")
                try:
                    info["process"].kill()
                except Exception:
                    pass
                _post_progress(scan_id, "FAILED", f"Scan timed out after {timeout_minutes} minutes")
                stuck.append(scan_id)
        for scan_id in stuck:
            del active_workers[scan_id]


def main():
    if not REDIS_URL:
        print("[ERROR] UPSTASH_REDIS_URL is not set in .env file.")
        return

    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║   AURIX AI Engine — Queue Listener v2.0         ║")
    print(f"║   Max Workers: {MAX_CONCURRENT_WORKERS}                                ║")
    print(f"║   Memory Limit: {MAX_MEMORY_PERCENT}%                              ║")
    print(f"║   CPU Limit: {MAX_CPU_PERCENT}%                                 ║")
    print(f"╚══════════════════════════════════════════════════╝")
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=10)
        r.ping()
        print(f"[SYSTEM] Connected to Upstash Redis. Listening on: {QUEUE_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        return

    last_health_check = 0
    last_watchdog_check = 0

    while True:
        try:
            now = time.time()

            # 1. Reap finished workers every loop
            reap_finished_workers()

            # 2. Run watchdog every 60 seconds to kill stuck scans
            if now - last_watchdog_check > 60:
                detect_stuck_workers(timeout_minutes=15)
                last_watchdog_check = now

            # 3. Check capacity
            with workers_lock:
                current_load = len(active_workers)
            
            if current_load >= MAX_CONCURRENT_WORKERS:
                time.sleep(3)
                continue

            # 4. Check system health every HEALTH_CHECK_INTERVAL seconds
            if now - last_health_check > HEALTH_CHECK_INTERVAL:
                if not check_system_health():
                    time.sleep(5)
                    last_health_check = now
                    continue
                last_health_check = now

            # 5. Pop a job from the queue
            result = r.brpop(QUEUE_NAME, timeout=5)
            if not result:
                continue

            _, message = result
            job_ticket = json.loads(message)
            
            scan_id = job_ticket.get("scan_id")
            target = job_ticket.get("url") or job_ticket.get("storage_path")
            
            if not scan_id or not target:
                print(f"[WARN] Invalid job ticket: {job_ticket}")
                continue
            
            # Check for duplicate — don't re-scan something already in progress
            with workers_lock:
                if scan_id in active_workers:
                    print(f"[WARN] Scan {scan_id} is already running. Skipping duplicate.")
                    continue
            
            print(f"\n{'='*60}")
            print(f"[JOB] Scan ID: {scan_id}")
            print(f"[JOB] Target:  {target}")
            print(f"[JOB] Slots:   {current_load + 1}/{MAX_CONCURRENT_WORKERS}")
            print(f"{'='*60}")
            
            # 6. Spawn worker as a NON-BLOCKING subprocess
            # Output goes to a per-scan log file (NOT subprocess.PIPE which can block!)
            log_dir = os.path.join(os.path.dirname(__file__), "worker-logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = open(os.path.join(log_dir, f"worker_{scan_id}.log"), "w")

            cmd = ["docker", "exec", "aurix_ai_worker", "python", "aurix_worker.py", target, scan_id]
            
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file
            )
            
            with workers_lock:
                active_workers[scan_id] = {
                    "process": process,
                    "started_at": time.time()
                }
            
            print(f"[SYSTEM] Worker launched. Resuming queue polling immediately.")

        except KeyboardInterrupt:
            print("\n[SYSTEM] Graceful shutdown initiated.")
            with workers_lock:
                if active_workers:
                    print(f"[SYSTEM] Waiting for {len(active_workers)} worker(s) to finish (max 60s)...")
                    for scan_id, info in active_workers.items():
                        try:
                            info["process"].wait(timeout=60)
                        except subprocess.TimeoutExpired:
                            info["process"].kill()
                            print(f"[SYSTEM] Force-killed worker {scan_id}")
            break
        except redis.exceptions.ConnectionError as e:
            print(f"[ERROR] Redis connection lost: {e}. Reconnecting in 10s...")
            time.sleep(10)
            try:
                r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=10)
                r.ping()
                print("[SYSTEM] Reconnected to Redis.")
            except Exception:
                pass
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
