import google.generativeai as genai
import json
import os
import time
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class AurixAIClient:
    """
    Manages the Hybrid AI Strategy for Project AURIX.
    Handles rate limiting and model switching between Flash and Pro.
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            print("[WARN] No API Key found. Set GOOGLE_API_KEY env var.")
        else:
            genai.configure(api_key=self.api_key)
            # Debug: List available models if connection fails
            try:
                available = [m.name for m in genai.list_models()]
                print(f"[DEBUG] Connection verified. Available models: {len(available)}")
            except Exception as e:
                print(f"[DEBUG] Could not list models: {e}")
        
        # Initialize Models with Stable Gemini 2.5 series (Early 2026 Standards)
        self.flash_model = genai.GenerativeModel('gemini-2.5-flash')
        self.pro_model = genai.GenerativeModel('gemini-2.5-pro')

    def call_logic_agent(self, prompt):
        """Uses Gemini Flash for high-volume triage."""
        try:
            response = self.flash_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"    [DEBUG] AI API Error: {e}")
            return {"error": str(e), "is_exploitable": False}

    def call_red_agent(self, prompt):
        """Uses Gemini Pro for deep reasoning and PoC generation."""
        # Note: Free tier Pro has a 2 RPM (requests per minute) limit.
        try:
            response = self.pro_model.generate_content(prompt)
            # Extract code between backticks
            text = response.text
            if "```python" in text:
                return text.split("```python")[1].split("```")[0].strip()
            elif "```" in text:
                return text.split("```")[1].split("```")[0].strip()
            return text.strip()
        except Exception as e:
            return f"# Error calling Red Agent: {str(e)}"

if __name__ == "__main__":
    # Test logic
    client = AurixAIClient()
    print("Testing Flash connection...")
    # Add dummy test if key is present
