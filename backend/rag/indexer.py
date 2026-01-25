"""
=============================================================================
GEOSPATIAL RAG - INDEXER
=============================================================================
Indexes database schema, data samples, and query patterns into vector store
=============================================================================
"""

import logging
from typing import List, Dict, Any
from database.postgis_client import get_postgis_client, DATABASE_SCHEMA
from rag.embedding_service import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class RAGIndexer:
    """Indexes knowledge base into vector store for RAG retrieval."""
    
    def __init__(self):
        self.db = get_postgis_client()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
    
    async def index_database_schema(self):
        """Index database schema documentation."""
        logger.info("Indexing database schema...")
        
        # Split schema into chunks
        schema_chunks = self._chunk_schema(DATABASE_SCHEMA)
        
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(schema_chunks):
            documents.append(chunk["text"])
            metadatas.append({
                "type": "schema",
                "chunk_id": i,
                "table": chunk.get("table", "general")
            })
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} schema chunks...")
        embeddings = await self.embedding_service.embed_batch(documents)
        
        # Add to vector store
        self.vector_store.add_schema_documents(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        logger.info("Database schema indexed successfully")
    
    async def index_query_patterns(self):
        """Index common query patterns and examples."""
        logger.info("Indexing query patterns...")
        
        patterns = [
            {
                "text": "Find all gold deposits in the database. Use the mods table and filter by major_comm containing 'gold'.",
                "metadata": {"type": "pattern", "intent": "filter_by_commodity", "table": "mods"}
            },
            {
                "text": "Show all boreholes. Use the borholes table (note: spelled 'borholes' not 'boreholes').",
                "metadata": {"type": "pattern", "intent": "list_all", "table": "borholes"}
            },
            {
                "text": "Find mineral deposits in a specific region. Use mods table with region column filter.",
                "metadata": {"type": "pattern", "intent": "filter_by_region", "table": "mods"}
            },
            {
                "text": "Show gold deposits near faults. Join mods with geology_faults_contacts_master using ST_DWithin for proximity.",
                "metadata": {"type": "pattern", "intent": "spatial_join", "tables": ["mods", "geology_faults_contacts_master"]}
            },
            {
                "text": "Find deposits within volcanic areas. Join mods with geology_master using ST_Intersects.",
                "metadata": {"type": "pattern", "intent": "spatial_intersection", "tables": ["mods", "geology_master"]}
            },
            {
                "text": "Get surface samples with specific elements. Use surface_samples table and filter by elements column.",
                "metadata": {"type": "pattern", "intent": "filter_by_element", "table": "surface_samples"}
            },
            {
                "text": "For point geometries, always output latitude and longitude using ST_Y and ST_X with proper SRID transformation.",
                "metadata": {"type": "pattern", "intent": "geometry_output", "geometry_type": "point"}
            },
            {
                "text": "For polygon geometries, output GeoJSON using ST_AsGeoJSON with proper SRID transformation.",
                "metadata": {"type": "pattern", "intent": "geometry_output", "geometry_type": "polygon"}
            }
        ]
        
        documents = [p["text"] for p in patterns]
        metadatas = [p["metadata"] for p in patterns]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} query patterns...")
        embeddings = await self.embedding_service.embed_batch(documents)
        
        # Add to vector store
        self.vector_store.add_query_patterns(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        logger.info("Query patterns indexed successfully")
    
    async def index_data_samples(self, sample_size: int = 50):
        """Index sample data records for context."""
        logger.info(f"Indexing {sample_size} data samples...")
        
        samples = []
        
        # Sample from mods table
        mods_query = f"SELECT eng_name, arb_name, major_comm, minor_comm, region, occ_imp FROM mods WHERE major_comm IS NOT NULL LIMIT {sample_size // 3}"
        mods_results = self.db.execute_query(mods_query)
        
        for record in mods_results:
            text = f"Mineral deposit: {record.get('eng_name', 'Unknown')} ({record.get('arb_name', '')}). "
            text += f"Major commodity: {record.get('major_comm', 'N/A')}. "
            text += f"Region: {record.get('region', 'N/A')}. "
            text += f"Importance: {record.get('occ_imp', 'N/A')}."
            
            samples.append({
                "text": text,
                "metadata": {
                    "type": "data_sample",
                    "table": "mods",
                    "commodity": record.get("major_comm", ""),
                    "region": record.get("region", "")
                }
            })
        
        # Sample from borholes
        borholes_query = f"SELECT project_na, borehole_i, elements FROM borholes WHERE elements IS NOT NULL LIMIT {sample_size // 3}"
        borholes_results = self.db.execute_query(borholes_query)
        
        for record in borholes_results:
            text = f"Borehole: {record.get('borehole_i', 'Unknown')} in project {record.get('project_na', 'Unknown')}. "
            text += f"Elements detected: {record.get('elements', 'N/A')}."
            
            samples.append({
                "text": text,
                "metadata": {
                    "type": "data_sample",
                    "table": "borholes",
                    "project": record.get("project_na", "")
                }
            })
        
        # Sample from surface_samples
        samples_query = f"SELECT sampleid, sampletype, elements FROM surface_samples WHERE elements IS NOT NULL LIMIT {sample_size // 3}"
        samples_results = self.db.execute_query(samples_query)
        
        for record in samples_results:
            text = f"Surface sample: {record.get('sampleid', 'Unknown')} of type {record.get('sampletype', 'Unknown')}. "
            text += f"Elements: {record.get('elements', 'N/A')}."
            
            samples.append({
                "text": text,
                "metadata": {
                    "type": "data_sample",
                    "table": "surface_samples",
                    "sample_type": record.get("sampletype", "")
                }
            })
        
        if not samples:
            logger.warning("No data samples found to index")
            return
        
        documents = [s["text"] for s in samples]
        metadatas = [s["metadata"] for s in samples]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} data samples...")
        embeddings = await self.embedding_service.embed_batch(documents)
        
        # Add to vector store
        self.vector_store.add_data_samples(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        logger.info(f"Indexed {len(samples)} data samples successfully")
    
    def _chunk_schema(self, schema_text: str) -> List[Dict[str, Any]]:
        """Split schema text into semantic chunks."""
        chunks = []
        current_table = None
        current_text = []
        
        lines = schema_text.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("TABLE:"):
                # Save previous chunk
                if current_text and current_table:
                    chunks.append({
                        "table": current_table,
                        "text": "\n".join(current_text)
                    })
                
                # Start new chunk
                current_table = line.replace("TABLE:", "").strip().split()[0]
                current_text = [line]
            elif line and not line.startswith("#") and not line.startswith("-"):
                current_text.append(line)
        
        # Save last chunk
        if current_text and current_table:
            chunks.append({
                "table": current_table,
                "text": "\n".join(current_text)
            })
        
        # Also add full schema as a general chunk
        chunks.append({
            "table": "general",
            "text": schema_text
        })
        
        return chunks
    
    async def index_all(self):
        """Index all knowledge base components."""
        logger.info("Starting full knowledge base indexing...")
        
        try:
            await self.index_database_schema()
            await self.index_query_patterns()
            await self.index_data_samples()
            
            logger.info("Knowledge base indexing complete!")
            
            # Print statistics
            stats = self.vector_store.get_collection_stats()
            logger.info(f"Vector store statistics: {stats}")
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise


# Global instance
_indexer: RAGIndexer = None


def get_indexer() -> RAGIndexer:
    """Get or create the global indexer."""
    global _indexer
    if _indexer is None:
        _indexer = RAGIndexer()
    return _indexer
