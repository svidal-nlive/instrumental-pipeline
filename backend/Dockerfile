# backend/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Ensure the project root is in PYTHONPATH
ENV PYTHONPATH="/app"

# Copy dependency files first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Set execute permission for the entrypoint script
RUN chmod +x /app/entrypoint.sh

# Expose the FastAPI port
EXPOSE 8000

# Set the container entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
