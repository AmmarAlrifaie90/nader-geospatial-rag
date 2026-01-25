"""
=============================================================================
GEOSPATIAL RAG - POSTGIS DATABASE CLIENT
=============================================================================
Handles all database operations with PostGIS
=============================================================================
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import geopandas as gpd
from shapely import wkt
from sqlalchemy import create_engine

from config import settings

logger = logging.getLogger(__name__)


class PostGISClient:
    """Client for PostGIS database operations."""
    
    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or settings.postgres_url
        self._connection = None
        
        # Parse connection details for psycopg2
        self.conn_params = {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "user": settings.postgres_user,
            "password": settings.postgres_password,
            "database": settings.postgres_database,
        }
        
        logger.info(f"PostGIS client initialized for {settings.postgres_database}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            yield conn
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Get a database cursor with automatic cleanup."""
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)
            fetch: Whether to fetch results
            
        Returns:
            List of result dictionaries
        """
        logger.debug(f"Executing query: {query[:200]}...")
        
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            return []
    
    def execute_safe_query(
        self,
        query: str,
        max_rows: Optional[int] = 1000
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute a query with safety limits.
        
        Args:
            query: SQL query string
            max_rows: Maximum rows to return (None = no limit, return all data)
            
        Returns:
            Tuple of (results, was_truncated)
        """
        query_upper = query.upper().strip()
        
        # Only add LIMIT if:
        # 1. Query doesn't already have LIMIT
        # 2. max_rows is not None (user wants a limit)
        if "LIMIT" not in query_upper and max_rows is not None:
            # Remove trailing semicolon if present
            query = query.rstrip(";").strip()
            query = f"{query} LIMIT {max_rows + 1}"
        
        results = self.execute_query(query)
        
        # Check truncation only if we have a limit
        if max_rows is not None:
            was_truncated = len(results) > max_rows
            if was_truncated:
                results = results[:max_rows]
        else:
            was_truncated = False
        
        return results, was_truncated
    
    def get_as_geodataframe(
        self,
        query: str,
        geom_col: str = "geom"
    ) -> gpd.GeoDataFrame:
        """
        Execute query and return as GeoDataFrame.
        
        Args:
            query: SQL query (must include geometry column)
            geom_col: Name of geometry column
            
        Returns:
            GeoDataFrame with results
        """
        engine = create_engine(self.connection_url)
        
        try:
            gdf = gpd.read_postgis(query, engine, geom_col=geom_col)
            return gdf
        finally:
            engine.dispose()
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table."""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute_query(query, (table_name,))
    
    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """
        results = self.execute_query(query)
        return [r["table_name"] for r in results]
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        # Sanitize table name
        query = sql.SQL("SELECT COUNT(*) as count FROM {}").format(
            sql.Identifier(table_name)
        )
        
        with self.get_cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            return result["count"]
    
    def get_table_bounds(self, table_name: str, geom_col: str = "geom") -> Dict[str, float]:
        """Get geographic bounds of a table."""
        query = sql.SQL("""
            SELECT 
                ST_XMin(ST_Extent({geom})) as min_lon,
                ST_YMin(ST_Extent({geom})) as min_lat,
                ST_XMax(ST_Extent({geom})) as max_lon,
                ST_YMax(ST_Extent({geom})) as max_lat
            FROM {table}
        """).format(
            geom=sql.Identifier(geom_col),
            table=sql.Identifier(table_name)
        )
        
        with self.get_cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            return dict(result)
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a query without executing it.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for dangerous operations
        dangerous_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
            "TRUNCATE", "CREATE", "GRANT", "REVOKE"
        ]
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False, f"Query contains forbidden keyword: {keyword}"
        
        # Try to explain the query (validates syntax)
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"EXPLAIN {query}")
            return True, None
        except psycopg2.Error as e:
            return False, str(e)
    
    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global client instance
_client: Optional[PostGISClient] = None


def get_postgis_client() -> PostGISClient:
    """Get or create the global PostGIS client."""
    global _client
    if _client is None:
        _client = PostGISClient()
    return _client


# Database schema for LLM context
DATABASE_SCHEMA = """
DATABASE: geodatabase (PostgreSQL 18.1 with PostGIS)

TABLE: mods (Mineral Occurrence Documentation System)
- gid: integer PRIMARY KEY
- mods: varchar(254) - MODS ID
- eng_name: varchar(254) - English name
- arb_name: varchar(254) - Arabic name
- major_comm: varchar(254) - Major commodities (gold, copper, etc.)
- minor_comm: varchar(254) - Minor commodities
- trace_comm: varchar(254) - Trace commodities
- longitude: double precision
- latitude: double precision
- region: varchar(254) - Regional location
- elevation: varchar(254) - Altitude in meters
- occ_type: varchar(254) - metallic/non-metallic
- exp_status: varchar(254) - Exploration status
- occ_imp: varchar(254) - Importance (very high, high, medium, low, very low)
- ancient_wo: varchar(254) - Ancient workings
- geochem_ex: varchar(254) - Geochemical exploration data
- geophys_ex: varchar(254) - Geophysical exploration data
- host_rocks: varchar(254) - Host rock types
- geologic_f: varchar(254) - Geological formation
- gitology: varchar(254) - Deposit type
- geom: geometry(Point, 4326) - Location point

TABLE: borholes (Borehole drilling data)
- gid: integer PRIMARY KEY
- project_id: varchar(254) - Project identifier
- project_na: varchar(254) - Project name
- borehole_i: varchar(254) - Borehole ID
- borehole_t: varchar(254) - Borehole type
- longitude: double precision
- latitude: double precision
- elements: varchar(254) - Chemical elements detected
- techn_data: varchar(254) - Technical data
- mineral_co: varchar(254) - Mineral composition
- pxrf: varchar(254) - pXRF analysis data
- geom: geometry(Point, 4326) - Location point

TABLE: surface_samples (Surface geological samples)
- gid: integer PRIMARY KEY
- projectid: varchar(254) - Project identifier
- projectnam: varchar(254) - Project name
- sampleid: varchar(254) - Sample ID
- sampletype: varchar(254) - Sample type (rock, soil, etc.)
- longitude: double precision
- latitude: double precision
- elements: varchar(254) - Chemical elements
- geom: geometry(Point, 4326) - Location point

SPATIAL FUNCTIONS:
- ST_Distance(geom1::geography, geom2::geography) - Distance in meters
- ST_DWithin(geom1::geography, geom2::geography, distance_meters) - Within distance
- ST_SetSRID(ST_MakePoint(lon, lat), 4326) - Create point
- ST_X(geom) - Get longitude
- ST_Y(geom) - Get latitude
"""
