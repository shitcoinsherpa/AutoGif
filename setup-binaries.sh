#!/usr/bin/env bash
# AutoGIF Binary Setup Script
# Downloads platform-specific binaries for ffmpeg, yt-dlp, and whisper

set -e

echo "==============================================="
echo "       AutoGIF Binary Setup Script"
echo "==============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    ARCH=$(uname -m)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    ARCH=$(uname -m)
else
    echo -e "${RED}Unsupported platform: $OSTYPE${NC}"
    echo "This script is for macOS and Linux only."
    exit 1
fi

echo "Detected platform: $PLATFORM ($ARCH)"
echo ""

# Create resources directory
mkdir -p resources

# Function to download with progress
download_with_progress() {
    local url=$1
    local output=$2
    echo "Downloading from: $url"
    if command -v wget &> /dev/null; then
        wget --show-progress -q -O "$output" "$url"
    elif command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$output" "$url"
    else
        echo -e "${RED}Error: Neither wget nor curl found. Please install one.${NC}"
        exit 1
    fi
}

# Download yt-dlp
echo "📥 Downloading yt-dlp..."
if [[ "$PLATFORM" == "macos" ]]; then
    YT_DLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
else
    YT_DLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
fi

download_with_progress "$YT_DLP_URL" "resources/yt-dlp"
chmod +x resources/yt-dlp
echo -e "${GREEN}✓ yt-dlp downloaded${NC}"
echo ""

# FFmpeg setup
echo "📥 Setting up FFmpeg..."
if [[ "$PLATFORM" == "macos" ]]; then
    if command -v brew &> /dev/null; then
        echo "Homebrew detected. Installing ffmpeg..."
        brew install ffmpeg
        echo -e "${GREEN}✓ FFmpeg installed via Homebrew${NC}"
    else
        echo -e "${YELLOW}Homebrew not found. Please install FFmpeg manually:${NC}"
        echo "1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "2. Run: brew install ffmpeg"
        echo ""
        echo "Or download static builds from: https://evermeet.cx/ffmpeg/"
    fi
elif [[ "$PLATFORM" == "linux" ]]; then
    echo "Downloading static FFmpeg build..."
    if [[ "$ARCH" == "x86_64" ]]; then
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    elif [[ "$ARCH" == "aarch64" ]]; then
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
    else
        echo -e "${RED}Unsupported architecture: $ARCH${NC}"
        echo "Please download FFmpeg manually from: https://ffmpeg.org/download.html"
        exit 1
    fi
    
    # Download and extract
    echo "Downloading FFmpeg..."
    download_with_progress "$FFMPEG_URL" "/tmp/ffmpeg.tar.xz"
    
    echo "Extracting FFmpeg..."
    tar -xf /tmp/ffmpeg.tar.xz -C /tmp/
    
    # Find the extracted directory
    FFMPEG_DIR=$(find /tmp -maxdepth 1 -name "ffmpeg-*-static" -type d | head -n 1)
    
    if [[ -n "$FFMPEG_DIR" ]]; then
        cp "$FFMPEG_DIR/ffmpeg" resources/
        cp "$FFMPEG_DIR/ffprobe" resources/
        chmod +x resources/ffmpeg resources/ffprobe
        rm -rf "$FFMPEG_DIR" /tmp/ffmpeg.tar.xz
        echo -e "${GREEN}✓ FFmpeg downloaded and extracted${NC}"
    else
        echo -e "${RED}Error: Could not extract FFmpeg${NC}"
        exit 1
    fi
fi
echo ""

# Whisper setup (optional)
echo "📥 Whisper setup (optional)..."
echo -e "${YELLOW}Note: Whisper binary is optional. AutoGIF will use faster-whisper Python package as fallback.${NC}"
echo ""

# Summary
echo "==============================================="
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Binaries installed in resources/:"
ls -la resources/ | grep -E "(yt-dlp|ffmpeg|ffprobe)" || true
echo ""
echo "You can now run: ./build.sh"
echo "===============================================" 