# ✅ Setup Checklist

Use this checklist to verify your system is ready to run:

## Prerequisites

- [ ] Python 3.10+ installed
- [ ] PostgreSQL with PostGIS installed and running
- [ ] Ollama running on Home PC (via Tailscale)
- [ ] Tailscale connected on both machines

## Configuration

- [ ] `.env` file created in `backend/` directory
- [ ] `OLLAMA_BASE_URL` set to your Home PC Tailscale IP
- [ ] `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` configured
- [ ] `POSTGRES_DATABASE` set to your database name

## Dependencies

- [ ] Virtual environment activated
- [ ] All packages installed: `pip install -r requirements.txt`
- [ ] ChromaDB installed: `pip install chromadb`

## Connections

- [ ] PostGIS database connection works
- [ ] Ollama connection works (from laptop to Home PC)

## RAG Setup (Optional)

- [ ] Knowledge base indexed: `python scripts/index_rag.py`
- [ ] Vector store created in `./vector_db/`

## Testing

- [ ] Server starts: `python main.py`
- [ ] Health check passes: `curl http://localhost:8000/api/health`
- [ ] Test query works: `curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d "{\"query\": \"show me all gold deposits\"}"`

## Quick Test Commands

```bash
# 1. Check Python version
python --version

# 2. Check PostgreSQL
pg_isready

# 3. Test database connection
python -c "from database.postgis_client import get_postgis_client; db = get_postgis_client(); print('OK' if db.health_check() else 'FAILED')"

# 4. Test Ollama connection
python -c "import asyncio; from llm.ollama_client import get_ollama_client; async def test(): ollama = get_ollama_client(); print('OK' if await ollama.health_check() else 'FAILED'); asyncio.run(test())"

# 5. Start server
python main.py
```

---

**Once all items are checked, you're ready to run!** ✅
