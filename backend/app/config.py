import os
from dotenv import load_dotenv

load_dotenv()

REDIS_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Set audio files directory within the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILES_DIR = os.path.join(BASE_DIR, "audio_files")  # ✅ Adjusted path
