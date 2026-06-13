import os
import json
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

if not SUPABASE_URL or "PASTE" in SUPABASE_URL:
    print("❌ Error: Supabase credentials not found in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_embedding(text):
    """Fetch 384-dimension embedding from Hugging Face API."""
    api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{EMBEDDING_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(api_url, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}})
    return response.json()

# Initial Security Knowledge Base (Industry Standards)
SECURITY_KNOWLEDGE = [
    {
        "content": "SQL Injection (SQLi): Occurs when untrusted data is sent to an interpreter as part of a command or query. Use parameterized queries or ORMs to prevent.",
        "metadata": {"category": "OWASP A03:2021", "cwe": "CWE-89"}
    },
    {
        "content": "Broken Access Control: Users can act outside of their intended permissions. Failure to enforce least privilege. Check IDOR, BOLA, and missing role checks.",
        "metadata": {"category": "OWASP A01:2021", "cwe": "CWE-284"}
    },
    {
        "content": "Insecure Deserialization: Untrusted data is used to abuse the logic of an application, inflict a DoS attack, or even execute arbitrary code. Avoid deserializing user-provided objects.",
        "metadata": {"category": "OWASP A08:2021", "cwe": "CWE-502"}
    },
    {
        "content": "Cross-Site Scripting (XSS): Malicious scripts are injected into trusted websites. Use context-aware output encoding and Content Security Policy (CSP).",
        "metadata": {"category": "OWASP A03:2021", "cwe": "CWE-79"}
    }
]

def seed():
    print(f"🚀 Seeding {len(SECURITY_KNOWLEDGE)} security rules to Supabase Cloud...")
    for entry in SECURITY_KNOWLEDGE:
        print(f"-> Processing: {entry['metadata']['category']}")
        vector = get_embedding(entry['content'])
        
        # Save to Supabase
        data = {
            "content": entry['content'],
            "metadata": entry['metadata'],
            "embedding": vector
        }
        res = supabase.table("threat_intel").insert(data).execute()
        print(f"✅ Success: {entry['metadata']['category']}")

if __name__ == "__main__":
    seed()
