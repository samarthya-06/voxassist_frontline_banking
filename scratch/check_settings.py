from backend.app.core.config import settings
import os

print(f"Current Working Directory: {os.getcwd()}")
print(f"SARVAM_API_KEY from settings: {settings.sarvam_api_key}")
print(f"SARVAM_API_KEY from environment: {os.getenv('SARVAM_API_KEY')}")
