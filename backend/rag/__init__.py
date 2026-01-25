"""
=============================================================================
GEOSPATIAL RAG - RETRIEVAL AUGMENTED GENERATION MODULE
=============================================================================
Implements true RAG with vector embeddings and semantic retrieval
=============================================================================
"""

from .embedding_service import get_embedding_service
from .vector_store import get_vector_store
from .rag_orchestrator import get_rag_orchestrator

__all__ = [
    "get_embedding_service",
    "get_vector_store", 
    "get_rag_orchestrator"
]
