from fastapi import FastAPI, HTTPException
import subprocess
import os
import urllib.parse
from minio import Minio
import redis
import time


app = FastAPI()

# 📌 MinIO Configuration
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "supersecret"
BUCKETS = ["original-files", "processed-stems", "final-instrumentals"]

# 📌 Redis Configuration (For Progress Tracking)
REDIS_HOST = "redis"
REDIS_PORT = 6379
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# 📌 Initialize MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT.replace("http://", ""),
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

# 📌 Define Paths
AUDIO_FILES_DIR = "/spleeter_service/audio_files"
SPLEETER_OUTPUT_DIR = "/spleeter_service/spleeter_audio/output"

def is_valid_mp3(file_path):
    """ Checks if an MP3 file is valid using FFmpeg. """
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError:
        return False

def merge_stems(task_id, stems_to_merge, output_path):
    """ Merges non-vocal stems into a single instrumental file using FFmpeg. """
    concat_file_path = f"{output_path}/{task_id}_concat_list.txt"

    if not stems_to_merge:
        return None  # 🔹 No stems available for merging, return None

    with open(concat_file_path, "w") as f:
        for stem in stems_to_merge:
            if os.path.exists(stem):  # ✅ Ensure the file exists before adding
                f.write(f"file '{stem}'\n")

    final_instrumental = f"{output_path}/{task_id}_instrumental.mp3"

    merge_command = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", concat_file_path,
        "-acodec", "libmp3lame", final_instrumental
    ]

    try:
        subprocess.run(merge_command, check=True)
        os.remove(concat_file_path)
        return final_instrumental
    except subprocess.CalledProcessError:
        return None

@app.post("/separate")
def separate_audio(file_name: str, model: str = "2stems"):
    """ Processes an audio file using Spleeter and ensures the entire pipeline runs automatically. """
    if model not in ["2stems", "4stems", "5stems"]:
        raise HTTPException(status_code=400, detail="Invalid model selection.")

    decoded_file_name = urllib.parse.unquote(file_name)
    task_id = decoded_file_name.replace(" ", "_").split(".")[0]

    local_file_path = f"{AUDIO_FILES_DIR}/{decoded_file_name}"
    output_path = f"{SPLEETER_OUTPUT_DIR}/{task_id}"

    redis_client.hset(task_id, mapping={"status": "Processing", "progress": "0%"})

    try:
        minio_client.fget_object("original-files", decoded_file_name, local_file_path)
    except Exception as e:
        redis_client.hset(task_id, mapping={"status": "Failed", "error": str(e)})
        raise HTTPException(status_code=404, detail="File not found in MinIO.")

    command = ["spleeter", "separate", "-p", f"spleeter:{model}", "-o", SPLEETER_OUTPUT_DIR, local_file_path]

    try:
        subprocess.run(command, check=True)
        redis_client.hset(task_id, mapping={"progress": "60%"})

        stem_files = {
            "2stems": ["accompaniment"],
            "4stems": ["vocals", "drums", "bass", "other"],
            "5stems": ["vocals", "drums", "bass", "piano", "other"]
        }

        stems_to_merge = []
        for stem in stem_files[model]:
            wav_file = f"{output_path}/{stem}.wav"
            mp3_file = f"{output_path}/{stem}.mp3"

            if os.path.exists(wav_file):
                subprocess.run(["ffmpeg", "-i", wav_file, "-q:a", "2", "-map", "a", mp3_file], check=True)

                if is_valid_mp3(mp3_file):
                    minio_client.fput_object("processed-stems", f"{task_id}/{stem}.mp3", mp3_file)
                    if stem != "vocals":
                        stems_to_merge.append(mp3_file)

                os.remove(wav_file)

        final_instrumental = merge_stems(task_id, stems_to_merge, SPLEETER_OUTPUT_DIR)

        if final_instrumental:
            minio_client.fput_object("final-instrumentals", f"{task_id}_instrumental.mp3", final_instrumental)
            os.remove(final_instrumental)

        os.remove(local_file_path)
        redis_client.hset(task_id, mapping={"status": "Completed", "progress": "100%"})

        return {"message": "Separation successful & uploaded to MinIO"}

    except subprocess.CalledProcessError:
        redis_client.hset(task_id, mapping={"status": "Failed", "progress": "Error"})
        raise HTTPException(status_code=500, detail="Spleeter processing failed")
