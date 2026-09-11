# AWS Production Server Cheatsheet

This document contains everything you need to know to access your AWS EC2 server, test the Aurix AI Engine, and hand off the project to the rest of your team.

---

## 🚀 Part 1: How to Access & Test the Server (Without Help!)

Whenever you want to check on the server, update the code, or run a manual test scan, just follow these exact steps from your Windows laptop.

### 1. Log into the Server
Open a Windows PowerShell terminal and run your SSH command. This uses your private `.pem` key to securely log into the AWS cloud instance:
```powershell
ssh -i "D:\DG BTECH\DG PROJECTS\FINAL YEAR PROJECT\new work\aurix-key.pem" ubuntu@65.0.134.65
```

### 2. Go to the Project Directory
Once you see the green `ubuntu@ip...` prompt, navigate into your deployed codebase:
```bash
cd "aurix/new work"
```

### 3. Update the Code (If you made changes on GitHub)
If you or your team pushes new code to GitHub, you need to pull it onto the server and rebuild the Docker container so the changes take effect:
```bash
git pull
docker compose build
docker compose up -d
```

### 4. Run a Manual Test Scan
To fire off a security audit on any public GitHub repository, just execute the worker script inside the running Docker container:
```bash
docker exec aurix_ai_worker python aurix_worker.py https://github.com/stamparm/DSVW
```
*(Replace the URL at the end with any repository you want to scan).*

### 5. Monitor Server Health
If the server ever feels slow or you want to make sure your 30GB hard drive isn't full, run these two commands:
```bash
# Check overall hard drive space
df -h /

# Wipe out unused Docker caches to instantly free up space
docker system prune -a -f
```

---

## 🤝 Part 2: What to Prepare for the Team (Handoff to Bhavya)

Now that the AI Engine is fully operational on AWS, your backend/UI team (Bhavya) needs to connect to it. Here is what you need to tell them:

### 1. The Server IP
Give Bhavya the public IP address of your AWS server: **`65.0.134.65`**

### 2. The Next Step (Creating the API Endpoint)
Currently, the AI Engine runs via a terminal command (`docker exec...`). For Bhavya's Next.js frontend or backend to trigger a scan automatically, she cannot type terminal commands. 
**Action Item:** The team needs to write a tiny `FastAPI` script (e.g., `server.py`) that runs inside the Docker container. This script will listen on a port (like `8000`) for incoming HTTP POST requests from Bhavya's UI, and then automatically trigger `worker.run_full_audit(url)`.

### 3. The Webhook Destination
When the AI Engine finishes a 15-minute scan, it needs somewhere to send the massive JSON report. 
**Action Item:** Bhavya needs to provide you with a **Webhook URL** (an endpoint on her backend). Once she gives it to you, you will run the `setup_env.py` script again on the AWS server to update the `.env` file with her exact URL. Until then, the engine will safely save all reports to the `pending-sync/` folder on the AWS server so they are never lost.

---
**Deployment Status:** SUCCESS ✅
**Environment:** AWS EC2 t3.small (2GB RAM, 30GB SSD)
**Architecture:** Dockerized Multi-Agent LangGraph System
