"""
=============================================================================
GEOSPATIAL RAG - EMBEDDING SERVICE
=============================================================================
Generates vector embeddings using Ollama embedding models
=============================================================================
"""

import logging
import httpx
from typing import List, Optional
from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Ollama."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        # Use embedding model (Ollama supports embedding generation with text models)
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        
        logger.info(f"Embedding service initialized: {self.base_url} using {self.model}")
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        return (await self.embed_batch([text]))[0]
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        url = f"{self.base_url}/api/embeddings"
        
        embeddings = []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for text in texts:
                    payload = {
                        "model": self.model,
                        "prompt": text
                    }
                    
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    embedding = result.get("embedding", [])
                    
                    if not embedding:
                        logger.warning(f"No embedding returned for text: {text[:50]}...")
                        # Fallback: return zero vector (shouldn't happen with proper model)
                        embedding = [0.0] * 768  # Common embedding dimension
                    
                    embeddings.append(embedding)
                    
        except httpx.TimeoutException:
            logger.error(f"Embedding request timed out after {self.timeout}s")
            raise TimeoutError(f"Embedding request timed out")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding HTTP error: {e.response.status_code}")
            raise ConnectionError(f"Embedding server error: {e.response.status_code}")
            
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise ConnectionError(
                f"Cannot connect to embedding server at {self.base_url}. "
                "Make sure Ollama is running and supports embeddings."
            )
        
        return embeddings
    
    async def health_check(self) -> bool:
        """Check if embedding service is available."""
        try:
            # Try to embed a test string
            await self.embed("test")
            return True
        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return False


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
