"""
=============================================================================
GEOSPATIAL RAG - SCHEMA LEARNER
=============================================================================
Dynamically learns database schema and builds synonym mappings
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
from database.postgis_client import get_postgis_client

logger = logging.getLogger(__name__)


class SchemaLearner:
    """Learns database schema dynamically and builds synonym mappings."""
    
    def __init__(self):
        self.db = get_postgis_client()
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._synonym_map: Optional[Dict[str, str]] = None
    
    def learn_schema(self) -> Dict[str, Any]:
        """
        Learn complete database schema from actual database.
        
        Returns:
            Dictionary with tables, columns, types, and relationships
        """
        if self._schema_cache:
            return self._schema_cache
        
        logger.info("Learning database schema from PostGIS...")
        
        schema = {
            "tables": {},
            "geometry_columns": {},
            "relationships": []
        }
        
        # Get all tables
        tables = self.db.get_all_tables()
        
        for table in tables:
            # Get column information
            columns = self.db.get_table_schema(table)
            
            # Get geometry column info
            geom_info = self._get_geometry_info(table)
            
            table_info = {
                "name": table,
                "columns": {},
                "geometry_type": None,
                "geometry_column": None,
                "row_count": self.db.get_table_count(table)
            }
            
            for col in columns:
                col_name = col["column_name"]
                col_type = col["data_type"]
                
                table_info["columns"][col_name] = {
                    "type": col_type,
                    "nullable": col["is_nullable"] == "YES",
                    "default": col.get("column_default")
                }
                
                # Check if it's a geometry column
                if col_type == "USER-DEFINED" or "geometry" in col_type.lower():
                    if geom_info:
                        table_info["geometry_type"] = geom_info.get("type")
                        table_info["geometry_column"] = col_name
            
            schema["tables"][table] = table_info
            
            # Store geometry info
            if table_info["geometry_column"]:
                schema["geometry_columns"][table] = {
                    "column": table_info["geometry_column"],
                    "type": table_info["geometry_type"],
                    "srid": geom_info.get("srid", 4326) if geom_info else 4326
                }
        
        self._schema_cache = schema
        logger.info(f"Learned schema for {len(tables)} tables")
        
        return schema
    
    def _get_geometry_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get geometry column information from PostGIS."""
        try:
            query = """
                SELECT 
                    f_geometry_column AS column_name,
                    type AS geometry_type,
                    coord_dimension,
                    srid
                FROM geometry_columns
                WHERE f_table_name = %s
                LIMIT 1
            """
            results = self.db.execute_query(query, (table_name,))
            if results:
                return {
                    "column": results[0]["column_name"],
                    "type": results[0]["geometry_type"],
                    "srid": results[0]["srid"]
                }
        except Exception as e:
            logger.warning(f"Could not get geometry info for {table_name}: {e}")
        
        return None
    
    def build_synonym_map(self) -> Dict[str, str]:
        """
        Build synonym/alias mapping for columns.
        
        Maps common terms to actual column names.
        """
        if self._synonym_map:
            return self._synonym_map
        
        schema = self.learn_schema()
        synonym_map = {}
        
        # Common synonyms
        synonyms = {
            # Area/Terrane synonyms
            "area": "terrane",
            "areas": "terrane",
            "terrain": "terrane",  # Misspelling handling
            "terrains": "terrane",
            "region": "region",
            "regions": "region",
            "zone": "terrane",
            "zones": "terrane",
            
            # Geology synonyms
            "formation": "unit_name",
            "formations": "unit_name",
            "rock type": "main_litho",
            "lithology": "main_litho",
            "lithology family": "litho_fmly",
            "rock family": "litho_fmly",
            "volcanic": "litho_fmly",  # For filtering
            "volcanos": "litho_fmly",  # Misspelling
            "volcano": "litho_fmly",
            "volcanoes": "litho_fmly",
            
            # Commodity synonyms
            "mineral": "major_comm",
            "minerals": "major_comm",
            "commodity": "major_comm",
            "commodities": "major_comm",
            "ore": "major_comm",
            
            # Name synonyms
            "name": "eng_name",
            "english name": "eng_name",
            "arabic name": "arb_name",
            
            # Project synonyms
            "project": "project_na",
            "project name": "project_na",
            
            # Sample synonyms
            "sample": "sampleid",
            "sample id": "sampleid",
            "sample type": "sampletype",
        }
        
        # Build table-specific synonyms
        for table_name, table_info in schema["tables"].items():
            for col_name in table_info["columns"].keys():
                # Add exact match
                synonym_map[col_name.lower()] = col_name
                
                # Add variations
                if "_" in col_name:
                    parts = col_name.split("_")
                    synonym_map[" ".join(parts).lower()] = col_name
                    synonym_map[parts[-1].lower()] = col_name  # Last part
        
        # Add common synonyms
        synonym_map.update(synonyms)
        
        # Learn from actual data (sample values to understand context)
        self._learn_from_data(synonym_map, schema)
        
        self._synonym_map = synonym_map
        logger.info(f"Built synonym map with {len(synonym_map)} mappings")
        
        return synonym_map
    
    def _learn_from_data(self, synonym_map: Dict[str, str], schema: Dict[str, Any]):
        """Learn synonyms from actual data values."""
        # Sample data to understand column usage
        for table_name, table_info in schema["tables"].items():
            try:
                # Get sample rows
                sample_query = f"SELECT * FROM {table_name} LIMIT 5"
                samples = self.db.execute_query(sample_query)
                
                # Analyze column values for context
                for sample in samples:
                    for col_name, value in sample.items():
                        if value and isinstance(value, str):
                            # If value contains common terms, add to synonyms
                            value_lower = value.lower()
                            if "area" in value_lower and col_name not in synonym_map:
                                synonym_map["area"] = col_name
                            if "terrane" in value_lower:
                                synonym_map["terrane"] = col_name
                                synonym_map["area"] = col_name  # Map area to terrane
            except Exception as e:
                logger.debug(f"Could not sample {table_name}: {e}")
    
    def get_column_for_term(self, term: str, table_name: Optional[str] = None) -> Optional[str]:
        """
        Get actual column name for a user term.
        
        Args:
            term: User's term (e.g., "area", "terrane")
            table_name: Optional table to search in
            
        Returns:
            Actual column name or None
        """
        synonym_map = self.build_synonym_map()
        term_lower = term.lower().strip()
        
        # Direct match
        if term_lower in synonym_map:
            return synonym_map[term_lower]
        
        # Partial match
        for synonym, column in synonym_map.items():
            if term_lower in synonym or synonym in term_lower:
                return column
        
        # If table specified, check that table's columns
        if table_name:
            schema = self.learn_schema()
            if table_name in schema["tables"]:
                columns = schema["tables"][table_name]["columns"]
                for col_name in columns.keys():
                    if term_lower in col_name.lower() or col_name.lower() in term_lower:
                        return col_name
        
        return None
    
    def get_schema_description(self) -> str:
        """Get human-readable schema description for LLM prompts."""
        schema = self.learn_schema()
        synonym_map = self.build_synonym_map()
        
        description = "DATABASE SCHEMA (Learned from actual database):\n\n"
        
        for table_name, table_info in schema["tables"].items():
            description += f"TABLE: {table_name}\n"
            description += f"- Type: {table_info.get('geometry_type', 'NON-SPATIAL')}\n"
            description += f"- Row count: {table_info.get('row_count', 0)}\n"
            description += "- Columns:\n"
            
            for col_name, col_info in table_info["columns"].items():
                col_type = col_info["type"]
                description += f"  - {col_name}: {col_type}\n"
            
            # Add synonyms for this table
            table_synonyms = {
                k: v for k, v in synonym_map.items()
                if any(v == col for col in table_info["columns"].keys())
            }
            if table_synonyms:
                description += "- Synonyms: "
                description += ", ".join([f"{k}→{v}" for k, v in list(table_synonyms.items())[:5]])
                description += "\n"
            
            description += "\n"
        
        return description
    
    def clear_cache(self):
        """Clear schema cache to force re-learning."""
        self._schema_cache = None
        self._synonym_map = None
        logger.info("Schema cache cleared")


# Global instance
_schema_learner: Optional[SchemaLearner] = None


def get_schema_learner() -> SchemaLearner:
    """Get or create the global schema learner."""
    global _schema_learner
    if _schema_learner is None:
        _schema_learner = SchemaLearner()
    return _schema_learner
