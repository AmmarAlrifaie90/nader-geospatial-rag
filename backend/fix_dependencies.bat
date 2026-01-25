@echo off
echo ========================================
echo Fixing Dependencies for Windows
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Installing NumPy (pre-built wheel)...
pip install --upgrade pip
pip install --only-binary :all: numpy

echo.
echo Installing other dependencies...
pip install fastapi uvicorn python-multipart
pip install psycopg2-binary
pip install sqlalchemy geoalchemy2
pip install httpx aiohttp
pip install python-dotenv pydantic pydantic-settings
pip install pydub
pip install geojson
pip install asyncio-throttle

echo.
echo Installing ChromaDB...
pip install chromadb

echo.
echo Installing geopandas (this may take a while)...
pip install geopandas

echo.
echo ========================================
echo Dependencies installed!
echo ========================================
pause
