from fastapi import FastAPI, Depends, File, UploadFile, Query, HTTPException
from minio import Minio
import asyncpg
import redis
import os
import subprocess
from app.database import redis_client, DATABASE_URL
from app.celery_worker import process_file
from celery.result import AsyncResult

app = FastAPI()

SPLEETER_URL = "http://spleeter:5001/process"

# MinIO Client
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "supersecret")

minio_client = Minio(
    "minio:9000",
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)

BUCKET_NAME = "instrumentals"

# Ensure bucket exists
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Instrumental Pipeline API!"}

@app.get("/health")
async def health_check():
    db_status = await check_postgres()
    redis_status = check_redis()
    return {
        "FastAPI": "Running",
        "PostgreSQL": "Healthy" if db_status else "Down",
        "Redis": "Healthy" if redis_status else "Down"
    }

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=file.filename,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024
        )
        return {"message": "File uploaded successfully", "filename": file.filename}
    except Exception as e:
        return {"error": str(e)}

@app.get("/files/")
async def list_files():
    objects = minio_client.list_objects(BUCKET_NAME)
    return [{"name": obj.object_name, "size": obj.size} for obj in objects]

async def check_postgres():
    try:
        conn = await asyncpg.connect(DATABASE_URL.replace("postgresql+asyncpg", "postgres"))
        await conn.close()
        return True
    except Exception:
        return False

def check_redis():
    try:
        redis_client.ping()
        return True
    except Exception:
        return False

@app.post("/process/{file_name}")
def process_audio(file_name: str):
    task = process_file.delay(file_name)
    return {"task_id": task.id, "message": f"Spleeter processing started for {file_name}"}

@app.get("/status/{task_id}")
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=process_file)
    return {"task_id": task_id, "status": task_result.status, "result": task_result.result}
