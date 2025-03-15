# file_watcher/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including inotify-tools and curl)
RUN apt-get update && \
    apt-get install -y inotify-tools curl && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories (will be mounted as volumes)
RUN mkdir -p /deemix_audio_files /pdl_audio_files /audio_files

# Copy dependency file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files (including file_watcher.sh and the helper module)
COPY . .

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use the entrypoint to fix permissions before running the file watcher script
ENTRYPOINT ["/entrypoint.sh"]

# Default command: run the file watcher script
CMD ["sh", "file_watcher.sh"]
