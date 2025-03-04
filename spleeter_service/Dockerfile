# Use a clean Python 3.10 base image
FROM python:3.10

# Set working directory
WORKDIR /spleeter_service

# Install system dependencies (FFmpeg)
RUN apt-get update && apt-get install -y ffmpeg

# Install correct NumPy version before TensorFlow
RUN pip install --no-cache-dir "numpy<2"

# Install Spleeter, FastAPI, Uvicorn, MinIO Client, Mutagen for metadata handling, and Redis
RUN pip install --no-cache-dir spleeter fastapi uvicorn minio tensorflow mutagen redis

# Create necessary directories with correct ownership
RUN mkdir -p /spleeter_service/pretrained_models \
    && chown -R 1000:1000 /spleeter_service/pretrained_models

# Copy our Spleeter API code into the container
COPY spleeter_api.py .

# Expose the FastAPI port
EXPOSE 5001

# Start FastAPI with Spleeter
CMD ["python3", "-m", "uvicorn", "spleeter_api:app", "--host", "0.0.0.0", "--port", "5001"]
