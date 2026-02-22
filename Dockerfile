FROM python:3.11-slim

# Install system dependencies for archive extraction, screenshots, and media handling
RUN apt-get update && apt-get install -y \
    # Archive support
    p7zip-full \
    unrar-free \
    zip \
    unzip \
    # Media / screenshot support
    ffmpeg \
    # Network & utilities
    wget \
    curl \
    ca-certificates \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p downloads/thumbnails downloads/screenshots

EXPOSE 8080

CMD ["python3", "bot.py"]
