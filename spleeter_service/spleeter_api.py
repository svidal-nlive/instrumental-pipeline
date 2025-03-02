from fastapi import FastAPI, HTTPException
import subprocess
import os
import urllib.parse  # Handle spaces in filenames
import mutagen  # Read metadata
from mutagen.mp3 import EasyMP3
from minio import Minio
import redis
import time  # For simulating progress updates

app = FastAPI()

# MinIO Configuration
MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "supersecret"
BUCKET_NAME = "instrumentals"

# Redis Configuration
REDIS_HOST = "redis"
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Initialize MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

SPLEETER_AUDIO_DIR = "/spleeter_audio"
SPLEETER_OUTPUT_DIR = f"{SPLEETER_AUDIO_DIR}/output"

@app.post("/separate")
def separate_audio(file_name: str):
    # Decode URL-encoded filenames (e.g., "07%20-%20Green.mp3" → "07 - Green.mp3")
    decoded_file_name = urllib.parse.unquote(file_name)
    local_file_path = f"{SPLEETER_AUDIO_DIR}/{decoded_file_name}"
    output_path = f"{SPLEETER_OUTPUT_DIR}/{decoded_file_name.split('.')[0]}"

    # Standardize output filename (replace spaces with underscores)
    instrumental_file = decoded_file_name.replace(" ", "_").replace(".mp3", "_instrumental.mp3")

    # Store initial status in Redis
    task_id = instrumental_file
    redis_client.hset(task_id, mapping={"status": "Processing", "progress": "0%"})

    # Step 1: Download file from MinIO
    try:
        minio_client.fget_object(BUCKET_NAME, decoded_file_name, local_file_path)
    except Exception as e:
        redis_client.hset(task_id, mapping={"status": "Failed", "error": str(e)})
        raise HTTPException(status_code=404, detail=f"File not found in MinIO: {str(e)}")

    # Step 2: Read original metadata
    metadata = {}
    try:
        audio = EasyMP3(local_file_path)
        metadata = {
            "title": audio.get("title", ["Unknown"])[0],
            "artist": audio.get("artist", ["Unknown"])[0],
            "album": audio.get("album", ["Unknown"])[0]
        }
    except Exception as e:
        metadata = {"error": f"Metadata extraction failed: {str(e)}"}

    # Update progress
    redis_client.hset(task_id, mapping={"progress": "20%"})

    # Step 3: Run Spleeter processing
    command = [
        "spleeter", "separate",
        "-p", "spleeter:2stems",
        "-o", SPLEETER_OUTPUT_DIR,
        local_file_path
    ]

    try:
        subprocess.run(command, check=True)
        redis_client.hset(task_id, mapping={"progress": "60%"})

        # Convert accompaniment.wav to MP3
        wav_file = f"{output_path}/accompaniment.wav"
        mp3_file = f"{output_path}/accompaniment.mp3"
        subprocess.run(["ffmpeg", "-i", wav_file, "-q:a", "2", "-map", "a", mp3_file], check=True)

        # Apply metadata to MP3 file
        final_mp3 = f"{SPLEETER_AUDIO_DIR}/{instrumental_file}"
        subprocess.run(["ffmpeg", "-i", mp3_file, "-metadata", f"title={metadata['title']} - Instrumental",
                        "-metadata", f"artist={metadata['artist']}",
                        "-metadata", f"album={metadata['album']}",
                        "-codec", "copy", final_mp3], check=True)

        # Upload MP3 to MinIO
        minio_client.fput_object(BUCKET_NAME, instrumental_file, final_mp3)

        # Cleanup - Remove processed files
        os.remove(local_file_path)
        os.remove(wav_file)
        os.remove(mp3_file)
        os.remove(final_mp3)

        redis_client.hset(task_id, mapping={"status": "Completed", "progress": "100%"})

        return {"message": "Separation & upload successful", "mp3_file": instrumental_file}
    
    except subprocess.CalledProcessError:
        redis_client.hset(task_id, mapping={"status": "Failed", "progress": "Error"})
        raise HTTPException(status_code=500, detail="Spleeter processing failed")
    except Exception as e:
        redis_client.hset(task_id, mapping={"status": "Failed", "progress": "Error", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}")
def get_task_status(task_id: str):
    """Retrieve processing status from Redis."""
    status = redis_client.hgetall(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status
