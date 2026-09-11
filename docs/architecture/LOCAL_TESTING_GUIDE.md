# Local Testing Guide for AURIX AI Engine

Before deploying updates to the AWS production server, you may want to test the LangGraph engine locally against new vulnerable repositories to see how the Red and Blue Agents perform.

Because you have fully containerized the engine (Docker-in-Docker), testing locally is incredibly easy and mirrors the production environment exactly.

---

## 🛠️ Step 1: Prepare Your Environment

1. Ensure **Docker Desktop** is open and running on your Windows machine.
2. Open PowerShell and navigate to your working directory:
   ```powershell
   cd "D:\DG BTECH\DG PROJECTS\FINAL YEAR PROJECT\new work"
   ```

## 🏗️ Step 2: Build and Start the Local Containers

Just like on the AWS server, you need to spin up the local worker node. If you have made any changes to the Python code (`aurix_graph.py`, `engine.py`, etc.), make sure to run the build command first.

```powershell
# Rebuild the LangGraph worker image (if you changed Python code)
docker compose build

# Start the worker container in the background
docker compose up -d
```

## 🚀 Step 3: Trigger a Manual Scan

To test the engine, you don't need Bhavya's Redis Queue. You can manually force the worker container to scan a new repository by passing the GitHub URL directly.

Here are a few great intentionally vulnerable repositories you can test against:
*   **Vulnerable Flask App:** `https://github.com/we45/Vulnerable-Flask-App`
*   **WebGoat (Java/Spring):** `https://github.com/WebGoat/WebGoat`
*   **NodeGoat (Node.js):** `https://github.com/OWASP/NodeGoat`

Run this command in PowerShell to trigger the scan (replace the URL with your target):

```powershell
docker exec aurix_ai_worker python aurix_worker.py https://github.com/we45/Vulnerable-Flask-App
```

## 📊 Step 4: Review the Results

Once the scan finishes (it may take a few minutes depending on the repository size and Groq API rate limits):

1. The engine will automatically generate a JSON report.
2. Because of your Docker volume mounts, the report will instantly appear on your local Windows machine inside the `new work/verified-results/` folder.
3. Open the generated `verified_report_<uuid>.json` file in VS Code.
4. Check the `wargame_status`, `poc_script`, and `patch_code` fields to analyze how well the Red and Blue Agents performed against the new vulnerabilities!

## 🧹 Step 5: Clean Up

When you are done testing for the day, you can shut down the local worker container to free up your computer's RAM:

```powershell
docker compose down
```

---

## ⚠️ Step 6: Reverting to Cloud-Friendly Paths (Before AWS Deploy)

Because `engine.py` uses Docker-in-Docker volume mounting, the `HOST_WORKSPACE_DIR` path passed to the inner scanners must be an **absolute host path**.

If you change the `.env` file or `docker-compose.yml` for local Windows testing, you **must revert** them to the AWS Ubuntu paths before pushing your code to GitHub, or the cloud engine will crash!

### 1. Revert `.env` (The Host Path)
On your Windows machine, your `.env` file uses forward slashes (to avoid `\n` newline parsing bugs):
*   **Local:** `HOST_WORKSPACE_DIR="D:/DG BTECH/DG PROJECTS/FINAL YEAR PROJECT/new work/workspace"`
*   **AWS Cloud:** `HOST_WORKSPACE_DIR="/home/ubuntu/aurix/new work/workspace"`

### 2. Revert `docker-compose.yml` (The Volume Mount)
To ensure the container can see the exact same absolute path on AWS:
*   **Local:** `- ./workspace:/app/workspace`
*   **AWS Cloud:** `- "/home/ubuntu/aurix/new work/workspace:/app/workspace"`

*(Note: We highly recommend keeping `setup_env.py` configured with the Ubuntu paths, so running it on the AWS server automatically generates the correct `.env`!)*
