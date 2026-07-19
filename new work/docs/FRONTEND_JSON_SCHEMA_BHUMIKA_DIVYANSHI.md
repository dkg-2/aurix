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

### 1. The Web Dashboard (Bhumika/Divyanshi)
Using the JSON above, you need to build a sleek React dashboard:
*   **Header:** Display the `url`, the `timestamp`, and the `summary` metrics (e.g., "12 Total Bugs Found", "8 Successfully Patched by AI").
*   **Vulnerability Table:** A list rendering the `findings` array. Columns should include `Title`, `Severity`, `File`, and `Wargame Status`.
*   **AI Attack/Defense Viewer:** When a user clicks a row in the table, open a modal or side-panel showing the `ai_analysis` text, and render the `patch` inside a nice syntax-highlighted code block!

### 2. The VS Code Extension
The extension will pull this exact same JSON.
*   **Inline Squigglies:** The extension should read `file` and `line` (e.g., `database/queries.py`, line 42) and highlight that exact line in the developer's VS Code editor.
*   **Hover Action:** When the developer hovers over the highlighted line, a popup should display the `ai_analysis` and offer a "1-Click Apply Fix" button that automatically injects the `patch` string into their file!

> **Action Item for Frontend Team:** You can copy the JSON snippet above into a file named `mock_data.json` in your React project today. Start building the UI and passing this mock data into your components. When Bhavya finishes the backend API, you will just swap the mock file out for a real `fetch()` request!
