.PHONY: help install run clean test lint format docs requirements check-python download-binaries

# Default Python command
PYTHON := python3
PIP := pip3

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    PLATFORM := macos
    SCRIPT_EXT := sh
else ifeq ($(UNAME_S),Linux)
    PLATFORM := linux
    SCRIPT_EXT := sh
else
    PLATFORM := windows
    SCRIPT_EXT := bat
    PYTHON := python
    PIP := pip
endif

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-python: ## Check Python version
	@echo "Checking Python version..."
	@$(PYTHON) -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" || \
		(echo "Error: Python 3.10+ required" && exit 1)
	@echo "Python version OK"

install: check-python ## Install dependencies in virtual environment
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv .venv
	@echo "Activating virtual environment and installing dependencies..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt
else
	@. .venv/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt
endif
	@echo "Installation complete!"

run: ## Run AutoGIF application
ifeq ($(PLATFORM),windows)
	@run.bat
else
	@chmod +x run.sh && ./run.sh
endif

clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf _autogif_temp/ 2>/dev/null || true
	@rm -rf .coverage htmlcov/ 2>/dev/null || true
	@rm -rf dist/ build/ *.egg-info/ 2>/dev/null || true
	@echo "Cleanup complete!"

test: ## Run tests
	@echo "Running tests..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && pytest tests/ -v
else
	@. .venv/bin/activate && pytest tests/ -v
endif

lint: ## Run code linting
	@echo "Running linters..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && flake8 autogif/ --max-line-length=120
else
	@. .venv/bin/activate && flake8 autogif/ --max-line-length=120
endif

format: ## Format code with black
	@echo "Formatting code..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && black autogif/
else
	@. .venv/bin/activate && black autogif/
endif

docs: ## Build documentation
	@echo "Building documentation..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && cd docs && make html
else
	@. .venv/bin/activate && cd docs && make html
endif

requirements: ## Update requirements.txt
	@echo "Updating requirements.txt..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && pip freeze > requirements.txt
else
	@. .venv/bin/activate && pip freeze > requirements.txt
endif

download-binaries: ## Download platform-specific binaries
	@echo "Downloading binaries for $(PLATFORM)..."
ifeq ($(PLATFORM),macos)
	@mkdir -p resources
	@echo "Downloading yt-dlp..."
	@curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o resources/yt-dlp
	@chmod +x resources/yt-dlp
	@echo "Please install ffmpeg using: brew install ffmpeg"
else ifeq ($(PLATFORM),linux)
	@mkdir -p resources
	@echo "Downloading yt-dlp..."
	@wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O resources/yt-dlp
	@chmod +x resources/yt-dlp
	@echo "Please install ffmpeg using your package manager"
else
	@echo "Windows binaries are already included in resources/"
endif

dev-install: install ## Install development dependencies
	@echo "Installing development dependencies..."
ifeq ($(PLATFORM),windows)
	@.venv\Scripts\activate.bat && $(PIP) install pytest flake8 black sphinx
else
	@. .venv/bin/activate && $(PIP) install pytest flake8 black sphinx
endif

docker-build: ## Build Docker image
	@docker build -t autogif:latest .

docker-run: ## Run in Docker container
	@docker run -it --rm -p 7860:7860 autogif:latest 