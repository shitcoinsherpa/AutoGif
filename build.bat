@echo off
REM Deletes any existing .venv, creates a fresh virtual environment, upgrades pip, installs from requirements.txt, then pauses.

echo Deleting existing virtual environment...
if exist .venv (
    rmdir /s /q .venv
)

echo Creating fresh virtual environment...
python -m venv .venv

echo Activating virtual environment and upgrading pip...
call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
.venv\Scripts\pip install -r requirements.txt

echo Build process complete.
pause 