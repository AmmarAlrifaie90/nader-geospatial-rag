# 🧠 RAG System Setup Guide

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is now implemented in your system! This is a **true RAG system** that:

1. **Retrieves** relevant context from a vector database using semantic search
2. **Augments** LLM prompts with the retrieved context
3. **Generates** responses using the augmented context

## Architecture

```
User Query
    ↓
Generate Embedding
    ↓
Semantic Search in Vector Store
    ↓
Retrieve Relevant Context (Schema, Patterns, Examples)
    ↓
Augment LLM Prompt with Context
    ↓
Generate Response
```

## Setup Steps

### 1. Install Dependencies

```bash
pip install chromadb
```

Or update requirements:
```bash
pip install -r requirements.txt
```

### 2. Index the Knowledge Base

Before using RAG, you need to index your knowledge base:

**Option A: Using API**
```bash
curl -X POST http://localhost:8000/api/rag/index
```

**Option B: Using Script**
```bash
cd backend
python scripts/index_rag.py
```

This will index:
- Database schema documentation
- Query patterns and examples
- Sample data records

### 3. Check Indexing Status

```bash
curl http://localhost:8000/api/rag/stats
```

You should see document counts for each collection.

## Usage

### Basic RAG Query

```python
import requests

response = requests.post("http://localhost:8000/api/rag/query", json={
    "query": "Find all gold deposits",
    "use_agentic": False,
    "max_context_chunks": 5
})

print(response.json()["response"])
```

### Agentic RAG (Iterative Refinement)

```python
response = requests.post("http://localhost:8000/api/rag/query", json={
    "query": "Show me mining sites",
    "use_agentic": True  # Enables iterative refinement
})
```

The agentic mode will:
1. Retrieve context
2. Generate response
3. If uncertain, refine query and retrieve more context
4. Iterate until confident answer

## API Endpoints

### POST `/api/rag/query`
Process a query using RAG.

**Request:**
```json
{
    "query": "Find gold deposits in volcanic areas",
    "use_agentic": false,
    "max_context_chunks": 5
}
```

**Response:**
```json
{
    "success": true,
    "query": "Find gold deposits in volcanic areas",
    "response": "Based on the retrieved context...",
    "context_used": 5,
    "context_summary": {
        "schema_chunks": 2,
        "pattern_chunks": 2,
        "sample_chunks": 1
    }
}
```

### POST `/api/rag/index`
Index the knowledge base (run once, or when schema changes).

### GET `/api/rag/stats`
Get statistics about indexed documents.

### POST `/api/rag/reset`
Reset vector store (for re-indexing).

## How It Works

### 1. Embedding Generation
- Uses Ollama to generate embeddings for queries and documents
- Embeddings capture semantic meaning

### 2. Vector Store (ChromaDB)
- Stores embeddings in persistent vector database
- Three collections:
  - `database_schema`: Schema documentation
  - `query_patterns`: Common query examples
  - `data_samples`: Sample data records

### 3. Semantic Retrieval
- Converts user query to embedding
- Searches vector store for similar embeddings
- Returns top-k most relevant chunks

### 4. Context Augmentation
- Formats retrieved chunks into context text
- Adds context to LLM prompt
- LLM generates response using context

## Integration with Existing System

The RAG system works alongside your existing Text-to-SQL system:

- **Text-to-SQL**: Direct SQL generation (faster, structured)
- **RAG**: Context-aware responses (more flexible, learns from examples)

You can use both:
- Use RAG for general questions and learning
- Use Text-to-SQL for precise data queries

## Troubleshooting

### "ChromaDB not installed"
```bash
pip install chromadb
```

### "No embeddings returned"
- Check Ollama is running
- Verify model supports embeddings
- Check network connection to Ollama

### "Vector store empty"
- Run indexing: `POST /api/rag/index`
- Check logs for indexing errors

### "Slow responses"
- Reduce `max_context_chunks` (default: 5)
- Check Ollama GPU acceleration
- Consider caching frequent queries

## Next Steps

1. **Index your knowledge base**: `POST /api/rag/index`
2. **Test RAG queries**: `POST /api/rag/query`
3. **Compare with Text-to-SQL**: See which works better for your use case
4. **Add custom patterns**: Edit `rag/indexer.py` to add domain-specific examples

## Difference from Text-to-SQL

| Feature | Text-to-SQL | RAG |
|---------|-------------|-----|
| **Retrieval** | Hardcoded schema | Semantic search |
| **Context** | Static prompts | Dynamic retrieval |
| **Learning** | No | Learns from examples |
| **Flexibility** | Structured queries | Natural language answers |
| **Speed** | Fast | Slightly slower |

Both systems complement each other! 🚀
