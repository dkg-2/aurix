import os

import base64

encoded_keys = "Z3NrXzkzYVpycW9ZUzIyS0dvSUlZdkYxV0dkeWIzRllRQURPdHh3NUhNZFA5cG10bm5SRUpFN3QsIGdza194R0NnbTVJUWhIcEFoNDVyRGVPN1dHZHliM0ZZYlpudGVtR3pxeE1sUUVNRWloaDYwZTdpLCBnc2tfTkU1c1dGUzA5SEJwYTZmRHp0cFdXR2R5YjNGWTZsaW5lSUN2OEwyZkZWa2xXdjZoSXo4LCBnc2tfUEJ2SHNKT2xFVmlMS2RHOEl1WGdXR2R5YjNGWXNpOE5TT1g2RXhWcWNvY1FOYmkzRThSMCwgZ3NrX1ZTWldoY05IT0c3Wk11d1VoWmttV0dkeWIzRll6OWlhTEdFaXVNYktETUlqTHRWcEpLcW0sIGdza19kRlpHV1RSS2pqNWZoT3FkY29KZVdHZHliM0ZZNDUza3BXa2pQOFJLR29UcVIwdm9ScUdzLCBnc2tfY0xWTkZmbjExTmZWQW5IMUNNNnhXR2R5YjNGWW5NT3VCdDN6ZWxMT016bnMzOGRlOFJUZiwgZ3NrX1RaUmdPTWdIVktUem53R2pvSzRPV0dkeWIzRllMUXRheUw3N2hmTkNNRXlsajhwajhaeW0sIGdza19YRnFXZVJUeDhnQ0ZNUVhQV2g5NVdHZHliM0ZZaTJRV3lDTzdUU1NoeVNWWnhOZUFJZ3Uz"
decoded_keys = base64.b64decode(encoded_keys).decode("utf-8")

env_content = f"""GROQ_API_KEY="{decoded_keys}"
AURIX_WEBHOOK_URL="http://172.17.0.1:8000/api/v1/scans/webhook"
HOST_WORKSPACE_DIR="/home/ubuntu/aurix/new work/workspace"
"""

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
with open(env_path, "w", encoding="utf-8") as f:
    f.write(env_content)

print(f"[SUCCESS] .env file successfully created at {env_path} with 9 API Keys!")
