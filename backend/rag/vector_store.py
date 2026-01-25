"""
=============================================================================
GEOSPATIAL RAG - VECTOR STORE
=============================================================================
Stores and retrieves vector embeddings using ChromaDB
=============================================================================
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logging.warning("ChromaDB not installed. Install with: pip install chromadb")

from config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector database for storing and retrieving embeddings."""
    
    def __init__(self, persist_directory: Optional[str] = None):
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "ChromaDB is required. Install with: pip install chromadb"
            )
        
        self.persist_directory = persist_directory or "./vector_db"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Collection for database schema and documentation
        self.schema_collection = self.client.get_or_create_collection(
            name="database_schema",
            metadata={"description": "Database schema and table documentation"}
        )
        
        # Collection for data samples and examples
        self.data_collection = self.client.get_or_create_collection(
            name="data_samples",
            metadata={"description": "Sample data records and examples"}
        )
        
        # Collection for query patterns
        self.query_collection = self.client.get_or_create_collection(
            name="query_patterns",
            metadata={"description": "Common query patterns and examples"}
        )
        
        logger.info(f"Vector store initialized at {self.persist_directory}")
    
    def add_schema_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None
    ):
        """Add database schema documents to the vector store."""
        if ids is None:
            ids = [f"schema_{i}" for i in range(len(documents))]
        
        if embeddings:
            self.schema_collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
        else:
            self.schema_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        logger.info(f"Added {len(documents)} schema documents to vector store")
    
    def add_data_samples(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ):
        """Add data sample documents with embeddings."""
        if ids is None:
            ids = [f"sample_{i}" for i in range(len(documents))]
        
        self.data_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} data samples to vector store")
    
    def add_query_patterns(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ):
        """Add query pattern examples with embeddings."""
        if ids is None:
            ids = [f"pattern_{i}" for i in range(len(documents))]
        
        self.query_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} query patterns to vector store")
    
    async def retrieve_relevant_context(
        self,
        query: str,
        query_embedding: List[float],
        collection_name: str = "database_schema",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context chunks based on semantic similarity.
        
        Args:
            query: Original query text
            query_embedding: Embedding vector of the query
            collection_name: Which collection to search
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        collection = self.client.get_collection(collection_name)
        
        # Search by embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        retrieved = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                retrieved.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "relevance_score": 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)
                })
        
        logger.info(f"Retrieved {len(retrieved)} relevant chunks for query: {query[:50]}...")
        return retrieved
    
    async def hybrid_retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve from multiple collections (hybrid retrieval).
        
        Returns:
            Dictionary with results from each collection
        """
        results = {}
        
        for collection_name in ["database_schema", "query_patterns", "data_samples"]:
            try:
                results[collection_name] = await self.retrieve_relevant_context(
                    query=query,
                    query_embedding=query_embedding,
                    collection_name=collection_name,
                    top_k=top_k
                )
            except Exception as e:
                logger.warning(f"Failed to retrieve from {collection_name}: {e}")
                results[collection_name] = []
        
        return results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about stored vectors."""
        stats = {}
        
        for name in ["database_schema", "query_patterns", "data_samples"]:
            try:
                collection = self.client.get_collection(name)
                count = collection.count()
                stats[name] = {
                    "document_count": count,
                    "collection_name": name
                }
            except Exception as e:
                stats[name] = {"error": str(e)}
        
        return stats
    
    def reset(self):
        """Reset all collections (for re-indexing)."""
        self.client.delete_collection("database_schema")
        self.client.delete_collection("query_patterns")
        self.client.delete_collection("data_samples")
        
        # Recreate collections
        self.schema_collection = self.client.get_or_create_collection(
            name="database_schema"
        )
        self.data_collection = self.client.get_or_create_collection(
            name="data_samples"
        )
        self.query_collection = self.client.get_or_create_collection(
            name="query_patterns"
        )
        
        logger.info("Vector store reset complete")


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
