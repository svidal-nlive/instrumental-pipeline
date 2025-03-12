# Spleeter Processing Service Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Install spleeter dependencies
RUN pip install --no-cache-dir spleeter flask requests

# Copy application files
COPY . .

# Expose API port
EXPOSE 5001

# Start the Flask application
CMD ["python", "spleeter_api.py"]
