# AURIX - Claude Interview Prep Reply

Here are all the detailed, technical answers based exactly on what we built and deployed for the AURIX architecture over the last few weeks:

### **AWS Deployment:**
1. **What exactly is running on the t3.small?** 
The full pipeline! There is **no FastAPI layer on this server** (Bhavya handles the API on her Render backend). This EC2 instance runs the `queue_listener.py` daemon, which pulls jobs from Upstash Redis and spawns the full LangGraph AI Engine, raw SAST scanners, and the Docker sandboxes.
2. **What OS is on the EC2 instance?** 
Ubuntu 22.04 LTS. We also manually configured a 4GB Swap file to prevent Out-Of-Memory (OOM) crashes during heavy multi-layered scanning.
3. **How are you keeping the server running?** 
We use `nohup python3 -u queue_listener.py > queue_listener.log 2>&1 &` to run the queue listener as a persistent background daemon.
4. **How is it accessed?** 
Raw public IP (`65.0.134.65`) accessed via SSH using a private `.pem` key.
5. **Which ports are open in the Security Group?** 
**Only Port 22 (SSH).** Because of our Decoupled Architecture, the AWS worker only makes *outbound* requests (pulling from Redis, pushing to the Render Webhook). It doesn't need to listen for inbound HTTP traffic, making it highly secure against external attacks.
6. **How are secrets managed on the server?** 
A local `.env` file. We built a custom `setup_env.py` script that safely generates this file on the AWS host, dynamically inserting base64-encoded LLM keys and writing the absolute Ubuntu host directory paths (`/home/ubuntu/aurix/new work/workspace`).
7. **Is Docker also running on the EC2?** 
Yes! We use a highly advanced **Docker-in-Docker (DinD)** architecture. The main LangGraph orchestrator runs inside a Docker container (`aurix_ai_worker`). We volume-mount `/var/run/docker.sock` into it, allowing the AI engine to programmatically spawn *more* containers on the host machine to run the SAST tools (Opengrep, Trivy) and the ephemeral exploit sandboxes.

### **Dockerfile:**
8. **What is the Dockerfile for?** 
We actually have two layers: `Dockerfile.engine` (which installs Python, LangGraph, Groq, and Redis dependencies for the orchestrator) and `docker-compose.yml` (which wires up the socket mounts). We also use a `security-engine:latest` image to isolate the execution of Opengrep, Trivy, Hadolint, and Gitleaks.
9. **What tools/packages are installed inside it?** 
`langgraph`, `docker` (Python SDK), `redis`, `requests`, `python-dotenv`, `groq`, etc.
10. **Did you build and push it to AWS ECR?** 
It is built locally on the EC2 instance. We `git pull` the code directly from GitHub and run `docker compose up -d --build`.

### **Local Path Audit:**
11. **What did you change to support local paths?** 
Upgraded `engine.py` into a **Dual-Ingestion Pipeline**. Instead of just doing `git clone`, it inspects the incoming target URL. If it ends in `.zip` or contains `storage`, it uses Python's `urllib` and `zipfile` modules to dynamically download the zipped workspace from Bhavya's Cloud Storage (which was uploaded by Divyanshi's VS Code extension) and extracts it directly into the scan workspace.
12. **Did you actually test it?** 
Yes! We tested the full pipeline on `Vulnerable-Flask-App` (101 findings) and `Hello-World` to verify that the dynamic parsing and webhook delivery works flawlessly.

### **New Code / Repo Updates:**
13. **Are there any new Python files in the repo?** 
Yes! 
- `queue_listener.py` (The Upstash Redis async polling daemon).
- `setup_env.py` (For automated AWS environment configuration).
- `test_trigger.py` (Mock client to push jobs to the cloud queue).
- `retry_dlq.py` (A Dead Letter Queue script to retry failed webhook payloads).
14. **Did you wire the RAG node into the graph?** 
Not yet. Waiting for Bhavya to finish the RAG Threat Intel API (pgvector).
15. **Did you add network_mode='none' to the sandbox?** 
Yes, the ephemeral sandboxes used by the Red Agent are strictly network-isolated.
16. **Did you add a README.md?** 
Yes, we added extensive documentation in the `docs/` folder: `ABSTRACT.md` (FYP Diary abstract), `AWS_DEPLOYMENT.md`, `AWS_SERVER_CHEATSHEET.md`, and `LOCAL_TESTING_GUIDE.md`.
17. **Are there new verified-results JSON files?** 
Yes! Tested against `Vulnerable-Flask-App` which processed 101 findings and successfully mapped them to the `API_CONTRACT.md` JSON schema.

### **Resume Impact:**
18. **Can you now say the engine is "deployed and live on AWS EC2"?** 
**100% YES.** It is a production-grade, 24/7 background daemon pulling live jobs from an Upstash Redis cloud queue and delivering results to a live Render backend.
19. **Any new metrics?** 
- **Resilience Metrics:** Implemented a **9-key dynamic API rotation pool** with exponential backoffs to completely bypass LLM rate limit crashes.
- **Webhook Metrics:** Implemented 90-second timeout handling to account for Render's "Cold Starts", plus a Dead Letter Queue that saves failed JSON payloads locally (`pending-sync/`) so data is never lost.
- Successfully processed 101 vulnerabilities in a single pass (`Vulnerable-Flask-App`).
