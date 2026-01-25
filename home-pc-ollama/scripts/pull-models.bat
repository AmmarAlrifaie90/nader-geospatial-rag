@echo off
REM =============================================================================
REM GEOSPATIAL RAG - PULL AI MODELS
REM =============================================================================

echo.
echo ============================================================
echo   DOWNLOADING AI MODELS FOR GEOSPATIAL RAG
echo ============================================================
echo.

echo [1/3] Pulling Qwen 2.5 7B (Main model - SQL + Routing + Analysis)...
docker exec geospatial-ollama ollama pull qwen2.5:7b

echo.
echo [2/3] Pulling Qwen 2.5 3B (Lightweight backup)...
docker exec geospatial-ollama ollama pull qwen2.5:3b

echo.
echo [3/3] Verifying models...
docker exec geospatial-ollama ollama list

echo.
echo ============================================================
echo   TESTING GPU ACCELERATION
echo ============================================================
echo.

echo Sending test prompt to verify GPU is being used...
curl -s http://localhost:11434/api/generate -d "{\"model\": \"qwen2.5:7b\", \"prompt\": \"Say hello in exactly 5 words.\", \"stream\": false}" | findstr /C:"response"

echo.
echo ============================================================
echo   ALL MODELS READY!
echo ============================================================
echo.
echo Available models:
echo   - qwen2.5:7b  (Recommended: Best for SQL and analysis)
echo   - qwen2.5:3b  (Backup: Faster but less accurate)
echo.
pause
