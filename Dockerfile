FROM python:3.11-slim

# Install system deps for archive extraction
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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["python3", "bot.py"]
