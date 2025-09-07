 # Use official Python slim image
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Install dependencies
RUN apt-get update -y && \
    apt-get install -y git ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Set environment variables (will override with Render env vars)
ENV DOWNLOAD_DIR=/app/downloads

# Make download dir
RUN mkdir -p /app/downloads/thumbs

# Start bot
CMD ["python", "bot.py"]
