# Aurix Team Onboarding & Development Guide

Welcome to the production environment! The Aurix AI Engine backend is now fully deployed on an AWS EC2 instance. It utilizes a highly optimized Docker-in-Docker architecture, parallel multi-tool scanning, and rate-limit-proof LangGraph API rotation.

This guide will show **Bhavya, Divyanshi, and Bhumika** how to access the server, run tests independently, and build out your specific components to connect to this engine.

---

## 🔐 1. How to Access the AWS Server

Because the server is secured, you cannot log in with a password. You must use the cryptographic private key.

1. **Get the Key:** Ask Divyansh to securely send you the `aurix-key.pem` file (via WhatsApp, Slack, etc.). *Do not upload this file to GitHub!*
2. **Open your Terminal:** (PowerShell on Windows, or Terminal on Mac/Linux).
3. **Connect to AWS:** Run the following command, replacing the path with wherever you saved the `.pem` file on your computer:
   ```bash
   ssh -i "C:\path\to\your\aurix-key.pem" ubuntu@65.0.134.65
   ```

---

## 🧪 2. How to Run a Test Scan Yourself

Once you see the green `ubuntu@ip...` terminal prompt, you are inside the cloud server! You can test the engine at any time to see how the AI processes code.

1. **Go to the project folder:**
   ```bash
   cd "aurix/new work"
   ```
2. **Trigger a scan:**
   ```bash
   docker exec aurix_ai_worker python aurix_worker.py https://github.com/stamparm/DSVW
   ```
   *(You can replace the URL with any public GitHub repository. The scan will clone the repo, find vulnerabilities in parallel, analyze them with Groq, save the JSON, and then automatically delete the cloned repo to save space).*

---

## 🚀 3. Next Steps & Component Development

The core AI engine is finished, but it currently only runs when someone types a command into the terminal. Here is how the rest of the team needs to connect their components:

### 👩‍💻 Bhavya: API Wrapper & Webhooks
Your primary goal is to connect the Next.js Frontend to this AWS backend.
*   **The API Trigger:** You need to write a simple Python web server (like FastAPI or Flask) inside the `new work` folder. This API should listen for an HTTP POST request from your Frontend (e.g., `POST /scan { "url": "..." }`). When it receives that request, it should programmatically trigger `worker.run_full_audit(url)` in the background.
*   **The Webhook Listener:** Because AI scans take 10 to 15 minutes, the Frontend cannot wait for a response. The AWS engine is currently configured to send a massive JSON payload to a "Webhook" when it finishes. You need to build a webhook receiver endpoint on your backend to catch this JSON and save it to the database. *(Tell Divyansh when this URL is ready so he can update the AWS `.env` file).*

### 👩‍🎨 Divyanshi & Bhumika: Database & UI Architecture
Your primary goal is to store and display the results that the AWS Engine generates.
*   **Database Schema:** The AWS Engine outputs a highly detailed JSON report. It includes arrays of vulnerabilities with fields like `title`, `severity`, `file`, `line`, and the AI's `wargame_status` (e.g., "Neutralized" or "Verified"). You need to design a MongoDB or PostgreSQL database schema capable of storing these scan histories so users can view past scans.
*   **Frontend Dashboard:** You need to design the UI components that will display this data. Look at the `verified-results` JSON files that the engine generates to see exactly what data you have to work with. You will need a dashboard showing total vulnerabilities, a list of files affected, and the AI's patch recommendations.

---

## 🔄 4. The Cloud Deployment Workflow

When any of you write new code (like the FastAPI wrapper):
1. Write and test your code locally on your own computers.
2. Push your code to the `main` branch on GitHub.
3. SSH into the AWS server (using the steps in Part 1).
4. Run these commands to deploy your new code to production:
   ```bash
   cd "aurix/new work"
   git pull
   docker compose up -d --build
   ```
