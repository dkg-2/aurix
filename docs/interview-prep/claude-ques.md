Here are all the questions — answer whatever you remember, mark anything you're unsure about and I'll improvise:

**AWS Deployment:**
1. What exactly is running on the t3.small — the FastAPI API layer only, the full pipeline (engine + LangGraph + sandbox), or something else?
2. What OS is on the EC2 instance — Ubuntu 22.04, Amazon Linux, something else?
3. How are you keeping the server running — systemd service, screen/tmux, or just running in the terminal?
4. How is it accessed — raw public IP, Elastic IP, or do you have a domain pointed to it?
5. Which ports are open in the Security Group — 8000 (FastAPI default), 80, 443?
6. How are secrets managed on the server — .env file, AWS SSM Parameter Store, or hardcoded (please don't say this)?
7. Is Docker also running on the EC2 for the scanning tools, or are those called differently in the cloud setup?

**Dockerfile:**
8. What is the Dockerfile for — the security-engine:latest scanning image, the aurix-sandbox:latest execution image, or both?
9. What tools/packages are installed inside it?
10. Did you build and push it to AWS ECR, DockerHub, or just build it locally on the EC2?

**Local Path Audit:**
11. What did you change to support local paths — does engine.py now accept a directory path instead of a GitHub URL?
12. Did you actually test it on AgroMark or another local project? What did it find?

**New Code / Repo Updates:**
13. Are there any new Python files in the repo beyond the ones you uploaded earlier (aurix_graph.py, engine.py, context_fetcher.py, sandbox_executor.py, groq_client.py, logic_agent.py, red/blue prompts, rag_node, worker, baseline_runner)?
14. Did you wire the RAG node into the graph (the 30-minute fix I recommended)?
15. Did you add `network_mode='none'` to the sandbox?
16. Did you add a README.md?
17. Are there new verified-results JSON files showing more neutralized vulnerabilities?

**Resume Impact:**
18. Can you now say the engine is "deployed and live on AWS EC2" — or is it still experimental/intermittent?
19. Any new metrics — more vulnerabilities neutralized, more repos tested?

Give me everything in one reply — short bullets are fine. I'll handle the rest.