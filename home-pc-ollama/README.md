# 🏠 Geospatial RAG - Home PC Setup

## Overview

This folder contains everything needed to set up the **LLM Server** on your Home PC.

Your Home PC (RTX 3060 Ti + Ryzen 9 3900X) will run:
- **Ollama** with NVIDIA CUDA acceleration
- **Qwen 2.5 7B** model for SQL generation, routing, and analysis
- **Tailscale** for secure remote access from your office laptop

---

## 📋 Prerequisites

| Requirement | Status | Notes |
|-------------|--------|-------|
| Windows 10/11 | ✅ | You have this |
| NVIDIA Driver | ✅ | You have this |
| Docker Desktop | ❌ | Need to install |
| Tailscale | ❌ | Need to install |
| Internet | ✅ | For downloading models (~5GB) |

---

## 🚀 Installation Steps

### Step 1: Install Docker Desktop (15 minutes)

1. **Download Docker Desktop:**
   - Go to: https://www.docker.com/products/docker-desktop
   - Click "Download for Windows"

2. **Run the installer:**
   - Double-click the downloaded file
   - ✅ Check "Use WSL 2 instead of Hyper-V" (recommended)
   - ✅ Check "Add shortcut to desktop"
   - Click "Install"

3. **Restart your computer** when prompted

4. **After restart:**
   - Docker Desktop should start automatically
   - Accept the license agreement
   - Skip the tutorial

5. **Configure Docker for GPU:**
   - Open Docker Desktop
   - Go to Settings (gear icon)
   - Resources → WSL Integration → Enable
   - Apply & Restart

### Step 2: Install NVIDIA Container Toolkit (5 minutes)

Open **PowerShell as Administrator** and run:

```powershell
# Check if WSL is installed
wsl --status

# If not installed, run:
wsl --install

# Restart computer, then continue...
```

After WSL is ready, the Docker Desktop with WSL 2 backend automatically supports NVIDIA GPUs.

### Step 3: Start Ollama (5 minutes)

1. **Open Command Prompt** in this folder

2. **Run Docker Compose:**
   ```cmd
   cd home-pc-ollama
   docker-compose up -d
   ```

3. **Wait for container to start** (about 30 seconds)

4. **Verify it's running:**
   ```cmd
   docker ps
   ```
   You should see `geospatial-ollama` in the list.

### Step 4: Download AI Models (10-20 minutes)

Run the model download script:

```cmd
scripts\pull-models.bat
```

Or manually:

```cmd
docker exec geospatial-ollama ollama pull qwen2.5:7b
```

### Step 5: Test Everything

1. **Test the API:**
   ```cmd
   curl http://localhost:11434/api/tags
   ```
   Should return a JSON list of models.

2. **Test GPU acceleration:**
   ```cmd
   scripts\test-gpu.bat
   ```

3. **Test a prompt:**
   ```cmd
   curl http://localhost:11434/api/generate -d "{\"model\": \"qwen2.5:7b\", \"prompt\": \"Hello!\", \"stream\": false}"
   ```

### Step 6: Install Tailscale (5 minutes)

1. **Download Tailscale:**
   - Go to: https://tailscale.com/download/windows
   - Download and run the installer

2. **Sign in:**
   - Use Google, Microsoft, or GitHub account
   - Or create a new Tailscale account

3. **Note your Tailscale IP:**
   - Click the Tailscale icon in system tray
   - Look for "My IP: 100.x.x.x"
   - **Save this IP** - you'll need it for your laptop!

4. **Verify Ollama is accessible:**
   - From another device on Tailscale:
   ```cmd
   curl http://100.x.x.x:11434/api/tags
   ```

---

## 📁 Files in This Folder

```
home-pc-ollama/
├── docker-compose.yml      # Docker configuration
├── scripts/
│   ├── install.bat         # Full installation script
│   ├── pull-models.bat     # Download AI models
│   └── test-gpu.bat        # Verify GPU is working
└── README.md               # This file
```

---

## 🔧 Common Commands

### Start Ollama
```cmd
docker-compose up -d
```

### Stop Ollama
```cmd
docker-compose down
```

### View Logs
```cmd
docker logs geospatial-ollama -f
```

### Restart Ollama
```cmd
docker-compose restart
```

### Check GPU Usage
```cmd
nvidia-smi
```

### List Downloaded Models
```cmd
docker exec geospatial-ollama ollama list
```

### Pull a New Model
```cmd
docker exec geospatial-ollama ollama pull <model-name>
```

---

## 🔥 Troubleshooting

### "NVIDIA driver not found" in container

1. Make sure Docker Desktop is using WSL 2 backend
2. Restart Docker Desktop
3. Run: `docker-compose down && docker-compose up -d`

### "Cannot connect to Docker daemon"

1. Open Docker Desktop application
2. Wait for it to fully start (whale icon stops animating)
3. Try again

### Slow inference (>30 seconds for simple prompts)

GPU might not be enabled:
1. Run `scripts\test-gpu.bat`
2. Check if `nvidia-smi` works inside container
3. Ensure Docker Desktop has GPU access enabled

### "Port 11434 already in use"

Another Ollama instance is running:
```cmd
# Find and stop it
netstat -ano | findstr 11434
taskkill /PID <pid> /F
```

### Tailscale can't connect

1. Make sure Tailscale is running on both devices
2. Both devices must be signed into same Tailscale account
3. Check Windows Firewall isn't blocking port 11434

---

## 📊 Resource Usage

Expected resource usage when running:

| Resource | Idle | During Inference |
|----------|------|------------------|
| GPU VRAM | ~5GB | ~6-7GB |
| System RAM | ~2GB | ~4GB |
| CPU | ~1% | ~20-40% |
| Disk | ~8GB | ~8GB |

---

## ⏭️ Next Steps

After completing this setup:

1. ✅ Home PC is running Ollama with GPU
2. ✅ Tailscale is installed and you have your IP
3. 👉 **Go to your laptop and set up the backend**
4. 👉 Configure the laptop to connect to `100.x.x.x:11434`

---

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run `scripts\test-gpu.bat` and note the output
3. Check Docker logs: `docker logs geospatial-ollama`
