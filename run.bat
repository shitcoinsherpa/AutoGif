@echo off
REM AutoGIF Runner - Activates venv and starts the Gradio UI

echo ===============================================
echo                     AutoGIF
echo ===============================================
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo WARNING: Virtual environment not found at .venv\
    echo Running with system Python installation.
    echo.
    echo To create virtual environment, run: build.bat
    echo.
)

echo Starting AutoGIF application...
echo.

REM Set environment variables to reduce noise
REM Suppress pkg_resources deprecation warning from ctranslate2
set PYTHONWARNINGS=ignore::DeprecationWarning:ctranslate2

REM Run the application
python -m autogif.main

REM Check if the app exited with an error
if errorlevel 1 (
    echo.
    echo ===============================================
    echo Application exited with an error code.
    echo ===============================================
)

echo.
echo AutoGIF has stopped.
pause
exit /b 