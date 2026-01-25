"""
=============================================================================
GEOSPATIAL RAG - INDEXING SCRIPT
=============================================================================
Run this script to index the knowledge base into the vector store
=============================================================================
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.indexer import get_indexer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Index the knowledge base."""
    logger.info("Starting RAG knowledge base indexing...")
    
    try:
        indexer = get_indexer()
        await indexer.index_all()
        
        logger.info("✓ Indexing complete!")
        logger.info("You can now use the RAG system via /api/rag/query")
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
