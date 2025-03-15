# backend/app/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file at project root
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/pipeline_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Authentication Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_super_secret_key")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "supersecurepassword")

# Bucket Names (Public and Private)
PUBLIC_ORIGINAL_BUCKET = os.getenv("PUBLIC_ORIGINAL_BUCKET", "public-original-files")
PUBLIC_PROCESSED_BUCKET = os.getenv("PUBLIC_PROCESSED_BUCKET", "public-processed-stems")
PUBLIC_FINAL_BUCKET = os.getenv("PUBLIC_FINAL_BUCKET", "public-final-instrumentals")
PRIVATE_ORIGINAL_BUCKET = os.getenv("PRIVATE_ORIGINAL_BUCKET", "private-original-files")
PRIVATE_PROCESSED_BUCKET = os.getenv("PRIVATE_PROCESSED_BUCKET", "private-processed-stems")
PRIVATE_FINAL_BUCKET = os.getenv("PRIVATE_FINAL_BUCKET", "private-final-instrumentals")

# Spleeter Service URL
SPLEETER_SERVICE_URL = os.getenv("SPLEETER_SERVICE_URL", "http://spleeter:5001/separate")
