import os
import glob
import json
import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("AURIX_WEBHOOK_URL")
TOKEN = os.getenv("AURIX_WEBHOOK_TOKEN")

dlq_files = glob.glob("pending-sync/failed_sync_*.json")

if not dlq_files:
    print("No failed syncs found in Dead Letter Queue!")
else:
    for file_path in dlq_files:
        print(f"Retrying payload: {file_path}")
        with open(file_path, "r") as f:
            payload = json.load(f)
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}"
        }
        
        try:
            print(f"Sending to {WEBHOOK_URL} ... (Waiting up to 90s for Render to wake up)")
            res = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=90)
            
            if res.status_code == 200:
                print(f"[+] Success! {file_path} was synced to Bhavya's DB.")
                os.remove(file_path) # Delete it so we don't send it again
            else:
                print(f"[-] Failed with status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[-] Exception: {e}")
