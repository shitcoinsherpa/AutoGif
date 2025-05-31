# AutoGIF Docker Image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY autogif/ ./autogif/
COPY resources/fonts/ ./resources/fonts/
COPY resources/*.exe ./resources/
COPY resources/icon.ico ./resources/

# Download Linux binaries
RUN mkdir -p resources && \
    wget -q https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O resources/yt-dlp && \
    chmod +x resources/yt-dlp && \
    wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*/ffmpeg resources/ && \
    cp ffmpeg-*/ffprobe resources/ && \
    chmod +x resources/ffmpeg resources/ffprobe && \
    rm -rf ffmpeg-*

# Create temp directory
RUN mkdir -p _autogif_temp

# Expose Gradio port
EXPOSE 7860

# Set environment variables
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"

# Run the application
CMD ["python", "-m", "autogif.main"] 