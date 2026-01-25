"""
=============================================================================
GEOSPATIAL RAG - TOOL 4: SPATIAL ANALYZER
=============================================================================
Performs spatial and statistical analysis with LLM interpretation
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
import json
from collections import Counter

from llm.ollama_client import get_ollama_client
from database.postgis_client import get_postgis_client, DATABASE_SCHEMA

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT = """You are a geospatial analysis expert for a mining database.

Given a user's analysis request, determine what analysis to perform and generate the appropriate SQL queries.

{schema}

AVAILABLE ANALYSIS TYPES:

1. BUFFER ANALYSIS - Find features within distance of a point/feature
   SQL Pattern: ST_DWithin(geom::geography, reference::geography, distance_meters)

2. CLUSTERING - Group nearby features
   SQL Pattern: ST_ClusterDBSCAN(geom, eps := distance_degrees, minpoints := N) OVER()

3. DENSITY ANALYSIS - Calculate point density per area
   SQL Pattern: COUNT(*) with spatial grouping

4. DISTANCE ANALYSIS - Calculate distances between features
   SQL Pattern: ST_Distance(geom1::geography, geom2::geography)

5. STATISTICAL SUMMARY - Aggregate statistics on attributes
   SQL Pattern: COUNT, AVG, MIN, MAX, GROUP BY

6. SPATIAL DISTRIBUTION - Analyze geographic spread
   SQL Pattern: ST_Extent, ST_Centroid, standard deviation of coordinates

7. NEAREST NEIGHBOR - Find closest features
   SQL Pattern: ORDER BY geom <-> reference_geom LIMIT N

8. OVERLAP/INTERSECTION - Find features in same area
   SQL Pattern: ST_Intersects, ST_Within

Respond with JSON:
{{
    "analysis_type": "buffer|cluster|density|distance|statistics|distribution|nearest|overlap",
    "description": "What this analysis will show",
    "sql_queries": [
        {{
            "name": "query_name",
            "purpose": "what this query calculates",
            "sql": "SELECT ..."
        }}
    ],
    "interpretation_needed": true/false
}}
"""


class SpatialAnalyzer:
    """Performs spatial and statistical analysis on geodata."""
    
    def __init__(self):
        self.ollama = get_ollama_client()
        self.db = get_postgis_client()
        self.schema = DATABASE_SCHEMA
    
    async def analyze(self, query: str) -> Dict[str, Any]:
        """
        Perform analysis based on natural language request.
        
        Args:
            query: Natural language analysis request
            
        Returns:
            Analysis results with interpretation
        """
        # Generate analysis plan
        plan = await self._generate_analysis_plan(query)
        
        # Execute queries
        results = {}
        for q in plan.get("sql_queries", []):
            try:
                query_results = self.db.execute_query(q["sql"])
                results[q["name"]] = {
                    "purpose": q["purpose"],
                    "data": query_results,
                    "row_count": len(query_results)
                }
            except Exception as e:
                results[q["name"]] = {
                    "purpose": q["purpose"],
                    "error": str(e)
                }
        
        # Generate interpretation if needed
        interpretation = None
        if plan.get("interpretation_needed", True):
            interpretation = await self._interpret_results(query, plan, results)
        
        return {
            "success": True,
            "analysis_type": plan.get("analysis_type"),
            "description": plan.get("description"),
            "results": results,
            "interpretation": interpretation,
            "natural_query": query
        }
    
    async def _generate_analysis_plan(self, query: str) -> Dict[str, Any]:
        """Generate analysis SQL queries using LLM."""
        prompt = ANALYSIS_PROMPT.format(schema=self.schema)
        
        try:
            result = await self.ollama.generate_json(
                prompt=f"Analyze request: \"{query}\"",
                system=prompt,
                temperature=0.0
            )
            return result
        except Exception as e:
            logger.error(f"Analysis plan generation failed: {e}")
            raise ValueError(f"Failed to generate analysis plan: {e}")
    
    async def _interpret_results(
        self,
        query: str,
        plan: Dict[str, Any],
        results: Dict[str, Any]
    ) -> str:
        """Generate human-readable interpretation of results."""
        
        # Prepare results summary for LLM
        summary_parts = []
        for name, result in results.items():
            if "error" in result:
                summary_parts.append(f"{name}: Error - {result['error']}")
            else:
                summary_parts.append(
                    f"{name} ({result['purpose']}): {result['row_count']} results"
                )
                if result['data'] and result['row_count'] <= 10:
                    summary_parts.append(f"  Data: {json.dumps(result['data'][:5])}")
        
        results_summary = "\n".join(summary_parts)
        
        interpretation_prompt = f"""
        The user asked: "{query}"
        
        Analysis type: {plan.get('analysis_type')}
        Description: {plan.get('description')}
        
        Results:
        {results_summary}
        
        Provide a clear, concise interpretation of these results for someone 
        interested in mining/geological data. What patterns or insights can we see?
        Keep it to 2-3 paragraphs maximum.
        """
        
        try:
            interpretation = await self.ollama.generate(
                prompt=interpretation_prompt,
                system="You are a mining data analyst. Interpret spatial analysis results clearly and concisely.",
                temperature=0.3
            )
            return interpretation
        except:
            return "Analysis completed. Please review the results above."
    
    async def buffer_analysis(
        self,
        table: str,
        lon: float,
        lat: float,
        radius_km: float
    ) -> Dict[str, Any]:
        """Find all features within radius of a point."""
        radius_m = radius_km * 1000
        
        sql = f"""
            SELECT *, 
                ROUND(ST_Distance(
                    geom::geography, 
                    ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography
                )::numeric / 1000, 2) AS distance_km
            FROM {table}
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography,
                {radius_m}
            )
            ORDER BY distance_km
            LIMIT 500
        """
        
        is_valid, error = self.db.validate_query(sql)
        if not is_valid:
            return {"success": False, "error": error}
        
        results = self.db.execute_query(sql)
        
        return {
            "success": True,
            "analysis_type": "buffer",
            "center": {"lon": lon, "lat": lat},
            "radius_km": radius_km,
            "feature_count": len(results),
            "data": results
        }
    
    async def cluster_analysis(
        self,
        table: str,
        cluster_distance_km: float = 10,
        min_points: int = 2
    ) -> Dict[str, Any]:
        """Perform DBSCAN clustering on points."""
        
        eps_degrees = cluster_distance_km / 111
        
        sql = f"""
            SELECT 
                ST_ClusterDBSCAN(geom, eps := {eps_degrees}, minpoints := {min_points}) OVER() AS cluster_id,
                gid,
                eng_name,
                major_comm,
                ST_Y(geom) AS latitude,
                ST_X(geom) AS longitude
            FROM {table}
            WHERE geom IS NOT NULL
            ORDER BY cluster_id NULLS LAST
            LIMIT 1000
        """
        
        results = self.db.execute_query(sql)
        
        cluster_counts = Counter(r.get("cluster_id") for r in results if r.get("cluster_id") is not None)
        
        return {
            "success": True,
            "analysis_type": "cluster",
            "parameters": {
                "distance_km": cluster_distance_km,
                "min_points": min_points
            },
            "cluster_count": len(cluster_counts),
            "cluster_sizes": dict(cluster_counts),
            "noise_points": sum(1 for r in results if r.get("cluster_id") is None),
            "data": results
        }
    
    async def commodity_statistics(self, table: str = "mods") -> Dict[str, Any]:
        """Get statistics about commodities."""
        
        sql = f"""
            SELECT 
                major_comm,
                COUNT(*) as occurrence_count,
                COUNT(DISTINCT region) as region_count
            FROM {table}
            WHERE major_comm IS NOT NULL AND major_comm != ''
            GROUP BY major_comm
            ORDER BY occurrence_count DESC
            LIMIT 50
        """
        
        results = self.db.execute_query(sql)
        
        return {
            "success": True,
            "analysis_type": "statistics",
            "total_commodities": len(results),
            "data": results
        }
    
    async def region_distribution(self, table: str = "mods") -> Dict[str, Any]:
        """Analyze distribution by region."""
        
        sql = f"""
            SELECT 
                region,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage,
                ST_Y(ST_Centroid(ST_Collect(geom))) as center_lat,
                ST_X(ST_Centroid(ST_Collect(geom))) as center_lon
            FROM {table}
            WHERE region IS NOT NULL AND region != ''
            GROUP BY region
            ORDER BY count DESC
        """
        
        results = self.db.execute_query(sql)
        
        return {
            "success": True,
            "analysis_type": "distribution",
            "total_regions": len(results),
            "data": results
        }


# Global instance
_analyzer: Optional[SpatialAnalyzer] = None


def get_analyzer() -> SpatialAnalyzer:
    """Get or create the global spatial analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SpatialAnalyzer()
    return _analyzer
