# spleeter_service/spleeter_api.py
import os
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException, Query
from minio import Minio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Spleeter Processing Service")

# MinIO configuration from environment variables
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "supersecurepassword")

# Bucket names (for original, processed stems, and final instrumentals)
PUBLIC_ORIGINAL_BUCKET = os.getenv("PUBLIC_ORIGINAL_BUCKET", "public-original-files")
PUBLIC_PROCESSED_BUCKET = os.getenv("PUBLIC_PROCESSED_BUCKET", "public-processed-stems")
PUBLIC_FINAL_BUCKET = os.getenv("PUBLIC_FINAL_BUCKET", "public-final-instrumentals")
PRIVATE_ORIGINAL_BUCKET = os.getenv("PRIVATE_ORIGINAL_BUCKET", "private-original-files")
PRIVATE_PROCESSED_BUCKET = os.getenv("PRIVATE_PROCESSED_BUCKET", "private-processed-stems")
PRIVATE_FINAL_BUCKET = os.getenv("PRIVATE_FINAL_BUCKET", "private-final-instrumentals")

# Initialize MinIO client (assuming HTTP, non-secure)
minio_client = Minio(
    MINIO_ENDPOINT.replace("http://", ""),
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def validate_mp3(file_path: str) -> bool:
    """Use ffmpeg to validate the MP3 file."""
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

def run_spleeter(input_file: str, output_dir: str, model: str = "5stems") -> None:
    """Run Spleeter to separate audio stems."""
    try:
        cmd = ["python", "-m", "spleeter", "separate", "-p", f"spleeter:{model}", "-o", output_dir, input_file]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Spleeter processing failed: {str(e)}")

def convert_wav_to_mp3(input_wav: str, output_mp3: str) -> None:
    """Convert a .wav file to .mp3 using FFmpeg."""
    cmd = ["ffmpeg", "-y", "-i", input_wav, "-codec:a", "libmp3lame", "-qscale:a", "2", output_mp3]
    subprocess.run(cmd, check=True)

def merge_mp3_files(input_files: list, output_file: str) -> None:
    """
    Merge multiple mp3 files using ffmpeg amix filter.
    This command mixes the input tracks with a duration equal to the longest input.
    """
    cmd = ["ffmpeg", "-y"]
    for infile in input_files:
        cmd.extend(["-i", infile])
    num_inputs = len(input_files)
    filter_complex = f"amix=inputs={num_inputs}:duration=longest:dropout_transition=2"
    cmd.extend(["-filter_complex", filter_complex, output_file])
    subprocess.run(cmd, check=True)

@app.post("/separate")
async def separate_audio(
    file_name: str = Query(..., description="The task_id of the file to process"),
    model: str = Query("5stems", description="Separation model to use"),
    source: str = Query("", description="Source identifier: 'manual' for user uploads, empty for auto downloads")
):
    """
    Processes an audio file using Spleeter:
      - Downloads the file from MinIO.
      - Validates the file.
      - Runs Spleeter to separate stems.
      - Converts each WAV stem to MP3.
      - Uploads the converted stems to the processed stems bucket.
      - Merges non-vocal stems into a final instrumental MP3.
      - Uploads the final instrumental to the final instrumentals bucket.
    """
    # Determine original file bucket based on source
    orig_bucket = PRIVATE_ORIGINAL_BUCKET if source.lower() == "manual" else PUBLIC_ORIGINAL_BUCKET

    with tempfile.TemporaryDirectory() as temp_dir:
        local_input = os.path.join(temp_dir, file_name)
        try:
            minio_client.fget_object(orig_bucket, file_name, local_input)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Original file not found: {str(e)}")

        if not validate_mp3(local_input):
            raise HTTPException(status_code=400, detail="Uploaded MP3 file is corrupted or invalid.")

        # Create an output directory for Spleeter processing
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        run_spleeter(local_input, output_dir, model)

        # Spleeter creates a folder named after the base filename (without extension)
        base_name, _ = os.path.splitext(file_name)
        processed_dir = os.path.join(output_dir, base_name)
        if not os.path.exists(processed_dir):
            raise HTTPException(status_code=404, detail="Spleeter output directory not found.")

        # Expected stems from Spleeter
        stems = ["vocals", "piano", "drums", "bass", "other"]
        converted_files = {}
        for stem in stems:
            wav_file = os.path.join(processed_dir, f"{stem}.wav")
            if not os.path.exists(wav_file):
                # For essential non-vocal stems, fail if missing
                if stem != "vocals":
                    raise HTTPException(status_code=404, detail=f"Expected stem {stem}.wav not found.")
                continue  # vocals can be optional for merging
            mp3_file = os.path.join(processed_dir, f"{base_name}_{stem}.mp3")
            convert_wav_to_mp3(wav_file, mp3_file)
            converted_files[stem] = mp3_file

        # Determine processed stems bucket based on source
        proc_bucket = PRIVATE_PROCESSED_BUCKET if source.lower() == "manual" else PUBLIC_PROCESSED_BUCKET
        # Upload each converted stem into a folder named after the base filename
        for stem, mp3_path in converted_files.items():
            object_name = f"{base_name}/{base_name}_{stem}.mp3"
            try:
                minio_client.fput_object(proc_bucket, object_name, mp3_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload processed stem {stem}: {str(e)}")

        # Merge non-vocal stems (piano, drums, bass, other) into final instrumental
        non_vocal_stems = []
        for stem in ["piano", "drums", "bass", "other"]:
            if stem in converted_files:
                non_vocal_stems.append(converted_files[stem])
        if not non_vocal_stems:
            raise HTTPException(status_code=404, detail="No non-vocal stems available for merging.")

        final_instrumental = os.path.join(processed_dir, f"{base_name}_instrumental.mp3")
        merge_mp3_files(non_vocal_stems, final_instrumental)

        # Determine final instrumentals bucket based on source
        final_bucket = PRIVATE_FINAL_BUCKET if source.lower() == "manual" else PUBLIC_FINAL_BUCKET
        object_name_final = f"{base_name}/{base_name}_instrumental.mp3"
        try:
            minio_client.fput_object(final_bucket, object_name_final, final_instrumental)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload final instrumental: {str(e)}")

        return {
            "message": "Separation and processing successful",
            "final_instrumental": f"{base_name}_instrumental.mp3",
            "processed_stems_folder": base_name
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
