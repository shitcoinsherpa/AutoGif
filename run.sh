#!/usr/bin/env bash
# AutoGIF Runner for Unix-like systems (macOS/Linux)
# Activates venv and starts the Gradio UI

set -e  # Exit on error

echo "==============================================="
echo "                     AutoGIF"
echo "==============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
    echo -e "${GREEN}Virtual environment activated.${NC}"
else
    echo -e "${YELLOW}WARNING: Virtual environment not found at .venv/${NC}"
    echo "Running with system Python installation."
    echo ""
    echo "To create virtual environment, run: ./build.sh"
    echo ""
fi

# Check for required binaries
echo "Checking required binaries..."
MISSING_BINARIES=()

# Check platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
else
    PLATFORM="unknown"
fi

# Check for ffmpeg
if [ -f "resources/ffmpeg" ]; then
    echo -e "${GREEN}✓${NC} Found bundled ffmpeg"
elif command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}!${NC} Using system ffmpeg"
else
    MISSING_BINARIES+=("ffmpeg")
fi

# Check for yt-dlp
if [ -f "resources/yt-dlp" ]; then
    echo -e "${GREEN}✓${NC} Found bundled yt-dlp"
elif command -v yt-dlp &> /dev/null; then
    echo -e "${YELLOW}!${NC} Using system yt-dlp"
else
    MISSING_BINARIES+=("yt-dlp")
fi

# Report missing binaries
if [ ${#MISSING_BINARIES[@]} -ne 0 ]; then
    echo ""
    echo -e "${RED}ERROR: Missing required binaries:${NC}"
    for binary in "${MISSING_BINARIES[@]}"; do
        echo "  - $binary"
    done
    echo ""
    echo "Please download platform-specific binaries from:"
    echo "  ffmpeg: https://ffmpeg.org/download.html"
    echo "  yt-dlp: https://github.com/yt-dlp/yt-dlp/releases"
    echo ""
    echo "Place them in the 'resources' directory."
    exit 1
fi

echo ""
echo "Starting AutoGIF application..."
echo ""

# Set environment variables to reduce noise
export PYTHONWARNINGS="ignore::DeprecationWarning:ctranslate2"

# Run the application
if command -v python3 &> /dev/null; then
    python3 -m autogif.main
else
    python -m autogif.main
fi

# Check if the app exited with an error
if [ $? -ne 0 ]; then
    echo ""
    echo "==============================================="
    echo -e "${RED}Application exited with an error.${NC}"
    echo "==============================================="
fi

echo ""
echo "AutoGIF has stopped."

# Keep terminal open on macOS when double-clicked
if [[ "$OSTYPE" == "darwin"* ]]; then
    read -n 1 -s -r -p "Press any key to continue..."
fi 