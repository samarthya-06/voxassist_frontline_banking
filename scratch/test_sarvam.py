import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_BASE = "https://api.sarvam.ai"

async def test_sarvam_stt():
    print(f"Testing Sarvam API Key: {SARVAM_API_KEY[:5]}...{SARVAM_API_KEY[-5:]}")
    
    # Create a dummy silent wav file (very small)
    audio_bytes = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {
                "model": "saaras:v3",
                "language_code": "hi-IN",
                "mode": "transcribe",
            }
            headers = {"api-subscription-key": SARVAM_API_KEY}
            
            print("Sending request to Sarvam...")
            resp = await client.post(
                f"{SARVAM_BASE}/speech-to-text",
                files=files,
                data=data,
                headers=headers,
            )
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sarvam_stt())
