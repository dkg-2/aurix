# Backend API & Webhook Specifications (Bhavya)

Based on our `webDashboard-api-sequence-diagram`, Divyansh has completed the **Worker Node (AWS EC2)**. Your role is to build the **Backend API** that bridges the React Dashboard and the Worker Node.

**You do NOT need the AWS Private Key or SSH access.** Your backend will communicate with Divyansh's AWS server entirely through REST APIs and Redis queues.

---

## 🏗️ 1. Your Architecture Responsibilities
You need to build a backend server (e.g., Node.js/Express, FastAPI, or Django) that will be hosted on Render/Heroku. Your backend must connect to:
1. **Supabase (PostgreSQL)**: To store User data and Scan Histories.
2. **Upstash (Redis)**: To hold a queue of "Pending Scans".

---

## 📡 2. Endpoint 1: Receive Scan Requests from Frontend
You need to expose an endpoint for the React Dashboard to trigger a scan.

**`POST /api/scans/github`**
*   **Payload from React:** `{ "github_url": "https://github.com/..." }`
*   **What your backend must do:**
    1. Generate a unique `scan_id`.
    2. Save a new row in Supabase: `{ scan_id: "...", url: "...", status: "PENDING" }`.
    3. Push a JSON message into your Upstash Redis Queue containing the `url` and `scan_id`. *(Divyansh's AWS server will constantly poll this Redis queue in the background. When it sees a job, it pulls it and starts the AI scan).*
*   **Response to React:** `202 Accepted { "scan_id": "...", "status": "PENDING" }`

---

## 🎣 3. Endpoint 2: The Webhook Receiver
Divyansh's AI Engine takes 10–15 minutes to run 4 security tools, clone code, and run LangGraph AI Wargames. When it finishes, it will send the massive results payload to a specific URL on your backend.

**`POST /api/v1/scans/webhook`** *(You must build this endpoint!)*
*   **Authorization:** The AWS server will send a header: `Authorization: Bearer aurix-dev-token`. Ensure you validate this so random people can't submit fake scan results.
*   **Payload from AWS:** A massive JSON object containing `scan_id`, `summary`, and the `findings` array.
*   **What your backend must do:**
    1. Find the Supabase record using the `scan_id`.
    2. Update the row's `status` to `COMPLETED`.
    3. Save the JSON `findings` array into a JSONB column in Supabase (or into a NoSQL collection).
*   **Response to AWS:** `200 OK` (If your server crashes or returns 500, Divyansh's AWS server will save the report to a Dead Letter Queue and retry later).

> **Action Item for Bhavya:** Once you deploy this backend to Render (e.g., `https://bhavya-aurix-api.onrender.com`), send the full Webhook URL to Divyansh. He will paste it into the AWS `.env` file, and the two systems will be fully connected!
