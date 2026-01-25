@echo off
REM =============================================================================
REM GEOSPATIAL RAG - HOME PC SETUP SCRIPT (Windows)
REM =============================================================================
REM This script sets up Docker, Ollama, and Tailscale on your Home PC
REM Run as Administrator!
REM =============================================================================

echo.
echo ============================================================
echo   GEOSPATIAL RAG - HOME PC SETUP
echo   RTX 3060 Ti + Ryzen 9 3900X
echo ============================================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [Step 1/5] Checking NVIDIA Driver...
nvidia-smi >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: NVIDIA driver not detected!
    echo Please install NVIDIA drivers from: https://www.nvidia.com/drivers
    pause
    exit /b 1
)
echo NVIDIA Driver: OK
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
echo.

echo [Step 2/5] Installing Docker Desktop...
echo.
echo Please follow these steps:
echo   1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
echo   2. Run the installer
echo   3. During installation, ensure "Use WSL 2 instead of Hyper-V" is checked
echo   4. Restart your computer when prompted
echo   5. After restart, run this script again
echo.
echo If Docker is already installed, press any key to continue...
pause >nul

REM Check if Docker is running
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Docker is not installed or not running!
    echo Please install Docker Desktop and restart your computer.
    pause
    exit /b 1
)
echo Docker: OK
docker --version
echo.

echo [Step 3/5] Configuring Docker for NVIDIA GPU...
echo.
echo Please ensure in Docker Desktop:
echo   Settings -> Resources -> WSL Integration -> Enable for your distro
echo   OR
echo   Settings -> Docker Engine -> Add GPU support
echo.
echo Press any key when Docker Desktop is configured...
pause >nul

echo [Step 4/5] Starting Ollama Container...
cd /d "%~dp0"
docker-compose up -d

if %errorLevel% neq 0 (
    echo ERROR: Failed to start Docker container!
    echo Please check Docker Desktop is running.
    pause
    exit /b 1
)

echo Waiting for Ollama to start...
timeout /t 10 /nobreak >nul

echo.
echo [Step 5/5] Downloading AI Models...
echo This may take 10-20 minutes depending on your internet speed...
echo.

REM Pull the main model (Qwen 2.5 7B)
echo Downloading Qwen 2.5 7B (recommended for SQL generation)...
docker exec geospatial-ollama ollama pull qwen2.5:7b

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo Ollama is running at: http://localhost:11434
echo.
echo To test, open a new terminal and run:
echo   curl http://localhost:11434/api/tags
echo.
echo Next step: Install Tailscale for remote access
echo   1. Download from: https://tailscale.com/download/windows
echo   2. Install and sign in
echo   3. Note your Tailscale IP (starts with 100.x.x.x)
echo   4. Share this IP with your laptop setup
echo.
echo ============================================================
pause
