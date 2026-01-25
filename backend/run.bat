@echo off
echo ========================================
echo Geospatial RAG System - Startup Script
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please create .env file with your configuration.
    echo See QUICK_START.md for details.
    echo.
    pause
)

REM Install/update dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Check if ChromaDB is installed
python -c "import chromadb" 2>nul
if errorlevel 1 (
    echo Installing ChromaDB...
    pip install chromadb
)

echo.
echo ========================================
echo Starting Geospatial RAG Server...
echo ========================================
echo.
echo Server will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python main.py

pause
