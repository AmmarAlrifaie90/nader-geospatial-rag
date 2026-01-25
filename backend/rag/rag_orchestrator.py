"""
=============================================================================
GEOSPATIAL RAG - RAG ORCHESTRATOR
=============================================================================
Implements Agentic RAG: Retrieves context, augments prompts, generates responses
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
from llm.ollama_client import get_ollama_client
from rag.embedding_service import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


RAG_SYSTEM_PROMPT = """You are an expert geospatial mining database assistant with access to retrieved context.

You will receive:
1. User's natural language query
2. Retrieved relevant context from the knowledge base
3. Database schema information

Your job is to:
1. Understand the user's intent using the retrieved context
2. Generate appropriate SQL queries or provide answers based on context
3. If context is insufficient, indicate what additional information is needed

Use the retrieved context to:
- Understand domain-specific terminology
- Learn from similar past queries
- Get examples of correct SQL patterns
- Understand data relationships

Always prioritize accuracy over creativity. If you're uncertain, ask for clarification."""


class RAGOrchestrator:
    """
    Agentic RAG Orchestrator that:
    1. Retrieves relevant context using semantic search
    2. Augments LLM prompts with retrieved context
    3. Generates responses using augmented context
    4. Can iteratively refine queries (agentic behavior)
    """
    
    def __init__(self):
        self.ollama = get_ollama_client()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
    
    async def process_query(
        self,
        query: str,
        max_context_chunks: int = 5,
        use_hybrid: bool = True
    ) -> Dict[str, Any]:
        """
        Process a query using RAG pipeline.
        
        Args:
            query: User's natural language query
            max_context_chunks: Maximum number of context chunks to retrieve
            use_hybrid: Whether to retrieve from multiple collections
            
        Returns:
            Dictionary with query, retrieved context, and generated response
        """
        # Step 1: Generate query embedding
        logger.info(f"Generating embedding for query: {query[:50]}...")
        query_embedding = await self.embedding_service.embed(query)
        
        # Step 2: Retrieve relevant context
        logger.info("Retrieving relevant context from vector store...")
        if use_hybrid:
            retrieved = await self.vector_store.hybrid_retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=max_context_chunks
            )
        else:
            retrieved = {
                "database_schema": await self.vector_store.retrieve_relevant_context(
                    query=query,
                    query_embedding=query_embedding,
                    collection_name="database_schema",
                    top_k=max_context_chunks
                )
            }
        
        # Step 3: Format context for prompt augmentation
        context_text = self._format_context(retrieved)
        
        # Step 4: Augment prompt with retrieved context
        augmented_prompt = self._augment_prompt(query, context_text)
        
        # Step 5: Generate response using augmented context
        logger.info("Generating response with augmented context...")
        response = await self.ollama.generate(
            prompt=augmented_prompt,
            system=RAG_SYSTEM_PROMPT,
            temperature=0.1
        )
        
        return {
            "query": query,
            "retrieved_context": retrieved,
            "context_summary": self._summarize_context(retrieved),
            "augmented_prompt": augmented_prompt[:500] + "..." if len(augmented_prompt) > 500 else augmented_prompt,
            "response": response,
            "context_chunks_used": sum(len(chunks) for chunks in retrieved.values())
        }
    
    def _format_context(self, retrieved: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format retrieved context into readable text."""
        sections = []
        
        if retrieved.get("database_schema"):
            sections.append("=== DATABASE SCHEMA CONTEXT ===")
            for chunk in retrieved["database_schema"]:
                sections.append(f"- {chunk['text']}")
                if chunk.get("metadata"):
                    sections.append(f"  Metadata: {chunk['metadata']}")
        
        if retrieved.get("query_patterns"):
            sections.append("\n=== RELEVANT QUERY PATTERNS ===")
            for chunk in retrieved["query_patterns"]:
                sections.append(f"- {chunk['text']}")
        
        if retrieved.get("data_samples"):
            sections.append("\n=== RELEVANT DATA EXAMPLES ===")
            for chunk in retrieved["data_samples"][:3]:  # Limit examples
                sections.append(f"- {chunk['text']}")
        
        return "\n".join(sections)
    
    def _augment_prompt(self, query: str, context: str) -> str:
        """Augment user query with retrieved context."""
        return f"""User Query: {query}

Retrieved Context from Knowledge Base:
{context}

Based on the retrieved context above, please:
1. Understand the user's intent
2. Use the context to inform your response
3. Generate appropriate SQL or provide an answer

User Query: {query}"""
    
    def _summarize_context(self, retrieved: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Summarize retrieved context statistics."""
        return {
            "schema_chunks": len(retrieved.get("database_schema", [])),
            "pattern_chunks": len(retrieved.get("query_patterns", [])),
            "sample_chunks": len(retrieved.get("data_samples", [])),
            "total_chunks": sum(len(chunks) for chunks in retrieved.values())
        }
    
    async def agentic_process(
        self,
        query: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Agentic RAG with iterative refinement.
        
        The agent can:
        1. Retrieve context
        2. Generate response
        3. If response is uncertain, refine query and retrieve more context
        4. Iterate until confident answer
        """
        iterations = []
        current_query = query
        
        for i in range(max_iterations):
            logger.info(f"Agentic iteration {i+1}/{max_iterations}")
            
            # Process query
            result = await self.process_query(current_query)
            iterations.append({
                "iteration": i + 1,
                "query": current_query,
                "response": result["response"],
                "context_used": result["context_chunks_used"]
            })
            
            # Check if we need to refine (simple heuristic)
            # In a real system, you'd use the LLM to decide
            if "uncertain" in result["response"].lower() or "not sure" in result["response"].lower():
                # Refine query based on response
                refinement_prompt = f"""
                Original query: {query}
                Current response: {result['response']}
                
                The response indicates uncertainty. Suggest a refined query that would help get a better answer.
                Respond with ONLY the refined query, nothing else.
                """
                
                refined = await self.ollama.generate(
                    prompt=refinement_prompt,
                    temperature=0.3
                )
                current_query = refined.strip()
                logger.info(f"Refining query to: {current_query}")
            else:
                # Confident answer, stop iterating
                break
        
        return {
            "original_query": query,
            "final_query": current_query,
            "iterations": iterations,
            "final_response": iterations[-1]["response"] if iterations else None
        }


# Global instance
_rag_orchestrator: Optional[RAGOrchestrator] = None


def get_rag_orchestrator() -> RAGOrchestrator:
    """Get or create the global RAG orchestrator."""
    global _rag_orchestrator
    if _rag_orchestrator is None:
        _rag_orchestrator = RAGOrchestrator()
    return _rag_orchestrator
