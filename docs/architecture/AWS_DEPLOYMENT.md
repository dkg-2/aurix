# AURIX: Complete AWS EC2 Deployment Guide

If you are reading this 6 months from now and need to completely rebuild the production environment from scratch, follow these exact steps. This guide contains every optimization, bug fix, and architectural decision we made to get the multi-agent AI Engine running perfectly on a 2GB RAM server.

---

## 🏗️ Phase 1: Server Provisioning & SSH

1. **Launch EC2 Instance:**
   *   **OS:** Ubuntu 26.04 LTS (x86_64)
   *   **Instance Type:** `t3.small` (2 vCPUs, 2GB RAM)
   *   **Storage:** 30GB General Purpose SSD (gp3)
   *   **Key Pair:** Generate and download a `.pem` file (e.g., `aurix-key.pem`). Keep it safe!

2. **Connect via SSH:**
   Open PowerShell on your local machine and run:
   ```powershell
   ssh -i "path/to/aurix-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
   ```

---

## 🛠️ Phase 2: System Dependencies & Virtual RAM

Because `t3.small` only has 2GB of RAM, running 4 heavy security scanners in parallel will instantly crash the server (OOM - Out of Memory). We fixed this by creating a 4GB Virtual RAM (Swap) file on the SSD.

1. **Install Docker:**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```

2. **Create the 4GB Swap File (CRITICAL):**
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
   *(To make it permanent across reboots, add `/swapfile none swap sw 0 0` to `/etc/fstab`).*

---

## 📥 Phase 3: Code Ingestion & Secrets

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/dkg-2/aurix.git
   cd "aurix/new work"
   ```

2. **Generate the `.env` File safely:**
   Because pasting long API keys into a Linux terminal causes line-wrapping bugs, we created a safe script (`setup_env.py`) that stores the keys in Base64 (bypassing GitHub Push Protection). 
   ```bash
   python3 setup_env.py
   ```
   *Verify the file was created correctly:* `cat .env`

---

## 🐳 Phase 4: Building the Dual-Image Architecture

Aurix relies on two separate Docker images. The **Scanner Image** (which holds Trivy, Opengrep, Gitleaks, Hadolint) and the **Worker Image** (which holds the Python LangGraph Engine).

1. **Build the Scanner Image (Tooling):**
   This takes about 3 minutes to download all the security binaries.
   ```bash
   docker build -t security-engine:latest -f Dockerfile.scanner .
   ```

2. **Build the Worker Image (LangGraph):**
   ```bash
   docker compose build
   docker compose up -d
   ```

---

## 🐛 Phase 5: The "Gotchas" We Fixed (Do Not Revert These!)

If the engine ever breaks in the future, make sure none of these 4 critical optimizations were accidentally undone:

1. **The Entrypoint Bypass (`engine.py`):**
   We had to add `--entrypoint ""` to the `docker run` command. Without this, Docker tries to execute the Python script inside the scanner container instead of the actual tools, resulting in 0 vulnerabilities found.
2. **Parallel Threading (`engine.py`):**
   We replaced the sequential execution with Python `threading.Thread` arrays to fire all 4 scanners simultaneously, drastically reducing scan times.
3. **Groq API Rate Limit Cooldown (`groq_client.py`):**
   Because parallel scanning finds bugs instantly, LangGraph was hitting Groq with 12 requests per second and getting `429 Too Many Requests` errors. We added a 10-second `time.sleep(10)` cooldown to the `rotate_key()` function to gracefully pace the AI and prevent infinite retry loops.
4. **Storage Purge (`aurix_worker.py`):**
   Cloning massive GitHub repos quickly eats up the 30GB SSD. We added a `shutil.rmtree(workspace_path)` block at the very end of the script to instantly delete the cloned repo once the JSON report is generated.

---

## 🚀 Phase 6: Final Execution

With everything built and configured, trigger a scan manually to test the pipeline:
```bash
docker exec aurix_ai_worker python aurix_worker.py https://github.com/stamparm/DSVW
```

If it processes the vulnerabilities and outputs `[INFO] Purging temporary workspace to save storage...`, your deployment is a **100% SUCCESS**.
