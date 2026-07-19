# Frontend Dashboard & VS Code Extension Specs (Bhumika & Divyanshi)

Based on the `webDashboard-api-sequence-diagram` and `vscode-extension-api-sequence-diagram`, Divyansh has finished building the core AI Worker Node on AWS. 

Your role is to design and develop the user-facing platforms that display the results from this AI Engine:
1. **The Web Dashboard (React/Next.js)**
2. **The VS Code Extension**

To build these, you don't need AWS access. You only need to understand the exact structure of the **Final JSON Report** that the AI Engine generates, so you can build React components (like graphs, tables, and code viewers) to display this data.

---

## 📊 The JSON Output Schema

When a user scans a repository, Bhavya's backend will eventually pass this exact JSON structure to your frontend. You should mock this JSON in your React app right now to start building the UI!

```json
{
  "scan_id": "829fcec8-6b82-4f94-a794-35ebf4e222cb",
  "url": "https://github.com/stamparm/DSVW",
  "timestamp": "2026-07-19T14:42:00.000Z",
  "summary": {
    "total_findings": 12,
    "neutralized_count": 8,
    "scan_engine": "Project AURIX LangGraph v1"
  },
  "findings": [
    {
      "id": "vuln-uuid-1234",
      "category": "sast",
      "title": "SQL Injection Warning",
      "file": "database/queries.py",
      "line": 42,
      "severity": "CRITICAL",
      
      // The Raw output from the security scanner (Trivy/Opengrep)
      "raw_message": "User input is directly interpolated into SQL string.",
      
      // Below are the AI-Enriched fields (The LangGraph Engine adds these!)
      "verified": true,
      
      // Can be: "Neutralized" (Patch works), "Verified" (Real bug, patch failed), or "Unverified"
      "wargame_status": "Neutralized", 
      
      "ai_analysis": "The Red Agent successfully exploited this parameter by injecting `1=1`. This allows complete database bypass.",
      
      "patch": "```python\n# Use parameterized queries instead\ncursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n```"
    }
  ]
}
```

---

## 💻 What You Need to Build

Although you share the same JSON output from the AI Engine, your roles operate in completely different domains.

### 🌐 Bhumika (Web Dashboard Developer)
*Reference: `Role Doc for Bhumika.pdf`*

Your job is to build the primary visual "Face" of AURIX using React/Next.js. You will consume the JSON output above from Bhavya's backend to build:
*   **Dual-Mode Ingestion UI:** A form to paste a GitHub URL (which triggers Bhavya's API) and a GitHub OAuth flow to list repositories.
*   **Results Dashboard (Kanban):** Map the `findings` array into a Kanban board where users can filter vulnerabilities by `severity` and sort them by `wargame_status` (Open, Resolved, Ignored).
*   **Contextual AI Chat Assistant:** A slide-out panel that uses the `ai_analysis` text to allow users to ask follow-up questions about the specific vulnerability.
*   **One-Click Pull Requests:** A "Remediate" button that takes the `patch` string and automatically branches the user's GitHub repository via the GitHub REST API.
*   **Blocker Note:** You are blocked by Bhavya. Ask her for a mock API endpoint immediately so you can start building the polling logic and Kanban board!

### ⚙️ Divyanshi (IDE & Integration Engineer)
*Reference: `Role Doc for Divyanshi.pdf`*

Your job is to bring AURIX directly into the developer's local machine by building the VS Code Extension.
*   **Zip & Ship Logic:** You must write the local file-system logic to zip the developer's workspace and POST it to Bhavya's API. *Crucial:* You must enforce `.gitignore` rules to prevent zipping massive `node_modules` folders, which will crash the AI Engine!
*   **Editor UI Diagnostics:** Once your polling loop receives the JSON report above, use the VS Code Diagnostics API. Parse the `file` and `line` fields to underline the exact vulnerable code with red squiggly lines in the user's editor.
*   **"Quick Fix" Auto-Patcher:** Implement the `CodeActionProvider`. When a user clicks the yellow lightbulb over the red squiggly line, take the `patch` string from the JSON and safely inject the fix directly into their local file!
*   **Blocker Note:** You are also blocked by Bhavya for the upload endpoints, but you MUST coordinate with Divyansh! The `.zip` file your extension uploads must unzip into a folder structure that exactly matches what Divyansh's AI Engine expects to scan.
