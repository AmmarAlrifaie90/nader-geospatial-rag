# 🌍 NADER - Geospatial RAG System

**NADER** is an intelligent geospatial query and analysis system that uses Retrieval-Augmented Generation (RAG) and agentic AI to interact with mining/geological databases through natural language.

## 🎯 Project Overview

NADER combines:
- **RAG (Retrieval-Augmented Generation)**: Enhances LLM with database context
- **Agentic Architecture**: Intelligent tool routing and decision-making
- **Spatial Analysis**: Advanced PostGIS queries and clustering
- **ML Prediction**: Prospectivity prediction using ensemble models
- **Voice Interface**: Arabic voice input/output pipeline
- **Interactive Visualization**: 2D/3D maps with dynamic filtering

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Natural Language Queries** | Ask questions in plain English or Arabic |
| 🗺️ **2D Map Visualization** | Leaflet-based interactive maps |
| 🏔️ **3D Visualization** | CesiumJS globe with terrain |
| 📊 **Spatial Analysis** | Clustering, buffers, statistics |
| 📥 **Data Export** | GeoJSON and Shapefile formats |
| 🎤 **Voice I/O** | Speech-to-text and text-to-speech |
| 🤖 **Local LLM** | Privacy-focused, runs on your hardware |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OFFICE LAPTOP                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────────────┐  │
│  │ Browser │◄──►│ FastAPI │◄──►│       PostGIS           │  │
│  │Frontend │    │ Backend │    │ (mods, borholes,        │  │
│  │         │    │         │    │  surface_samples)       │  │
│  └─────────┘    └────┬────┘    └─────────────────────────┘  │
└──────────────────────┼──────────────────────────────────────┘
                       │ Tailscale
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    HOME PC                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Docker + Ollama                         │    │
│  │         Qwen 2.5 7B (GPU Accelerated)               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Components

### 1. Home PC (LLM Server)
- **Location:** `home-pc-ollama/`
- **Purpose:** Runs Ollama with GPU acceleration
- **Requirements:** RTX 3060 Ti or better, Docker

### 2. Backend (FastAPI)
- **Location:** `backend/`
- **Purpose:** API server, database access, tool orchestration
- **Requirements:** Python 3.10+, PostGIS

### 3. Frontend (Web UI)
- **Location:** `frontend/`
- **Purpose:** User interface, maps, chat
- **Requirements:** Modern web browser

## 🚀 Quick Start

### Step 1: Setup Home PC (20 minutes)

```bash
# On your Home PC (RTX 3060 Ti)
cd home-pc-ollama

# Install Docker Desktop, then:
docker-compose up -d

# Download the AI model
docker exec geospatial-ollama ollama pull qwen2.5:7b

# Install Tailscale and note your IP (100.x.x.x)
```

### Step 2: Setup Backend (10 minutes)

```bash
# On your Laptop
cd backend

# Create environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env with your Tailscale IP and database credentials

# Run
python main.py
```

### Step 3: Open Frontend

```bash
# Serve the frontend (or open index.html directly)
cd frontend
python -m http.server 8080

# Open http://localhost:8080 in your browser
```

## 💬 Example Queries

| Query | Tool Used | Description |
|-------|-----------|-------------|
| "Find all gold deposits" | SQL Generator | Search by commodity |
| "Show copper sites on map" | 2D Visualizer | Map visualization |
| "Display boreholes in 3D" | 3D Visualizer | CesiumJS globe |
| "Cluster analysis of mineral sites" | Analyzer | Spatial analysis |
| "Export gold sites to GeoJSON" | Exporter | File download |
| "أين مواقع الذهب؟" | SQL Generator | Arabic support |

## 🗄️ Database Schema

### Tables

| Table | Description | Records |
|-------|-------------|---------|
| `mods` | Mineral Occurrence Documentation System | Mining sites |
| `borholes` | Borehole drilling data | Drill holes |
| `surface_samples` | Surface geological samples | Field samples |

### Key Fields

- **mods:** `eng_name`, `arb_name`, `major_comm`, `minor_comm`, `region`, `occ_imp`
- **borholes:** `project_na`, `borehole_i`, `elements`
- **surface_samples:** `sampleid`, `sampletype`, `elements`

## 📋 Requirements

### Home PC (LLM Server)
- Windows 10/11
- NVIDIA GPU (RTX 3060 Ti or better)
- 16GB RAM
- Docker Desktop
- Tailscale

### Laptop (Backend)
- Windows 10/11
- Python 3.10+
- PostgreSQL with PostGIS
- Tailscale
- Google Cloud account (optional, for voice)

## 🔧 Configuration

### Environment Variables

```env
# Ollama (Home PC)
OLLAMA_BASE_URL=http://100.x.x.x:11434
OLLAMA_MODEL=qwen2.5:7b

# Database
POSTGRES_HOST=localhost
POSTGRES_DATABASE=geodatabase

# Google Cloud (Voice)
GOOGLE_CLOUD_CREDENTIALS=./credentials/key.json

# Cesium (3D)
CESIUM_ION_TOKEN=your_token
```

## 📖 Documentation

- [Home PC Setup](home-pc-ollama/README.md)
- [Backend Setup](backend/README.md)
- [API Reference](backend/README.md#api-endpoints)

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to Ollama" | Check Tailscale connection, verify IP |
| "Database error" | Check PostgreSQL is running, verify credentials |
| "Voice not working" | Check Google Cloud credentials and API quota |
| "3D map blank" | Get free Cesium Ion token |
| "Slow responses" | Check GPU is being used (`nvidia-smi`) |

## 🔒 Security Notes

- **Never commit `.env` file** - It contains sensitive credentials
- Use `.env.example` as a template
- Keep API keys and passwords secure
- Review `.gitignore` before pushing to GitHub

## 📄 License

MIT License - Use freely for personal and commercial projects.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) - Local LLM runtime
- [Qwen](https://github.com/QwenLM/Qwen) - AI model
- [Mapbox](https://www.mapbox.com) - Map visualization
- [Deck.gl](https://deck.gl) - 3D visualization
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [PostGIS](https://postgis.net) - Spatial database
- [Whisper](https://github.com/openai/whisper) - Speech recognition
