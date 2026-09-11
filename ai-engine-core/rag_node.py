import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_embedding(text):
    """Fetch 384-dimension embedding from Hugging Face API."""
    api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{EMBEDDING_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(api_url, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}})
    return response.json()

def fetch_threat_intel(query_text, limit=3):
    """Semantic search against Supabase Vector DB."""
    query_vector = get_embedding(query_text)
    
    # We use rpc (remote procedure call) to call a custom Postgres function 
    # that handles vector similarity. (We need to add this SQL function next).
    res = supabase.rpc("match_threat_intel", {
        "query_embedding": query_vector,
        "match_threshold": 0.5, # Adjust for precision
        "match_count": limit
    }).execute()
    
    return res.data

def rag_node(state):
    """
    AURIX LangGraph Node: RAG Retrieval.
    Enriches the current vulnerability with industry-standard threat intelligence.
    """
    vuln = state.get("current_vuln")
    if not vuln:
        return state
    
    print(f"🔍 [RAG] Fetching Threat Intel for: {vuln['title']}")
    intel = fetch_threat_intel(f"{vuln['title']}: {vuln.get('snippet', '')}")
    
    # Format the intel for the Logic Agent
    intel_summary = "\n".join([f"- {i['content']} (Source: {i['metadata']['category']})" for i in intel])
    
    state["threat_intel"] = intel_summary
    return state
