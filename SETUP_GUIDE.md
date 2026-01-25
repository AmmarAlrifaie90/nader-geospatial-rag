# 📋 Complete Setup Guide - Geospatial RAG

## Overview

This guide walks you through the complete setup process step by step.

**Time Required:** ~1 hour total
- Home PC setup: 30 minutes
- Laptop setup: 20 minutes  
- Testing: 10 minutes

---

## Part 1: Home PC Setup (RTX 3060 Ti)

### Step 1.1: Install Docker Desktop

1. Download Docker Desktop:
   - Go to: https://www.docker.com/products/docker-desktop
   - Click "Download for Windows"

2. Run the installer:
   - Double-click the downloaded file
   - ✅ Check "Use WSL 2 instead of Hyper-V"
   - Click "Install"

3. Restart your computer

4. After restart:
   - Docker Desktop will start automatically
   - Accept the license agreement
   - Wait for Docker to fully start (whale icon stops animating)

### Step 1.2: Verify GPU Support

Open PowerShell and run:
```powershell
nvidia-smi
```

You should see your RTX 3060 Ti listed.

### Step 1.3: Start Ollama

1. Open Command Prompt in the `home-pc-ollama` folder

2. Run:
```cmd
docker-compose up -d
```

3. Wait 30 seconds, then verify:
```cmd
docker ps
```
You should see `geospatial-ollama` running.

### Step 1.4: Download AI Model

```cmd
docker exec geospatial-ollama ollama pull qwen2.5:7b
```

This downloads ~5GB. Wait for it to complete.

### Step 1.5: Test the LLM

```cmd
curl http://localhost:11434/api/generate -d "{\"model\": \"qwen2.5:7b\", \"prompt\": \"Hello\", \"stream\": false}"
```

You should get a response within a few seconds.

### Step 1.6: Install Tailscale

1. Download: https://tailscale.com/download/windows
2. Install and sign in (Google, Microsoft, or GitHub)
3. Note your Tailscale IP:
   - Click Tailscale icon in system tray
   - Look for "My IP: 100.x.x.x"
   - **Save this IP!** You'll need it for the laptop.

---

## Part 2: Laptop Setup

### Step 2.1: Install Tailscale on Laptop

1. Download: https://tailscale.com/download/windows
2. Install and sign in with the **same account** as Home PC
3. Verify connection:
```cmd
ping 100.x.x.x
```
(Replace with your Home PC's Tailscale IP)

### Step 2.2: Verify PostGIS

Make sure your PostGIS database is running with the mining data.

Test connection:
```cmd
psql -h localhost -U postgres -d geodatabase -c "SELECT COUNT(*) FROM mods;"
```

### Step 2.3: Setup Python Environment

```cmd
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2.4: Configure Environment

```cmd
copy .env.example .env
```

Edit `.env` with notepad:
```cmd
notepad .env
```

Update these values:
```env
# Your Home PC's Tailscale IP
OLLAMA_BASE_URL=http://100.x.x.x:11434

# Your database password
POSTGRES_PASSWORD=your_actual_password
```

### Step 2.5: Start Backend

```cmd
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
✓ PostGIS database connected
✓ Ollama LLM server connected
```

### Step 2.6: Open Frontend

Option A - Direct file:
- Open `frontend/index.html` in your browser

Option B - Local server:
```cmd
cd frontend
python -m http.server 8080
```
Then open: http://localhost:8080

---

## Part 3: Testing

### Test 1: Basic Query

In the chat, type:
```
Find all gold deposits
```

Expected: Results appear, map shows points

### Test 2: Spatial Query

```
Show mineral sites within 50km of coordinates 24.5, 40.3
```

Expected: Points near that location

### Test 3: 3D Visualization

```
Show boreholes in 3D
```

Expected: 3D globe with points (note: needs Cesium token for terrain)

### Test 4: Export

```
Export copper sites to GeoJSON
```

Expected: Download link appears

---

## Part 4: Optional - Google Cloud Voice Setup

### Step 4.1: Create Google Cloud Project

1. Go to: https://console.cloud.google.com
2. Create new project: "Geospatial RAG"

### Step 4.2: Enable APIs

1. Go to: APIs & Services > Library
2. Search and enable:
   - "Cloud Speech-to-Text API"
   - "Cloud Text-to-Speech API"

### Step 4.3: Create Service Account

1. Go to: IAM & Admin > Service Accounts
2. Click "Create Service Account"
3. Name: "geospatial-rag-voice"
4. Grant roles:
   - Cloud Speech Client
   - Cloud Text-to-Speech Client
5. Click "Done"

### Step 4.4: Create Key

1. Click on the service account you created
2. Go to "Keys" tab
3. Add Key > Create new key > JSON
4. Download the file

### Step 4.5: Configure

1. Save the JSON file to `backend/credentials/google-cloud-key.json`
2. Update `.env`:
```env
GOOGLE_CLOUD_CREDENTIALS=./credentials/google-cloud-key.json
GOOGLE_CLOUD_PROJECT=your-project-id
```

3. Restart the backend

---

## Part 5: Optional - Cesium Ion Token

For 3D terrain visualization:

1. Go to: https://cesium.com/ion/tokens
2. Create free account
3. Copy your default access token
4. Update `.env`:
```env
CESIUM_ION_TOKEN=your_token_here
```

---

## Troubleshooting

### "Cannot connect to Ollama"

1. Check Home PC Docker is running:
```cmd
docker ps
```

2. Check Tailscale on both machines
3. Verify IP is correct in `.env`

### "Database connection failed"

1. Check PostgreSQL is running
2. Verify password in `.env`
3. Test connection:
```cmd
psql -h localhost -U postgres -d geodatabase
```

### "Slow LLM responses"

1. Check GPU is being used:
```cmd
nvidia-smi
```
You should see `ollama` process using GPU memory.

2. If not, restart Docker and Ollama:
```cmd
docker-compose down
docker-compose up -d
```

### "Voice not working"

1. Check Google Cloud credentials path
2. Verify APIs are enabled
3. Check browser microphone permissions

---

## Quick Commands Reference

### Home PC

```bash
# Start Ollama
docker-compose up -d

# Stop Ollama
docker-compose down

# View logs
docker logs geospatial-ollama -f

# Check GPU
nvidia-smi

# Pull new model
docker exec geospatial-ollama ollama pull <model>
```

### Laptop

```bash
# Activate environment
venv\Scripts\activate

# Start backend
python main.py

# Start frontend server
cd frontend && python -m http.server 8080
```

---

## Success Checklist

- [ ] Docker Desktop installed on Home PC
- [ ] Ollama container running
- [ ] Qwen 2.5 7B model downloaded
- [ ] Tailscale installed on both machines
- [ ] Home PC Tailscale IP noted
- [ ] Laptop can ping Home PC via Tailscale
- [ ] Python environment created
- [ ] Dependencies installed
- [ ] .env configured with correct IP and DB password
- [ ] Backend starts without errors
- [ ] Frontend loads in browser
- [ ] Test query returns results
- [ ] Map displays points
- [ ] (Optional) Voice input works
- [ ] (Optional) 3D terrain displays

---

**Congratulations! 🎉** Your Geospatial RAG system is ready!
