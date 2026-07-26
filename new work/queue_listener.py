import os
import json
import redis
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
QUEUE_NAME = "aurix_scan_queue"

def main():
    if not REDIS_URL:
        print("[ERROR] UPSTASH_REDIS_URL is not set in .env file.")
        print("[ERROR] Please ask Bhavya for the connection string and add it.")
        return

    print(f"[SYSTEM] Connecting to Upstash Redis...")
    try:
        # Added socket_timeout=10 to prevent "Timeout reading from socket" during BRPOP
        r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=10)
        r.ping() # Test connection
        print(f"[SYSTEM] Successfully connected! Listening on queue: {QUEUE_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        return

    while True:
        try:
            # BRPOP blocks for 5 seconds waiting for a job ticket
            result = r.brpop(QUEUE_NAME, timeout=5)
            if result:
                _, message = result
                job_ticket = json.loads(message)
                
                scan_id = job_ticket.get("scan_id")
                # Handle both URL uploads and VS Code zip uploads
                target = job_ticket.get("url") or job_ticket.get("storage_path")
                
                if not scan_id or not target:
                    print(f"[WARN] Invalid job ticket received: {job_ticket}")
                    continue
                
                print(f"\n==================================================")
                print(f"[JOB RECEIVED] Scan ID: {scan_id}")
                print(f"[JOB RECEIVED] Target: {target}")
                print(f"==================================================")
                
                # Execute the worker script INSIDE the running Docker container
                cmd = ["docker", "exec", "aurix_ai_worker", "python", "aurix_worker.py", target, scan_id]
                
                print(f"[SYSTEM] Spawning worker process inside Docker...")
                # We use subprocess so the listener stays perfectly isolated from the heavy LangGraph execution
                subprocess.run(cmd)
                
                print(f"[SYSTEM] Worker process finished. Resuming queue polling...")

        except KeyboardInterrupt:
            print("\n[SYSTEM] Shutting down Queue Listener gracefully.")
            break
        except Exception as e:
            print(f"[ERROR] Polling loop encountered an error: {e}")
            import time
            time.sleep(5) # Backoff before retrying

if __name__ == "__main__":
    main()
