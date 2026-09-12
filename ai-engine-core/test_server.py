"""
AURIX Test Server — Lightweight Flask app for testing the AI Engine end-to-end.
Runs on the same AWS instance as the engine. Serves a web dashboard at port 5000.

Endpoints:
  GET  /                        → Test Dashboard UI
  POST /api/test/scan-url       → Submit a repo URL for scanning
  POST /api/test/scan-zip       → Upload a zip file for scanning
  GET  /api/test/status/<id>    → Check if a scan is done
  GET  /api/test/results/<id>   → Download the full JSON report
"""

import os
import json
import uuid
import time
import redis
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_file

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
QUEUE_NAME = "aurix_scan_queue"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "verified-results")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "workspace", "uploads")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

r = redis.from_url(REDIS_URL, decode_responses=True)

# ──────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────

@app.route("/api/test/scan-url", methods=["POST"])
def scan_url():
    """Submit a GitHub repo URL for scanning."""
    data = request.json
    repo_url = data.get("url")
    if not repo_url:
        return jsonify({"error": "Missing 'url' field"}), 400

    scan_id = str(uuid.uuid4())
    payload = {
        "scan_id": scan_id,
        "url": repo_url,
        "timestamp": time.time(),
        "source": "test_dashboard"
    }
    r.lpush(QUEUE_NAME, json.dumps(payload))

    return jsonify({
        "scan_id": scan_id,
        "status": "QUEUED",
        "message": f"Scan queued for {repo_url}"
    })


@app.route("/api/test/scan-zip", methods=["POST"])
def scan_zip():
    """Upload a zip file for scanning."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".zip"):
        return jsonify({"error": "Only .zip files are accepted"}), 400

    scan_id = str(uuid.uuid4())
    upload_path = os.path.join(UPLOAD_DIR, f"{scan_id}.zip")
    file.save(upload_path)

    payload = {
        "scan_id": scan_id,
        "storage_path": upload_path,
        "timestamp": time.time(),
        "source": "test_dashboard_zip"
    }
    r.lpush(QUEUE_NAME, json.dumps(payload))

    return jsonify({
        "scan_id": scan_id,
        "status": "QUEUED",
        "message": f"Zip uploaded and scan queued"
    })


@app.route("/api/test/status/<scan_id>", methods=["GET"])
def scan_status(scan_id):
    """Check if a scan report is ready."""
    report_path = os.path.join(RESULTS_DIR, f"verified_report_{scan_id}.json")
    if os.path.exists(report_path):
        # Read the summary without loading the entire file
        with open(report_path, "r") as f:
            report = json.load(f)
        summary = report.get("summary", {})
        return jsonify({
            "scan_id": scan_id,
            "status": "COMPLETED",
            "summary": summary
        })
    else:
        return jsonify({
            "scan_id": scan_id,
            "status": "PROCESSING"
        })


@app.route("/api/test/results/<scan_id>", methods=["GET"])
def scan_results(scan_id):
    """Download the full JSON report."""
    report_path = os.path.join(RESULTS_DIR, f"verified_report_{scan_id}.json")
    if os.path.exists(report_path):
        return send_file(report_path, mimetype="application/json")
    else:
        return jsonify({"error": "Report not found. Scan may still be processing."}), 404


# ──────────────────────────────────────────────
# WEB DASHBOARD (Single HTML Page)
# ──────────────────────────────────────────────

@app.route("/")
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AURIX — Test Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            font-size: 2.2rem;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle { color: #888; margin-bottom: 40px; font-size: 0.95rem; }

        .card {
            background: #14141f;
            border: 1px solid #2a2a3a;
            border-radius: 12px;
            padding: 28px;
            margin-bottom: 24px;
        }
        .card h2 { font-size: 1.1rem; color: #00d4ff; margin-bottom: 16px; }

        label { display: block; font-size: 0.85rem; color: #aaa; margin-bottom: 6px; }
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 12px 16px;
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 0.95rem;
            margin-bottom: 16px;
            outline: none;
        }
        input[type="text"]:focus { border-color: #00d4ff; }
        input[type="file"] { cursor: pointer; }

        button {
            padding: 12px 28px;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            border: none;
            border-radius: 8px;
            color: #fff;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.85; }
        button:disabled { opacity: 0.4; cursor: not-allowed; }

        #status-panel {
            display: none;
            background: #14141f;
            border: 1px solid #2a2a3a;
            border-radius: 12px;
            padding: 28px;
            margin-top: 24px;
        }
        .status-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
        .spinner {
            width: 20px; height: 20px;
            border: 3px solid #333;
            border-top: 3px solid #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-text { font-weight: 600; }
        .status-text.processing { color: #ffa500; }
        .status-text.completed { color: #00ff88; }

        #scan-id-display { font-family: monospace; color: #888; font-size: 0.85rem; margin-bottom: 12px; }

        #summary-box {
            display: none;
            background: #1a1a2e;
            border-radius: 8px;
            padding: 20px;
            margin-top: 16px;
        }
        .summary-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2a2a3a; }
        .summary-row:last-child { border: none; }
        .summary-label { color: #aaa; }
        .summary-value { font-weight: 600; color: #fff; }
        .summary-value.red { color: #ff4444; }
        .summary-value.green { color: #00ff88; }

        #download-btn {
            display: none;
            margin-top: 16px;
            background: linear-gradient(135deg, #00ff88, #00d4ff);
            color: #000;
        }

        .or-divider { text-align: center; color: #555; margin: 20px 0; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ AURIX Test Dashboard</h1>
        <p class="subtitle">Submit a repository or zip file to test the AI Security Engine end-to-end.</p>

        <!-- Scan by URL -->
        <div class="card">
            <h2>🔗 Scan by Repository URL</h2>
            <label>GitHub Repository URL</label>
            <input type="text" id="repo-url" placeholder="https://github.com/owner/repo.git">
            <button onclick="submitUrl()">🚀 Start Scan</button>
        </div>

        <div class="or-divider">— OR —</div>

        <!-- Scan by Zip Upload -->
        <div class="card">
            <h2>📦 Scan by Zip Upload</h2>
            <label>Select a .zip file of your project</label>
            <input type="file" id="zip-file" accept=".zip">
            <button onclick="submitZip()">📤 Upload & Scan</button>
        </div>

        <!-- Status Panel -->
        <div id="status-panel">
            <div class="status-header">
                <div class="spinner" id="spinner"></div>
                <span class="status-text processing" id="status-text">Processing...</span>
            </div>
            <div id="scan-id-display"></div>
            <div id="elapsed-time" style="color:#888; font-size:0.85rem;"></div>

            <div id="summary-box">
                <div class="summary-row">
                    <span class="summary-label">Total Findings</span>
                    <span class="summary-value" id="s-total">-</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">Exploitable</span>
                    <span class="summary-value red" id="s-exploitable">-</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">Neutralized</span>
                    <span class="summary-value green" id="s-neutralized">-</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">Scan Time</span>
                    <span class="summary-value" id="s-time">-</span>
                </div>
            </div>

            <button id="download-btn" onclick="downloadReport()">📥 Download Full JSON Report</button>
        </div>
    </div>

    <script>
        let currentScanId = null;
        let pollTimer = null;
        let startTime = null;
        let elapsedTimer = null;

        function showStatus(scanId) {
            currentScanId = scanId;
            startTime = Date.now();
            document.getElementById('status-panel').style.display = 'block';
            document.getElementById('scan-id-display').textContent = 'Scan ID: ' + scanId;
            document.getElementById('status-text').textContent = 'Processing...';
            document.getElementById('status-text').className = 'status-text processing';
            document.getElementById('spinner').style.display = 'block';
            document.getElementById('summary-box').style.display = 'none';
            document.getElementById('download-btn').style.display = 'none';

            // Start elapsed timer
            elapsedTimer = setInterval(() => {
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                document.getElementById('elapsed-time').textContent = 'Elapsed: ' + elapsed + 's';
            }, 1000);

            // Start polling every 5 seconds
            pollTimer = setInterval(checkStatus, 5000);
        }

        async function submitUrl() {
            const url = document.getElementById('repo-url').value.trim();
            if (!url) return alert('Please enter a repository URL');

            const res = await fetch('/api/test/scan-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            showStatus(data.scan_id);
        }

        async function submitZip() {
            const fileInput = document.getElementById('zip-file');
            if (!fileInput.files.length) return alert('Please select a zip file');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const res = await fetch('/api/test/scan-zip', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            showStatus(data.scan_id);
        }

        async function checkStatus() {
            if (!currentScanId) return;

            const res = await fetch('/api/test/status/' + currentScanId);
            const data = await res.json();

            if (data.status === 'COMPLETED') {
                clearInterval(pollTimer);
                clearInterval(elapsedTimer);

                document.getElementById('status-text').textContent = '✅ Scan Complete!';
                document.getElementById('status-text').className = 'status-text completed';
                document.getElementById('spinner').style.display = 'none';

                // Show summary
                const s = data.summary;
                document.getElementById('s-total').textContent = s.total_findings || 0;
                document.getElementById('s-exploitable').textContent = s.exploitable_count || 0;
                document.getElementById('s-neutralized').textContent = s.neutralized_count || 0;
                document.getElementById('s-time').textContent = (s.elapsed_seconds || 0) + 's';
                document.getElementById('summary-box').style.display = 'block';
                document.getElementById('download-btn').style.display = 'inline-block';
            }
        }

        function downloadReport() {
            if (currentScanId) {
                window.open('/api/test/results/' + currentScanId, '_blank');
            }
        }
    </script>
</body>
</html>"""


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║   AURIX Test Dashboard Server                   ║")
    print("║   Open in browser: http://YOUR_AWS_IP:5000      ║")
    print("╚══════════════════════════════════════════════════╝")
    app.run(host="0.0.0.0", port=5000, debug=False)
