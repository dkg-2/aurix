# Final Year Project Progress Diary (BCS-753)
**Project Title:** AURIX: AI-Powered Automated Security Vulnerability Scanning and Intelligent Context-Aware Auto-Patching VS Code IDE Extension  
**Project ID:** PSIT-AI-2026-08  
**Team Members:** Divyansh (Core Engine Architect), Bhumika (Web Frontend Developer), Bhavya (Backend & Infrastructure Engineer), Divyanshi (VS Code IDE Extension Developer)  
**Academic Session:** 2026-27 (Odd Semester)  

---

### **WEEK 1**
**Work Done in Current Week:**
*   **Architecture & Backend:** Scaffolded the overall system architecture. Provisioned cloud infrastructure using Supabase (Free Tier) and Upstash (Serverless Redis). Executed SQL schemas for core relational tables (USERS, PROJECTS, SCANS) including Foreign Key mapping.
*   **Web Frontend:** Initialized a Next.js/React application with Tailwind CSS for rapid styling. Scaffolded the primary "Door" (Auth UI) creating `<LoginForm />` and `<SignUpForm />` components.
*   **IDE Extension:** Studied the AURIX High-Level Design (HLD) document. Scaffolded the extension core template infrastructure using the 'yo code' TypeScript environment generator.
*   **AI Core Engine:** Set up the LangGraph orchestrator blueprint. Drafted the foundational Python script for the Triage Node to pull initial jobs from the Redis queue.

**Work to be Done in Next Week:**
Configure authentication across the entire stack. Implement mock API endpoints on the backend and prepare the local environment for AI context ingestion and file packaging.

---

### **WEEK 2**
**Work Done in Current Week:**
*   **Architecture & Backend:** Configured Supabase "The Vault" with Email/Password and GitHub OAuth.
*   **Web Frontend:** Wrote the logic to POST credentials to the backend and securely save the returned session token (JWT) in localStorage/secure cookies.
*   **IDE Extension:** Successfully implemented the 'Aurix: Login' command infrastructure. Integrated the native VS Code SecretStorage framework to securely cache and persist JWTs across active developer sessions.
*   **AI Core Engine:** Designed the Semantic Slicer using Abstract Syntax Trees (AST) to trace execution paths across multiple files, ensuring the AI receives rich "Semantic Slices" rather than naive code chunks.

**Work to be Done in Next Week:**
Initialize the backend server, engineer the local workspace packager module for the IDE, build the ingestion UI for the web app, and integrate local Vector DBs for RAG intelligence.

---

### **WEEK 3**
**Work Done in Current Week:**
*   **Architecture & Backend:** Initialized Node.js Express server. Developed mock endpoints (POST /api/scans/github and /upload) returning 202 Accepted status to unblock parallel frontend and extension development.
*   **Web Frontend:** Built a flexible, authenticated Dual-Mode Ingestion UI allowing users to paste a GitHub Repository URL or use a native dropdown of owned repositories via the GitHub REST API.
*   **IDE Extension:** Built the Workspace Packager engine using recursive file-system walks. Integrated standard '.gitignore' parsing logic to respect project rules and preserve folder hierarchies.
*   **AI Core Engine:** Integrated a local Vector DB (ChromaDB) to ground the AI's reasoning. Formulated the schema for the AurixState Python TypedDict to act as shared memory across LangGraph nodes.

**Work to be Done in Next Week:**
Enforce hard blocklists for file packaging, implement API polling loops on the frontend, develop local credential screening in the IDE, and build the Consensus Gate for the AI.

---

### **WEEK 4**
**Work Done in Current Week:**
*   **Architecture & Backend:** Developed GET /api/scans/{scan_id} mock endpoint returning schema-compliant JSON. Deployed Express server to Render/Railway for teammate access.
*   **Web Frontend:** Implemented the async polling mechanism using SWR/fetch to call the GET endpoint every 5 seconds, updating a dynamic progress bar as status changes (PENDING -> SCANNING -> COMPLETED).
*   **IDE Extension:** Developed selective and delta scanning paths ('Aurix: Scan Active File' and 'Aurix: Scan Staged Changes') using localized 'git diff --cached' configurations.
*   **AI Core Engine:** Engineered the Logic Agent and Consensus Gate. Programmed the conditional edge to strictly drop findings with a `confidence_score < 0.80` to save compute resources.

**Work to be Done in Next Week:**
Replace mock routes with live database logic, upgrade the IDE Secret Guard, finalize the Kanban results dashboard, and initiate the Ephemeral Docker Sandbox development.

---

### **WEEK 5**
**Work Done in Current Week:**
*   **Architecture & Backend:** Integrated live backend logic for GitHub ingestion. Metadata is saved to Supabase (PENDING status) and jobs are pushed to the Upstash Redis Queue (LPUSH) for async processing.
*   **Web Frontend:** Built the Results Dashboard (Kanban Upgraded). Designed the final view to map the verified vulnerabilities array into a rich data-grid, filterable by Severity and sortable by status.
*   **IDE Extension:** Coded the Pre-Flight regex Secret Guard system to catch common signature groups (AWS keys, passwords), configuring a blocking UX warning modal to intercept high-risk file saves.
*   **AI Core Engine:** Developed the Ephemeral Docker Sandbox engine using the Docker Python SDK to dynamically spin up isolated, network-restricted containers for safe exploit testing.

**Work to be Done in Next Week:**
Implement multipart/form-data upload logic with Supabase Storage, attach the IDE Secret Guard to live AI endpoints, and prompt the Red and Blue AI Agents.

---

### **WEEK 6**
**Work Done in Current Week:**
*   **Architecture & Backend:** Integrated `multer` for multipart/form-data handling. Implemented Supabase SDK to stream .zip payloads directly to cloud storage buckets to manage memory constraints.
*   **Web Frontend:** Implemented React Syntax Highlighter to cleanly render the Red Agent's Python script and the Blue Agent's patch code with proper indentation and colors.
*   **IDE Extension:** Upgraded the Secret Guard module by attaching it to the live AI classification endpoint to accurately determine variance between genuine private credentials and dummy testing values.
*   **AI Core Engine:** Prompted the Red Agent to write tailored `poc_script.py` payloads, and sequentially prompted the Blue Agent to generate the verified `patch_code`.

**Work to be Done in Next Week:**
Refactor polling logic to perform live queries, build a background status polling loop in the IDE, and engineer the AI Reflexion Loop for self-correction.

---

### **WEEK 7**
**Work Done in Current Week:**
*   **Architecture & Backend:** Refactored GET /api/scans/{scan_id} to perform live Supabase queries, returning real-time SCANNING or COMPLETED statuses and payloads.
*   **Web Frontend:** Added interactivity to the Results Dashboard, implementing a toggle tied to a PATCH request allowing users to mark a bug as `is_resolved: true`.
*   **IDE Extension:** Developed the functional API Connector layer. Engineered a multipart upload system via POST to safely pass the zipped workspace file bundle with JWT headers.
*   **AI Core Engine:** Engineered the "Reflexion" Loop. Configured the state machine to capture stderr from the Docker sandbox and route it back to the Red Agent for self-correction (capped at 3 retries).

**Work to be Done in Next Week:**
Setup the pgvector database extension, stream real-time IDE execution logs, and prepare comprehensive documentation for Progress Evaluation 1.

---

### **WEEK 8**
**Work Done in Current Week:**
*   **Architecture & Backend:** Commenced Phase 3 (AI Upgrade). Enabled `pgvector` in Supabase and designed the `knowledge_base` table with high-dimensional vector columns for the RAG pipeline.
*   **Web Frontend:** Prepared presentation assets and demonstrated the seamless authentication, dual-mode ingestion, and syntax-highlighted Kanban dashboard.
*   **IDE Extension:** Added asynchronous status polling mechanics tied to the 'vscode.window.withProgress' tracking UI. Streamed real-time remote scan logs dynamically to the AURIX IDE Output Panel.
*   **AI Core Engine:** Prepared and finalized the data seeding script (`seed_rag.js`) for OWASP security guidelines.
*   **Milestone:** Successfully completed Progress Evaluation 1.

**Work to be Done in Next Week:**
Convert ingested docs into embeddings, build the Contextual AI Chat Assistant, map the LangGraph State Reducer, and develop the IDE Diagnostics UI.

---

### **WEEK 9**
**Work Done in Current Week:**
*   **Architecture & Backend:** Built `seed_rag.js` for document ingestion. Parsed OWASP Cheat Sheets, vulnerability PoC templates, and patch code templates for Python and JS.
*   **Web Frontend:** Built a slide-out Contextual AI Chat Assistant panel attached to the vulnerability detail view, allowing users to ask follow-up questions about specific bugs.
*   **IDE Extension:** Built the IDE Diagnostics UI core components. Parsed the JSON responses and successfully bound them to the VS Code Diagnostics API to draw red squiggly error indications.
*   **AI Core Engine:** Mapped the final State Reducer (Node 7) to append fully verified dictionary objects to the `verified_reports` state list, compiling the final JSON payload autonomously.

**Work to be Done in Next Week:**
Integrate Transformers.js for embeddings, coordinate IDE relative zip unpacking paths, and implement native CodeActionProviders for quick fixes.

---

### **WEEK 10**
**Work Done in Current Week:**
*   **Architecture & Backend:** Integrated `Transformers.js` with the `all-MiniLM-L6-v2` model. Converted markdown security documentation into embeddings and populated the Supabase vector table.
*   **Web Frontend:** Finalized the AI Chatbot's state management using React Hooks and Context to maintain conversation history seamlessly during navigation.
*   **IDE Extension:** Implemented the native 'CodeActionProvider' pipeline to surface a context-aware "Quick Fix" lightbulb action labelled: "AURIX: Apply AI Security Patch".
*   **AI Core Engine:** Coordinated closely with the IDE integration team to calibrate relative zip unpacking path resolutions for the isolated Docker simulation sandbox engine.

**Work to be Done in Next Week:**
Develop the Threat Intel Similarity Search API, architect the webview visualization for the IDE, and build the "One-Click PR" feature on the web dashboard.

---

### **WEEK 11**
**Work Done in Current Week:**
*   **Architecture & Backend:** Developed Threat Intel Similarity Search via Supabase RPC. Implemented cosine similarity search returning the top 3 relevant security contexts in under 500ms.
*   **Web Frontend:** Built the "One-Click GitHub Pull Requests" module. Added a "Remediate" button that automatically branches the user's repository, applies the AI's code patch, and opens a PR using the OAuth token.
*   **IDE Extension:** Built the elegant inline "Ghost-Text" code patcher layer. Integrated the modern Inline Completion API framework to stream suggested code improvements instantly via the Tab key.
*   **AI Core Engine:** Utilized LangGraph's async capabilities (Send API) to fan out the state machine, enabling Parallel Wargaming to process multiple vulnerabilities concurrently, drastically reducing scan times.

**Work to be Done in Next Week:**
Initiate Phase 4 Orchestration by creating internal webhook routes, implement the IDE Attack Path Webview, and enforce strict Pydantic schemas in the AI outputs.

---

### **WEEK 12**
**Work Done in Current Week:**
*   **Architecture & Backend:** Initiated Phase 4 (Orchestration). Created POST `/api/internal/webhook/scan-complete` to serve as the catch mechanism for payloads from the AWS AI Worker.
*   **Web Frontend:** Polished graceful error handling. If the backend returns Status: FAILED, the UI now shows a clear alert box rather than crashing, and gracefully handles incomplete patch_code data.
*   **IDE Extension:** Implemented the complete Attack Path Webview panel. Designed an interactive HTML-based canvas component detailing progressive multi-stage threat paths generated by the Red Team engine.
*   **AI Core Engine:** Enforced Strict Schema constraints using LangChain's `.with_structured_output()` and Pydantic models. Connected the completed state machine to POST results to the backend webhook.

**Work to be Done in Next Week:**
Finalize webhook database update logic, conduct extensive full-lifecycle integration testing, and prepare for Progress Evaluation 2.

---

### **WEEK 13**
**Work Done in Current Week:**
*   **Architecture & Backend:** Finalized webhook parsing logic to extract verified bugs, update SCAN status, and populate the VERIFIED_VULNERABILITIES relational table.
*   **Web Frontend:** Ensured all protected routes immediately redirect unauthenticated users. Prepared demonstration protocols and presentation assets showcasing the live web application.
*   **IDE Extension:** Conducted extensive full-lifecycle integration testing: validation sequences included login routing, file packaging, polling tracking, diagnostics injection, and ghost-text streaming.
*   **AI Core Engine:** Fine-tuned the AI prompts and Consensus Gate threshold based on integration test results to minimize false positives while maintaining high detection rates.
*   **Milestone:** Successfully completed Progress Evaluation 2.

**Work to be Done in Next Week:**
Implement API rate limiting to protect cloud compute, polish extension UX, write unit tests, and draft user documentation.

---

### **WEEK 14**
**Work Done in Current Week:**
*   **Architecture & Backend:** Implemented Redis-backed API Rate Limiting using `express-rate-limit`. Configured 429 error handling to prevent queue flooding and manage expensive AI compute quotas.
*   **Web Frontend:** Addressed feedback from Progress Evaluation 2, optimizing UI responsiveness on mobile views and enhancing the loading state animations.
*   **IDE Extension:** Polished extension UX across all pathways (smooth Status Bar notifications, fallback error dialog handling, log filtering). Formulated a suite of unit test validation suites targeting packager exclusion rules.
*   **AI Core Engine:** Optimized token usage within the RAG context injector and improved the AST slicer's robustness when parsing malformed or syntactically incorrect source code.

**Work to be Done in Next Week:**
Develop automated data sanitization cron jobs, build the IDE extension binary, deploy the web app, and begin drafting the final authoritative project document.

---

### **WEEK 15**
**Work Done in Current Week:**
*   **Architecture & Backend:** Developed `node-cron` scheduled jobs for data sanitization. Implemented automatic deletion of .zip payloads from Supabase Storage post-scan to ensure privacy and efficiency.
*   **Web Frontend:** Successfully deployed the production-ready web application on Vercel. Verified flawless handling of user sessions and real-time backend communication over public domains.
*   **IDE Extension:** Successfully built the plugin binary using the 'vsce package' framework. Validated clear setup and removal behaviors locally and consolidated the final engineering configuration docs.
*   **AI Core Engine:** Finalized the Dockerfile configurations for the AI Worker daemon, ensuring the Docker-in-Docker (DinD) sandbox orchestration operates securely on the production AWS EC2 instance.

**Work to be Done in Next Week:**
Conduct final full-stack integration testing, compile the complete FYP Progress Diary, finish the End Semester Report, and prepare for final project defenses.

---

### **WEEK 16**
**Work Done in Current Week:**
*   **Architecture & Backend:** Conducted full-stack integration testing. Verified Redis queuing, webhook handshakes with AWS EC2, and RAG retrieval latency. Finalized production deployment.
*   **Web Frontend:** Concluded end-to-end user acceptance testing for the Dual-Mode ingestion, automated PR generation, and real-time AI Chatbot.
*   **IDE Extension:** Compiled the comprehensive FYP Progress Diary collection and completed all structural documentation reporting segments focusing explicitly on the IDE Integration platform architectures.
*   **AI Core Engine:** Monitored the production AI Worker during stress tests, confirming successful parallel wargaming and strict ephemeral container destruction upon task completion.

**Work to be Done in Next Week:**
Progress Evaluation 3: Participate in final live project defenses, engine presentations, and multi-department evaluation panels.
