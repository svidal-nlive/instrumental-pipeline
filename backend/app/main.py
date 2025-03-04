from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from minio import Minio
import os
import uuid
import requests
from typing import List
import re  # 🔹 Added for snake_case conversion
import redis  # 🔹 Import Redis for status tracking

app = FastAPI()

# 📌 MinIO Configuration
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "supersecret"
BUCKETS = ["original-files", "processed-stems", "final-instrumentals"]

# 📌 Spleeter Service URL
SPLEETER_SERVICE_URL = "http://spleeter:5001/separate"

# 📌 Redis Configuration
REDIS_HOST = "redis"
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# 📌 Initialize MinIO Client
minio_client = Minio(
    "minio:9000",
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# 📌 Ensure MinIO Buckets Exist
def create_buckets():
    for bucket in BUCKETS:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)

create_buckets()

# 📌 Utility Function: Convert Filename to Snake Case
def to_snake_case(filename: str) -> str:
    """ Converts a filename to snake_case and removes special characters. """
    base_name, ext = os.path.splitext(filename)
    base_name = re.sub(r'[\s\-]+', '_', base_name)  # Replace spaces/hyphens with underscores
    base_name = re.sub(r'[^a-zA-Z0-9_]', '', base_name)  # Remove special characters
    return f"{base_name}{ext}"

# 📌 Utility Function: Generate Unique Task ID (Fix `.mp3.mp3` Issue)
def generate_task_id(filename: str) -> str:
    base_name, ext = os.path.splitext(to_snake_case(filename))  # 🔹 Ensure snake_case
    unique_id = str(uuid.uuid4())[:8]  # Short UUID
    return f"{base_name}_{unique_id}{ext}"  # ✅ Prevent `.mp3.mp3`

# 📌 1️⃣ Upload a Song & Trigger Processing
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), model: str = "2stems"):
    """
    Uploads an audio file to MinIO under the 'original-files' bucket.
    Converts filename to snake_case.
    Accepts model selection for Spleeter.
    Automatically triggers Spleeter processing asynchronously.
    """
    try:
        # Convert to snake_case and generate Task ID
        sanitized_filename = to_snake_case(file.filename)
        task_id = generate_task_id(sanitized_filename)

        # ✅ Ensure file_name ends in `.mp3`
        if not task_id.endswith(".mp3"):
            task_id += ".mp3"

        # Upload to MinIO
        minio_client.put_object(
            "original-files",
            task_id,
            file.file,
            length=-1,
            part_size=10 * 1024 * 1024
        )

        # 🔹 Store Initial Status in Redis
        redis_client.hset(task_id, mapping={"status": "Uploaded", "progress": "0%"})

        # 🔹 Asynchronously Trigger Spleeter Processing
        try:
            requests.post(
                SPLEETER_SERVICE_URL,
                params={"file_name": task_id, "model": model},
                timeout=1  # ✅ Only wait 1 second to trigger request, then exit
            )
        except requests.exceptions.Timeout:
            pass  # ✅ Ignore timeout since processing continues in the background

        return {
            "message": "Upload successful, processing started asynchronously",
            "file_name": task_id,
            "task_id": task_id.replace(".mp3", ""),  # ✅ Show task ID without .mp3
            "model": model
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# 📌 2️⃣ List Available Songs
@app.get("/songs/")
def list_songs():
    """ Lists all available songs in the 'original-files' bucket. """
    try:
        objects = minio_client.list_objects("original-files", recursive=True)
        return [{"song_name": obj.object_name} for obj in objects]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve songs: {str(e)}")

# 📌 3️⃣ Retrieve Final Instrumental
@app.get("/instrumentals/{song_id}/")
def get_instrumental(song_id: str):
    """
    Retrieves the final instrumental for a specific song.
    """
    try:
        instrumental_file = f"{song_id}_instrumental.mp3"
        minio_client.stat_object("final-instrumentals", instrumental_file)
        return {"instrumental": instrumental_file}
    except Exception:
        raise HTTPException(status_code=404, detail="Instrumental not found.")

# 📌 2️⃣ Get Processing Status
@app.get("/status/{task_id}")
def get_task_status(task_id: str):
    """ Retrieves processing status from Redis. """
    status = redis_client.hgetall(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status
