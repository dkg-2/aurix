import os
import json
import redis
import uuid
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
QUEUE_NAME = "aurix_scan_queue"

def trigger_test_scan():
    if not REDIS_URL:
        print("[ERROR] UPSTASH_REDIS_URL is not set.")
        return

    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Create a mock job ticket exactly like Bhavya's API does
    scan_id = str(uuid.uuid4())
    job_ticket = {
        "scan_id": scan_id,
        "url": "https://github.com/octocat/Hello-World",
        "user_id": "local-test-user"
    }
    
    print(f"[TEST] Pushing Job Ticket into Upstash Redis...")
    print(json.dumps(job_ticket, indent=2))
    
    r.lpush(QUEUE_NAME, json.dumps(job_ticket))
    print(f"[TEST] Job pushed successfully! The Queue Listener should pick it up within 5 seconds.")

if __name__ == "__main__":
    trigger_test_scan()
