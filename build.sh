#!/usr/bin/env bash
# AutoGIF Build Script for Unix-like systems (macOS/Linux)
# Creates virtual environment and installs dependencies

set -e  # Exit on error

echo "==============================================="
echo "          AutoGIF Build Script"
echo "==============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}Error: Python not found. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}Error: Python 3.10 or higher is required. Found: Python $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}Error: Failed to create virtual environment${NC}"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Build complete!${NC}"
echo ""
echo "To run AutoGIF, use: ./run.sh"
echo ""

# Keep terminal open on macOS when double-clicked
if [[ "$OSTYPE" == "darwin"* ]]; then
    read -n 1 -s -r -p "Press any key to continue..."
fi 