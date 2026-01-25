# 🔧 Troubleshooting Guide

## Issue 1: NumPy Build Error (Missing C Compiler)

**Error:**
```
ERROR: Unknown compiler(s): [['icl'], ['cl'], ['cc'], ['gcc'], ['clang']]
```

**Solution:**

### Option A: Use Pre-built Wheels (Recommended)
```bash
# Activate venv
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install NumPy from pre-built wheel
pip install --only-binary :all: numpy

# Then install other packages
pip install -r requirements.txt
```

### Option B: Use the Fix Script
```bash
fix_dependencies.bat
```

### Option C: Install Visual Studio Build Tools
1. Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
2. Install "C++ build tools" workload
3. Restart terminal and try again

---

## Issue 2: Port 8000 Already in Use

**Error:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Solution:**

### Step 1: Find What's Using Port 8000
```bash
netstat -ano | findstr :8000
```

This shows the PID (Process ID) using the port.

### Step 2: Kill the Process
```bash
taskkill /PID [PID_NUMBER] /F
```

Replace `[PID_NUMBER]` with the actual PID from Step 1.

### Step 3: Or Use Different Port
```bash
uvicorn main:app --port 8001
```

Then access at: `http://localhost:8001`

### Quick Check Script
```bash
check_port.bat
```

---

## Issue 3: ChromaDB Not Installed

**Error:**
```
WARNING:root:ChromaDB not installed
```

**Solution:**
```bash
pip install chromadb
```

---

## Issue 4: Database Connection Failed

**Error:**
```
✗ Database connection failed
```

**Solution:**

1. **Check PostgreSQL is running:**
   ```bash
   pg_isready
   ```

2. **Verify credentials in `.env`:**
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_DATABASE=geodatabase
   ```

3. **Test connection manually:**
   ```bash
   psql -h localhost -U postgres -d geodatabase
   ```

---

## Issue 5: Ollama Connection Failed

**Error:**
```
✗ Ollama LLM server not available
```

**Solution:**

1. **Check Home PC is running**
2. **Verify Tailscale is connected:**
   ```bash
   # On laptop
   tailscale status
   ```

3. **Test Ollama directly:**
   ```bash
   curl http://YOUR_TAILSCALE_IP:11434/api/tags
   ```

4. **Update `.env` with correct IP:**
   ```env
   OLLAMA_BASE_URL=http://100.100.100.100:11434
   ```

---

## Issue 6: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:**

1. **Make sure venv is activated:**
   ```bash
   venv\Scripts\activate
   ```

2. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check if module exists:**
   ```bash
   pip list | findstr module_name
   ```

---

## Issue 7: Geopandas Installation Fails

**Error:**
```
ERROR: Failed building wheel for geopandas
```

**Solution:**

1. **Install dependencies first:**
   ```bash
   pip install --only-binary :all: numpy
   pip install --only-binary :all: pandas
   pip install --only-binary :all: shapely
   pip install geopandas
   ```

2. **Or use conda (if available):**
   ```bash
   conda install -c conda-forge geopandas
   ```

---

## Quick Fix Commands

### Complete Reset (if nothing works)
```bash
# Delete venv
rmdir /s venv

# Create new venv
python -m venv venv
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install NumPy first (pre-built)
pip install --only-binary :all: numpy

# Install everything else
pip install -r requirements.txt
pip install chromadb
```

---

## Still Having Issues?

1. **Check Python version:**
   ```bash
   python --version
   ```
   Should be 3.10 or higher.

2. **Check pip version:**
   ```bash
   pip --version
   ```
   Upgrade if old: `python -m pip install --upgrade pip`

3. **Check all services:**
   - PostgreSQL running?
   - Ollama accessible?
   - Tailscale connected?

4. **Check logs:**
   - Look at the error message carefully
   - Check if it's a missing dependency or connection issue

---

## Common Solutions Summary

| Issue | Quick Fix |
|-------|-----------|
| NumPy build error | `pip install --only-binary :all: numpy` |
| Port in use | `taskkill /PID [PID] /F` or use port 8001 |
| ChromaDB missing | `pip install chromadb` |
| Database error | Check `.env` and PostgreSQL status |
| Ollama error | Check Tailscale and IP address |
| Module not found | Activate venv and reinstall |
