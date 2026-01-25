@echo off
echo Checking if port 8000 is in use...
netstat -ano | findstr :8000
if %errorlevel% == 0 (
    echo.
    echo Port 8000 is already in use!
    echo.
    echo To fix this:
    echo 1. Find the process using port 8000 (see PID above)
    echo 2. Kill it: taskkill /PID [PID_NUMBER] /F
    echo 3. Or use a different port: uvicorn main:app --port 8001
    echo.
) else (
    echo Port 8000 is available.
)
pause
