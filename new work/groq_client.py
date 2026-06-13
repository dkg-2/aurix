from groq import Groq
import json
import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class AurixGroqClient:
    """
    Enhanced Groq Client with Key Rotation and error recovery.
    """

    def __init__(self, api_key=None):
        # Support multiple keys: GROQ_API_KEY="key1,key2,key3"
        raw_keys = api_key or os.environ.get("GROQ_API_KEY", "")
        self.api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.current_key_index = 0
        
        if not self.api_keys:
            print("[WARN] No GROQ_API_KEY found.")
            self.client = None
        else:
            self._init_client()
        
        self.triage_model = "openai/gpt-oss-20b"
        self.reasoning_model = "openai/gpt-oss-120b"

    def _init_client(self):
        key = self.api_keys[self.current_key_index]
        self.client = Groq(api_key=key)
        print(f"[SYSTEM] AI Engine using Key #{self.current_key_index + 1}")

    def rotate_key(self):
        """Switches to the next API key in the list."""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self._init_client()
            return True
        return False

    def call_logic_agent(self, prompt, retry=True):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON. Ensure you return a complete object."},
                    {"role": "user", "content": prompt}
                ],
                model=self.triage_model,
                response_format={"type": "json_object"},
                max_completion_tokens=2048 # Increase to avoid truncation
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            if "429" in str(e) and self.rotate_key():
                return self.call_logic_agent(prompt, retry)
            if "validation" in str(e).lower() and retry:
                print("    [RETRY] JSON failed. Attempting with explicit JSON instruction...")
                return self.call_logic_agent(prompt + "\nIMPORTANT: Return ONLY a valid JSON object.", retry=False)
            print(f"    [DEBUG] Groq Triage Error: {e}")
            return {"error": str(e), "results": []}

    def call_red_agent(self, prompt):
        # ... (existing red agent code) ...
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional security auditor. Output ONLY code within triple backticks. No conversational filler."},
                    {"role": "user", "content": prompt}
                ],
                model=self.reasoning_model,
            )
            text = chat_completion.choices[0].message.content
            # Normalize smart quotes and other common malformations
            text = text.replace("’", "'").replace("“", '"').replace("”", '"')
            
            # Extract code between backticks - discard everything else
            if "```python" in text:
                return text.split("```python")[1].split("```")[0].strip()
            elif "```" in text:
                return text.split("```")[1].split("```")[0].strip()
            
            # If no backticks, it might be a refusal or a malformed response
            return f"# Error: AI did not provide code block. Response was: {text[:50]}..."
        except Exception as e:
            if "429" in str(e) and self.rotate_key():
                return self.call_red_agent(prompt)
            return f"# Error: {str(e)}"

    def call_blue_agent(self, prompt):
        """Uses high-reasoning Groq model for Patch generation."""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are 'Aurix Blue', a professional security engineer. Output ONLY a Python patch script within triple backticks."},
                    {"role": "user", "content": prompt}
                ],
                model=self.reasoning_model,
            )
            text = chat_completion.choices[0].message.content
            text = text.replace("’", "'").replace("“", '"').replace("”", '"')
            
            if "```python" in text:
                return text.split("```python")[1].split("```")[0].strip()
            elif "```" in text:
                return text.split("```")[1].split("```")[0].strip()
            return f"# Error: No code block. Response: {text[:50]}..."
        except Exception as e:
            if "429" in str(e) and self.rotate_key():
                return self.call_blue_agent(prompt)
            return f"# Error: {str(e)}"
