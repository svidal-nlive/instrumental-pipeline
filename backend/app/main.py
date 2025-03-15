import os
import json
import asyncio
import urllib.parse
from io import BytesIO
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from minio import Minio
import redis
import httpx

# Import CORS middleware
from fastapi.middleware.cors import CORSMiddleware

# Import Alembic config and command utilities
from alembic.config import Config
from alembic import command

# Import application modules
from app.auth.routes import get_current_user, auth_router
from app.database import engine, Base, get_db, SessionLocal
from app import models
from app.models import Song, User
from app.routes.song_router import song_router
from app.admin.routes import admin_router
from app.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    PUBLIC_ORIGINAL_BUCKET,
    PRIVATE_ORIGINAL_BUCKET,
    SPLEETER_SERVICE_URL
)
from app.utils.common import to_snake_case, generate_task_id
from app.logger import logger
from app.auth.utils import hash_password

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # Run Alembic migrations to ensure the database schema is up-to-date.
    try:
        alembic_cfg = Config("/app/alembic.ini")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully.")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        raise e

    # Create required buckets in MinIO
    create_buckets()
    logger.info("Application startup completed.")

    # Seed a default admin user from environment variables
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme")
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == admin_email))
        existing_admin = result.scalars().first()
        if not existing_admin:
            new_admin = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                is_admin=True
            )
            db.add(new_admin)
            await db.commit()
            logger.info("Default admin user created.")
        else:
            logger.info("Default admin already exists.")

# Include routers
app.include_router(admin_router)
app.include_router(song_router)
app.include_router(auth_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MinIO client with environment variables
minio_client = Minio(
    MINIO_ENDPOINT.replace("http://", ""),
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
redis_client = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), decode_responses=True)

def create_buckets():
    # Create required buckets if they do not exist
    buckets = [PUBLIC_ORIGINAL_BUCKET, PRIVATE_ORIGINAL_BUCKET]
    for bucket in buckets:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
            logger.info(f"Bucket created: {bucket}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Instrumental Pipeline API"}

@app.post("/upload/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    model: str = Query("5stems"),
    source: str = Query("", description="Source of file: 'manual' for user uploads, empty for auto downloads")
):
    try:
        file_data = await file.read()
        task_id = generate_task_id(file.filename, file_data)

        async with SessionLocal() as db:
            result = await db.execute(select(Song).filter(Song.task_id == task_id))
            existing_song = result.scalars().first()
            if existing_song:
                raise HTTPException(status_code=400, detail="Duplicate file upload detected.")

        bucket = PRIVATE_ORIGINAL_BUCKET if source.lower() == "manual" else PUBLIC_ORIGINAL_BUCKET
        file_length = len(file_data)
        file_stream = BytesIO(file_data)
        minio_client.put_object(
            bucket,
            task_id,
            data=file_stream,
            length=file_length,
            part_size=10 * 1024 * 1024
        )
        logger.info(f"✅ Original file uploaded: {task_id} to bucket: {bucket}")

        redis_client.hset(task_id, mapping={"status": "Uploaded", "progress": "0%"})

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                SPLEETER_SERVICE_URL,
                params={"file_name": task_id, "model": model, "source": source},
            )
            response.raise_for_status()
            logger.info(f"✅ Successfully triggered processing for {task_id}")

        async with SessionLocal() as db:
            display_filename = to_snake_case(file.filename)
            new_song = Song(
                task_id=task_id,
                title=display_filename,
                processing_status="Pending",
                is_global=False if source.lower() == "manual" else True
            )
            db.add(new_song)
            await db.commit()
            await db.refresh(new_song)

        return {
            "message": "Upload successful, processing started asynchronously",
            "task_id": task_id.replace(".mp3", ""),
            "model": model
        }
    except httpx.HTTPError as he:
        logger.error(f"❌ HTTP error during processing trigger for {task_id}: {str(he)}")
        raise HTTPException(status_code=500, detail=f"HTTP error: {str(he)}")
    except Exception as e:
        logger.error(f"❌ File upload failed for {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
