# 💻 Geospatial RAG - Backend

## Overview

FastAPI backend that provides:
- Natural language to PostGIS SQL conversion
- 2D/3D visualization data preparation
- Spatial analysis
- File export (GeoJSON, Shapefile)
- Voice I/O integration

## Setup

### 1. Prerequisites

- Python 3.10+
- PostgreSQL with PostGIS
- Google Cloud account (for voice features)

### 2. Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
copy .env.example .env
```

**Required settings:**

```env
# Your Home PC Tailscale IP
OLLAMA_BASE_URL=http://100.x.x.x:11434

# Your PostgreSQL database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=geodatabase
```

### 4. Google Cloud Setup (for voice)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable APIs:
   - Cloud Speech-to-Text API
   - Cloud Text-to-Speech API
4. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Create new service account
   - Grant roles: "Cloud Speech Client" and "Cloud Text-to-Speech Client"
   - Create JSON key and download
5. Save the key file and update `.env`:
   ```env
   GOOGLE_CLOUD_CREDENTIALS=./credentials/google-cloud-key.json
   ```

### 5. Run the Backend

```bash
# Development
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | POST | Natural language query (auto-routed) |
| `/api/visualize/2d` | POST | 2D map visualization |
| `/api/visualize/3d` | POST | 3D CesiumJS visualization |
| `/api/analyze` | POST | Spatial analysis |
| `/api/export` | POST | Export to file |
| `/api/voice/query` | POST | Voice query processing |
| `/api/voice/tts` | POST | Text to speech |
| `/api/health` | GET | Health check |
| `/api/database/tables` | GET | List database tables |

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── router/
│   └── intent_router.py # LLM-based query routing
├── tools/
│   ├── tool1_sql_generator.py  # NL to SQL
│   ├── tool2_visualizer_2d.py  # Leaflet data
│   ├── tool3_visualizer_3d.py  # CesiumJS data
│   ├── tool4_analyzer.py       # Spatial analysis
│   ├── tool5_exporter.py       # File export
│   └── tool6_voice_io.py       # Voice I/O
├── database/
│   └── postgis_client.py       # Database operations
└── llm/
    └── ollama_client.py        # LLM communication
```

## Troubleshooting

### "Cannot connect to Ollama"
- Check your Home PC is running
- Verify Tailscale is connected on both machines
- Confirm the IP in `OLLAMA_BASE_URL` matches your Home PC's Tailscale IP

### "Database connection failed"
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure PostGIS extension is installed

### "Voice features not working"
- Check Google Cloud credentials path
- Verify APIs are enabled in Google Cloud Console
- Check your Google Cloud quota
