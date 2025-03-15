# Spleeter Processing Service Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose API port
EXPOSE 5001

# Start the FastAPI application using uvicorn
CMD ["uvicorn", "spleeter_api:app", "--host", "0.0.0.0", "--port", "5001"]
