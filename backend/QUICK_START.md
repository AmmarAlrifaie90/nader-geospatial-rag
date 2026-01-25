# 🚀 Quick Start Guide - Run Your RAG System

## Step 1: Install Dependencies

```bash
# Navigate to backend directory
cd geospatial-rag/backend

# Activate virtual environment (if not already active)
venv\Scripts\activate

# Install/update dependencies
pip install -r requirements.txt
```

**New dependency for RAG:**
```bash
pip install chromadb
```

---

## Step 2: Configure Environment

Create a `.env` file in the `backend` directory:

```bash
# Copy from example (if exists) or create new
copy .env.example .env
# OR just create .env file manually
```

**Edit `.env` file with your settings:**

```env
# Ollama (Your Home PC Tailscale IP)
OLLAMA_BASE_URL=http://100.100.100.100:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120

# PostGIS Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_DATABASE=geodatabase

# Optional: Google Cloud (for voice features)
GOOGLE_CLOUD_CREDENTIALS=./credentials/google-cloud-key.json
GOOGLE_CLOUD_PROJECT=your-project-id

# Optional: Cesium (for 3D maps)
CESIUM_ION_TOKEN=your_token_here

# Application
DEBUG=false
APP_VERSION=1.0.0
```

**Important:** Replace:
- `100.100.100.100` with your Home PC's Tailscale IP
- `your_password_here` with your PostgreSQL password
- `geodatabase` with your actual database name

---

## Step 3: Verify Connections

### Check PostGIS Connection
```bash
# Test database connection
python -c "from database.postgis_client import get_postgis_client; db = get_postgis_client(); print('✓ Connected!' if db.health_check() else '✗ Failed')"
```

### Check Ollama Connection
```bash
# Test Ollama connection
python -c "import asyncio; from llm.ollama_client import get_ollama_client; async def test(): ollama = get_ollama_client(); result = await ollama.health_check(); print('✓ Connected!' if result else '✗ Failed'); asyncio.run(test())"
```

---

## Step 4: Index RAG Knowledge Base (Optional but Recommended)

**This indexes your database schema and query patterns into the vector store:**

```bash
# Option 1: Using API (after starting server)
curl -X POST http://localhost:8000/api/rag/index

# Option 2: Using script
python scripts/index_rag.py
```

**What it does:**
- Learns your database schema
- Indexes query patterns
- Indexes sample data
- Creates vector embeddings

---

## Step 5: Start the Server

```bash
# Option 1: Direct Python
python main.py

# Option 2: Using uvicorn (recommended)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**You should see:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ✓ PostGIS database connected
INFO:     ✓ Ollama LLM server connected
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 6: Test the System

### Test 1: Health Check
```bash
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "llm": "healthy"
  }
}
```

### Test 2: Simple Query (Text-to-SQL)
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"show me all gold deposits\"}"
```

### Test 3: RAG Query (with context retrieval)
```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"show me all gold deposits\", \"max_context_chunks\": 5}"
```

### Test 4: Spatial Join Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"show me all points inside a polygon\"}"
```

### Test 5: Synonym Handling
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"show gold deposits in areas where area is Arabian Shield\"}"
```

---

## Step 7: Check RAG Stats (if indexed)

```bash
curl http://localhost:8000/api/rag/stats
```

**Expected:**
```json
{
  "success": true,
  "collections": {
    "database_schema": {"document_count": 10},
    "query_patterns": {"document_count": 8},
    "data_samples": {"document_count": 50}
  },
  "total_documents": 68
}
```

---

## Common Issues & Solutions

### Issue 1: "Cannot connect to Ollama"
**Solution:**
- Check Home PC is running
- Verify Tailscale is connected
- Check `OLLAMA_BASE_URL` in `.env`
- Test: `curl http://YOUR_IP:11434/api/tags`

### Issue 2: "Database connection failed"
**Solution:**
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Test connection: `psql -h localhost -U postgres -d geodatabase`

### Issue 3: "ChromaDB not installed"
**Solution:**
```bash
pip install chromadb
```

### Issue 4: "Module not found"
**Solution:**
```bash
# Make sure you're in backend directory
cd geospatial-rag/backend

# Activate venv
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 5: "Port 8000 already in use"
**Solution:**
```bash
# Use different port
uvicorn main:app --port 8001
```

---

## Next Steps

1. **Index RAG knowledge base** (if not done):
   ```bash
   python scripts/index_rag.py
   ```

2. **Test with frontend** (if you have one):
   - Open `frontend/index.html` in browser
   - Or serve it: `python -m http.server 8080`

3. **Try different queries:**
   - "Find all gold deposits"
   - "Show boreholes in volcanic areas"
   - "Find points near faults"
   - "Show me all points inside polygons"

---

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/query` | POST | Natural language query (Text-to-SQL) |
| `/api/rag/query` | POST | RAG query (with context retrieval) |
| `/api/rag/index` | POST | Index knowledge base |
| `/api/rag/stats` | GET | RAG statistics |
| `/api/visualize/2d` | POST | 2D map visualization |
| `/api/visualize/3d` | POST | 3D visualization |
| `/api/analyze` | POST | Spatial analysis |
| `/api/export` | POST | Export data |
| `/api/health` | GET | Health check |
| `/api/database/tables` | GET | List tables |

---

## Success Indicators

✅ Server starts without errors  
✅ Health check returns "healthy"  
✅ Queries return results  
✅ RAG stats show indexed documents (if indexed)  
✅ SQL queries execute successfully  

**You're ready to go!** 🎉
