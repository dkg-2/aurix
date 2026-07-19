# AURIX - Asynchronous Architecture & Data Flow

**Target Audience:** Full Stack Development Team (Divyansh, Bhavya, Bhumika, Divyanshi)
**Purpose:** To clearly define how the AI Engine interacts with the FastAPI Backend and React Frontend, and why we have chosen an asynchronous, decoupled microservice architecture.

---

## 1. The Architectural Challenge
The AURIX AI Engine performs heavy operations: it clones repositories, runs 4 separate Dockerized security scanners (Opengrep, Trivy, Gitleaks, Hadolint), and then executes a LangGraph pipeline connecting multiple LLM agents (Red Agent, Blue Agent, Logic Agent) with a local Sandbox.

**The Constraints:**
*   **Time:** A full audit takes between **3 to 5 minutes** (potentially up to 10 minutes for massive codebases).
*   **Compute:** Running multiple Docker containers concurrently causes RAM spikes (600MB - 800MB peak).

**Why we cannot use standard REST:**
If the Frontend sends a standard HTTP request to the Backend, and the Backend waits for the AI Engine to finish before responding, the HTTP connection will remain open for 5 minutes. The browser will time out, the connection will drop, and the user's screen will crash. 

---

## 2. The Solution: The "Webhook Handoff"
To solve this, we have fully decoupled Divyansh's AI Engine from Bhavya's FastAPI Backend. They are now separate Microservices that communicate asynchronously via a **Webhook**.

### Step-by-Step Data Flow

1. **User Initiation (Frontend - Bhumika):**
   * The user clicks "Start Scan" and provides a GitHub URL on the dashboard.
   
2. **Instant Acknowledgement (Backend - Bhavya):**
   * The FastAPI backend receives the request, writes a new `PENDING` scan record to the database, and **instantly** responds to the Frontend with a `202 Accepted` status and a `scan_id`. 
   * *Result:* The Frontend does not freeze. It immediately shows the user a "Scan in Progress" loading UI.

3. **Background Trigger (Backend -> AI Engine):**
   * The Backend silently triggers the AI Engine in the background, passing the GitHub URL and `scan_id`.

4. **The Heavy Lifting (AI Engine - Divyansh):**
   * The Engine runs independently for 3-5 minutes, churning through the scanners and the LangGraph Reflexion loop.

5. **The Webhook POST (AI Engine -> Backend):**
   * Once the engine finishes the final report, it fires an HTTP `POST` request to Bhavya's dedicated Webhook endpoint (e.g., `/api/v1/scans/webhook`) containing the massive JSON payload defined in the `API_CONTRACT.md`.
   * *Resilience:* If the Backend is down, the AI Engine catches the error and saves the payload to a local `pending-sync/` Dead-Letter Queue (DLQ) to ensure zero data loss.

6. **Database Update (Backend - Bhavya):**
   * The Webhook endpoint receives the JSON, validates the `AURIX_WEBHOOK_TOKEN`, and updates the database record from `PENDING` to `COMPLETED`.

7. **User Notification (Frontend - Bhumika):**
   * Because the Frontend has been quietly polling the Backend every 10 seconds (or listening via WebSockets), it notices the status change to `COMPLETED` and pops up a notification for the user to view their results.

---

## 3. Production Deployment Strategy
Because we need to run "Docker-in-Docker" (the AI Engine must spawn the Sandbox containers dynamically), we cannot use standard serverless platforms. The system must be deployed on a Virtual Private Server (VPS).

### Hardware & Compute Requirements
*   **Oracle Cloud (Always Free ARM):** Highly recommended. Provides up to 24GB RAM and 4 CPUs. This allows the 4 initial scanners to run in parallel using multi-threading for maximum speed.
*   **AWS EC2 / GCP (1GB RAM Free Tier):** If using these smaller servers, we **must** configure a 2GB-4GB Swap File on the SSD to act as virtual RAM. Furthermore, we must update the AI Engine to run the 4 scanners *sequentially* (one by one) rather than multi-threaded, keeping peak RAM usage below 800MB to avoid Linux Kernel crashes (OOM Killer).

---

## 4. Team Action Items

*   **Bhavya (Backend):** Build the `/api/v1/scans/webhook` endpoint. It must accept a POST request, verify the Bearer token, and parse the JSON schema matching `API_CONTRACT.md`. 
*   **Bhumika (Frontend):** Ensure the UI is fully asynchronous. When a scan starts, direct the user to a loading screen that either polls the backend `GET /scan/{id}/status` or listens for a WebSocket event.
*   **Divyansh (AI Engine):** Ensure the `.env` file is properly configured on the production server (with `HOST_WORKSPACE_DIR` for Docker path mapping) so the Webhook has the correct target URL to "phone home" to.
