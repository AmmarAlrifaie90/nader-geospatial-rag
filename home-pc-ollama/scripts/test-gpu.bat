@echo off
REM =============================================================================
REM GEOSPATIAL RAG - TEST GPU ACCELERATION
REM =============================================================================

echo.
echo ============================================================
echo   TESTING NVIDIA GPU FOR OLLAMA
echo ============================================================
echo.

echo [1/4] Checking NVIDIA Driver...
nvidia-smi
echo.

echo [2/4] Checking Docker Container...
docker ps | findstr geospatial-ollama
if %errorLevel% neq 0 (
    echo ERROR: Ollama container is not running!
    echo Run: docker-compose up -d
    pause
    exit /b 1
)
echo.

echo [3/4] Checking GPU inside Container...
docker exec geospatial-ollama nvidia-smi
echo.

echo [4/4] Running inference speed test...
echo Timing a simple prompt (should be under 5 seconds with GPU)...

powershell -Command "Measure-Command { Invoke-RestMethod -Uri 'http://localhost:11434/api/generate' -Method Post -Body '{\"model\": \"qwen2.5:7b\", \"prompt\": \"What is 2+2?\", \"stream\": false}' -ContentType 'application/json' } | Select-Object TotalSeconds"

echo.
echo ============================================================
echo   GPU TEST COMPLETE
echo ============================================================
echo.
echo If TotalSeconds is under 5, GPU acceleration is working!
echo If TotalSeconds is over 30, GPU may not be properly configured.
echo.
pause
