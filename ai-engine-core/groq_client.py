import os
import json
import threading
import time
import random
import re
from groq import Groq
from dotenv import load_dotenv

# Load dotenv from parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(parent_dir, '.env'))

# Thread-safe key rotation setup
_api_keys = [k.strip() for k in os.environ.get("GROQ_API_KEY", "").split(",") if k.strip()]
_key_lock = threading.Lock()
_key_index = 0

def estimate_tokens(text: str) -> int:
    """Estimate tokens using ~3.5 chars per token heuristic."""
    return max(1, int(len(text) / 3.5))

def _get_next_key() -> str:
    """Thread-safe round-robin API key rotation."""
    global _key_index
    with _key_lock:
        if not _api_keys:
            raise ValueError("No GROQ API keys available. Please check your GROQ_API_KEY environment variable.")
        key = _api_keys[_key_index]
        _key_index = (_key_index + 1) % len(_api_keys)
        return key

def _reset_backoff():
    """Hook to reset any global backoff state after a successful call."""
    pass

def _call_with_retries(model: str, prompt: str, max_tokens: int = None, require_json: bool = False) -> str:
    """Internal method to handle API calls with exponential backoff, jitter, and key rotation."""
    max_retries = 3
    base_backoff = 1.0

    for attempt in range(max_retries + 1):
        api_key = _get_next_key()
        # Create a new client instance with the rotated key and 30-second timeout
        # max_retries=0 because we handle retries manually to rotate keys on failure
        client = Groq(api_key=api_key, timeout=30.0, max_retries=0)
        
        try:
            messages = []
            if require_json:
                messages.append({"role": "system", "content": "You are an expert security analyst. You MUST respond with valid JSON only. No markdown, no explanation, just the JSON object."})
            messages.append({"role": "user", "content": prompt})
            
            kwargs = {
                "model": model,
                "messages": messages,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if require_json:
                kwargs["response_format"] = {"type": "json_object"}
                
            response = client.chat.completions.create(**kwargs)
            _reset_backoff()
            return response.choices[0].message.content
            
        except Exception as e:
            # Handles Groq API errors: RateLimitError (429), APIStatusError (413), APITimeoutError
            is_final_attempt = (attempt == max_retries)
            if is_final_attempt:
                print(f"API call failed after {max_retries} retries. Final error: {e}")
                raise e
            
            # Exponential backoff with random 0-2s jitter
            sleep_time = (base_backoff * (2 ** attempt)) + random.uniform(0, 2)
            time.sleep(sleep_time)

def call_triage(prompt: str, max_output_tokens: int = 1500) -> dict:
    """
    Uses triage model to return parsed JSON.
    If response is not valid JSON, retries once with explicit JSON instruction.
    """
    model = 'openai/gpt-oss-20b'
    try:
        response_text = _call_with_retries(model, prompt, max_tokens=max_output_tokens, require_json=True)
        return json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        # Retry once with explicit instruction if JSON parsing fails
        retry_prompt = prompt + "\n\nYou must respond ONLY with valid JSON."
        try:
            response_text = _call_with_retries(model, retry_prompt, max_tokens=max_output_tokens, require_json=True)
            return json.loads(response_text)
        except Exception as e:
            print(f"Failed to parse JSON after retry: {e}")
            return {}
    except Exception as e:
        print(f"call_triage failed: {e}")
        return {}

def call_reasoning(prompt: str) -> str:
    """
    Uses reasoning model to return raw text.
    Extracts code from ```python blocks if present.
    """
    model = 'openai/gpt-oss-120b'
    try:
        response_text = _call_with_retries(model, prompt)
        
        # Extract Python code blocks if present
        pattern = r"```python\s*(.*?)\s*```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        if matches:
            return "\n\n".join(matches)
        return response_text
    except Exception as e:
        print(f"call_reasoning failed: {e}")
        return ""
