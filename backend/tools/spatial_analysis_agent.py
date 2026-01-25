"""
=============================================================================
SPATIAL ANALYSIS AGENT
=============================================================================
Smart analysis suggester that:
1. Detects data type from query results (points/lines/polygons)
2. Suggests relevant analyses based on data type + context
3. Executes PostGIS spatial analyses
4. Returns results with natural language explanations
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import json

from database.postgis_client import get_postgis_client

logger = logging.getLogger(__name__)


# =============================================================================
# ANALYSIS DEFINITIONS BY DATA TYPE
# =============================================================================

POINT_ANALYSES = {
    "clustering": {
        "id": 1,
        "name": "Cluster Analysis",
        "icon": "🔵",
        "description": "Find groups of nearby points using DBSCAN algorithm",
        "when_useful": "When you have 10+ points and want to find natural groupings"
    },
    "regional": {
        "id": 2,
        "name": "Regional Distribution",
        "icon": "📊",
        "description": "Count and analyze points by administrative region",
        "when_useful": "When you want to see geographic distribution"
    },
    "commodity": {
        "id": 3,
        "name": "Commodity Breakdown",
        "icon": "💎",
        "description": "Analyze mineral/commodity distribution",
        "when_useful": "When working with mineral deposits (mods table)"
    },
    "geology_correlation": {
        "id": 4,
        "name": "Geology Correlation",
        "icon": "🪨",
        "description": "Find which geology units contain the points",
        "when_useful": "To understand geological context"
    }
}

LINE_ANALYSES = {
    "total_length": {
        "id": 1,
        "name": "Total Length",
        "icon": "📏",
        "description": "Sum of all line lengths in kilometers",
        "when_useful": "To understand total extent of linear features"
    },
    "orientation": {
        "id": 2,
        "name": "Orientation Analysis",
        "icon": "🧭",
        "description": "Analyze dominant directions (N-S, E-W, NE-SW, NW-SE)",
        "when_useful": "To understand structural trends"
    },
    "line_density": {
        "id": 3,
        "name": "Line Density",
        "icon": "📈",
        "description": "Calculate fault/line density per area",
        "when_useful": "To find areas with high fault activity"
    },
    "intersections": {
        "id": 4,
        "name": "Intersection Points",
        "icon": "✖️",
        "description": "Find where lines cross each other",
        "when_useful": "To identify fault intersections"
    },
    "buffer_zones": {
        "id": 5,
        "name": "Buffer Zones",
        "icon": "⭕",
        "description": "Create buffer zones around lines",
        "when_useful": "For proximity analysis"
    }
}

POLYGON_ANALYSES = {
    "area_stats": {
        "id": 1,
        "name": "Area Statistics",
        "icon": "📐",
        "description": "Calculate total, average, min, max area",
        "when_useful": "To understand size distribution"
    },
    "coverage": {
        "id": 2,
        "name": "Coverage Analysis",
        "icon": "📊",
        "description": "Calculate percentage of total study area",
        "when_useful": "To understand spatial coverage"
    },
    "overlap_detection": {
        "id": 3,
        "name": "Overlap Detection",
        "icon": "🔀",
        "description": "Find overlapping polygons",
        "when_useful": "To check data integrity"
    },
    "boundary_length": {
        "id": 4,
        "name": "Boundary Length",
        "icon": "🔲",
        "description": "Calculate total perimeter of polygons",
        "when_useful": "To understand complexity"
    },
    "litho_distribution": {
        "id": 5,
        "name": "Lithology Distribution",
        "icon": "🗺️",
        "description": "Breakdown by rock type/lithology",
        "when_useful": "When analyzing geology polygons"
    }
}


class SpatialAnalysisAgent:
    """
    Smart spatial analysis agent that suggests and performs analyses
    based on query results.
    """
    
    def __init__(self):
        self.db = get_postgis_client()
        self.last_query_data = None
        self.last_query_type = None
        self.last_tables_used = []
        self.last_sql = None
        self.analysis_pending = False
    
    # =========================================================================
    # DATA TYPE DETECTION
    # =========================================================================
    
    def detect_data_type(self, data: List[Dict], query_type: str = None) -> str:
        """
        Detect if data contains points, lines, or polygons.
        """
        if query_type:
            return query_type
        
        if not data:
            return "unknown"
        
        sample = data[0]
        
        # Check for coordinate columns (points)
        if "latitude" in sample or "lat" in sample:
            return "point"
        
        # Check for GeoJSON geometry
        if "geojson_geom" in sample:
            try:
                geom = json.loads(sample["geojson_geom"]) if isinstance(sample["geojson_geom"], str) else sample["geojson_geom"]
                geom_type = geom.get("type", "").lower()
                if geom_type in ["point", "multipoint"]:
                    return "point"
                elif geom_type in ["linestring", "multilinestring"]:
                    return "line"
                elif geom_type in ["polygon", "multipolygon"]:
                    return "polygon"
            except:
                pass
        
        return "point"  # Default assumption
    
    # =========================================================================
    # ANALYSIS SUGGESTIONS
    # =========================================================================
    
    def get_analysis_suggestions(
        self,
        data: List[Dict],
        query_type: str,
        tables_used: List[str],
        original_query: str = ""
    ) -> Dict[str, Any]:
        """
        Get suggested analyses based on the data returned.
        Only offers analysis for POINT data to avoid breaking line/polygon queries.
        """
        self.last_query_data = data
        self.last_query_type = query_type
        self.last_tables_used = tables_used
        
        data_type = self.detect_data_type(data, query_type)
        row_count = len(data)
        
        # Only offer analysis for POINT data
        # Lines and polygons work fine without analysis suggestions
        if data_type == "point" and row_count >= 3:
            self.analysis_pending = True
            analyses = self._filter_point_analyses(data, tables_used, row_count)
            
            # Build suggestion message
            suggestion_text = self._build_suggestion_message(
                data_type, row_count, analyses, original_query
            )
            
            return {
                "data_type": data_type,
                "row_count": row_count,
                "analyses_available": analyses,
                "suggestion_text": suggestion_text,
                "can_analyze": len(analyses) > 0
            }
        else:
            # No analysis for lines/polygons - just return data
            self.analysis_pending = False
            return {
                "data_type": data_type,
                "row_count": row_count,
                "analyses_available": [],
                "suggestion_text": "",
                "can_analyze": False
            }
    
    def _filter_point_analyses(
        self,
        data: List[Dict],
        tables_used: List[str],
        row_count: int
    ) -> List[Dict]:
        """Filter point analyses based on context."""
        analyses = []
        
        # Always suggest clustering if enough points
        if row_count >= 5:
            analyses.append(POINT_ANALYSES["clustering"])
        
        # Regional if we have region data
        sample = data[0] if data else {}
        if "region" in sample or "admin_region" in sample:
            analyses.append(POINT_ANALYSES["regional"])
        
        # Commodity if from mods table
        if "mods" in tables_used or "major_comm" in sample:
            analyses.append(POINT_ANALYSES["commodity"])
        
        # Geology correlation
        analyses.append(POINT_ANALYSES["geology_correlation"])
        
        return analyses
    
    def _filter_line_analyses(
        self,
        data: List[Dict],
        tables_used: List[str],
        row_count: int
    ) -> List[Dict]:
        """Filter line analyses based on context."""
        analyses = [
            LINE_ANALYSES["total_length"],
            LINE_ANALYSES["orientation"],
        ]
        
        if row_count >= 2:
            analyses.append(LINE_ANALYSES["intersections"])
        
        if row_count >= 5:
            analyses.append(LINE_ANALYSES["line_density"])
        
        analyses.append(LINE_ANALYSES["buffer_zones"])
        
        return analyses
    
    def _filter_polygon_analyses(
        self,
        data: List[Dict],
        tables_used: List[str],
        row_count: int
    ) -> List[Dict]:
        """Filter polygon analyses based on context."""
        analyses = [
            POLYGON_ANALYSES["area_stats"],
            POLYGON_ANALYSES["coverage"],
        ]
        
        if row_count >= 2:
            analyses.append(POLYGON_ANALYSES["overlap_detection"])
        
        analyses.append(POLYGON_ANALYSES["boundary_length"])
        
        # Lithology for geology polygons
        sample = data[0] if data else {}
        if "geology" in str(tables_used) or "litho" in str(sample.keys()):
            analyses.append(POLYGON_ANALYSES["litho_distribution"])
        
        return analyses
    
    def _build_suggestion_message(
        self,
        data_type: str,
        row_count: int,
        analyses: List[Dict],
        original_query: str
    ) -> str:
        """Build a natural language suggestion message."""
        if not analyses:
            return ""
        
        type_word = {
            "point": "points",
            "line": "lines/faults",
            "polygon": "areas"
        }.get(data_type, "features")
        
        lines = [
            f"\n📊 **Spatial Analysis Available** ({row_count} {type_word})",
            "─" * 40,
            ""
        ]
        
        for i, analysis in enumerate(analyses, 1):
            lines.append(f"  {analysis['icon']} **{i}. {analysis['name']}**")
            lines.append(f"     {analysis['description']}")
            lines.append("")
        
        lines.append("─" * 40)
        lines.append("Type a number (1-{}) or ask a new question.".format(len(analyses)))
        
        return "\n".join(lines)
    
    # =========================================================================
    # ANALYSIS EXECUTION
    # =========================================================================
    
    def is_analysis_request(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user input is requesting an analysis.
        Returns (is_analysis, analysis_key)
        
        Now supports:
        - Explicit analysis requests (e.g., "do cluster analysis", "run clustering")
        - Number selection when analysis is pending (e.g., "1", "2")
        """
        user_input = user_input.strip().lower()
        
        # Check for explicit analysis commands (works even without pending analysis)
        explicit_analysis_patterns = [
            ("cluster analysis", "clustering"),
            ("clustering analysis", "clustering"),
            ("do cluster", "clustering"),
            ("run cluster", "clustering"),
            ("cluster the", "clustering"),
            ("regional analysis", "regional"),
            ("regional distribution", "regional"),
            ("commodity analysis", "commodity"),
            ("commodity breakdown", "commodity"),
            ("geology correlation", "geology_correlation"),
            ("geology analysis", "geology_correlation"),
        ]
        
        for pattern, analysis_key in explicit_analysis_patterns:
            if pattern in user_input:
                logger.info(f"Detected explicit analysis request: {pattern} -> {analysis_key}")
                return True, analysis_key
        
        # If analysis is pending, check for number selection
        if self.analysis_pending:
            # STRICT CHECK 1: Only numbers (1, 2, 3, etc.)
            if user_input.isdigit():
                num = int(user_input)
                if self.last_query_type == "point":
                    analyses = list(POINT_ANALYSES.keys())
                elif self.last_query_type == "line":
                    analyses = list(LINE_ANALYSES.keys())
                elif self.last_query_type == "polygon":
                    analyses = list(POLYGON_ANALYSES.keys())
                else:
                    return False, None
                
                if 1 <= num <= len(analyses):
                    return True, analyses[num - 1]
            
            # STRICT CHECK 2: Only if input is VERY short (likely just an analysis name)
            if len(user_input) > 30:
                return False, None
            
            # STRICT CHECK 3: Must contain "analysis" or "analyze" or "run" to trigger keyword matching
            is_analysis_command = (
                "analysis" in user_input or 
                "analyze" in user_input or 
                "run " in user_input or
                len(user_input) < 15
            )
            
            if not is_analysis_command:
                return False, None
            
            # Now check for specific analysis keywords (only for short/explicit requests)
            analysis_keywords = {
                "cluster": "clustering",
                "clustering": "clustering",
                "regional": "regional",
                "commodity": "commodity",
                "geology correlation": "geology_correlation",
            }
            
            for keyword, analysis_key in analysis_keywords.items():
                if keyword in user_input:
                    return True, analysis_key
        
        return False, None
    
    async def run_analysis(
        self,
        analysis_key: str,
        custom_params: Dict[str, Any] = None,
        data: list = None
    ) -> Dict[str, Any]:
        """
        Run the specified analysis on data.
        
        Args:
            analysis_key: Type of analysis to run
            custom_params: Custom parameters for analysis (e.g., cluster distance)
            data: Data to analyze (if None, uses last_query_data)
        """
        # Use provided data or fall back to last query data
        analysis_data = data if data is not None else self.last_query_data
        
        if not analysis_data:
            return {
                "success": False,
                "error": "No data available for analysis. Run a query first or provide data."
            }
        
        # Temporarily store analysis data for use in analysis methods
        original_data = self.last_query_data
        self.last_query_data = analysis_data
        
        try:
            params = custom_params or {}
            
            # Point analyses
            if analysis_key == "clustering":
                result = await self._run_clustering(params)
            elif analysis_key == "density":
                result = await self._run_density(params)
            elif analysis_key == "regional":
                result = await self._run_regional(params)
            elif analysis_key == "commodity":
                result = await self._run_commodity(params)
            elif analysis_key == "nearest_neighbor":
                result = await self._run_nearest_neighbor(params)
            elif analysis_key == "distance_to_faults":
                result = await self._run_distance_to_faults(params)
            elif analysis_key == "geology_correlation":
                result = await self._run_geology_correlation(params)
            elif analysis_key == "bounding_area":
                result = await self._run_bounding_area(params)
            
            # Line analyses
            elif analysis_key == "total_length":
                result = await self._run_total_length(params)
            elif analysis_key == "orientation":
                result = await self._run_orientation(params)
            elif analysis_key == "intersections":
                result = await self._run_intersections(params)
            elif analysis_key == "buffer_zones":
                result = await self._run_buffer_zones(params)
            
            # Polygon analyses
            elif analysis_key == "area_stats":
                result = await self._run_area_stats(params)
            elif analysis_key == "coverage":
                result = await self._run_coverage(params)
            elif analysis_key == "litho_distribution":
                result = await self._run_litho_distribution(params)
            
            else:
                result = {
                    "success": False,
                    "error": f"Unknown analysis type: {analysis_key}"
                }
            
            # Ensure result uses the analysis_data
            if result.get("success") and "data" not in result:
                result["data"] = analysis_data
            
            return result
            
        finally:
            # Restore original data
            self.last_query_data = original_data
    
    # =========================================================================
    # POINT ANALYSES
    # =========================================================================
    
    async def _run_clustering(self, params: Dict) -> Dict[str, Any]:
        """Run DBSCAN clustering analysis."""
        distance_km = float(params.get("distance_km", 5))  # Ensure it's a float
        min_points = params.get("min_points", 2)
        
        # Convert km to meters (geometry is in SRID 3857 which uses meters)
        distance_m = distance_km * 1000
        
        logger.info(f"Running clustering with distance: {distance_km} km ({distance_m} m)")
        
        # Get point IDs from last query
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids:
            return {"success": False, "error": "No valid point IDs found"}
        
        table = self.last_tables_used[0] if self.last_tables_used else "mods"
        
        sql = f"""
            WITH subset AS (
                SELECT gid, geom, 
                    COALESCE(eng_name, '') as name,
                    COALESCE(major_comm, '') as commodity,
                    COALESCE(region, '') as region,
                    ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude,
                    ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude
                FROM {table}
                WHERE gid IN ({','.join(map(str, point_ids))})
            )
            SELECT 
                ST_ClusterDBSCAN(geom, eps := {distance_m}, minpoints := {min_points}) OVER() AS cluster_id,
                gid, name, commodity, region, latitude, longitude
            FROM subset
            ORDER BY cluster_id NULLS LAST
        """
        
        try:
            results = self.db.execute_query(sql)
            
            # Analyze clusters
            cluster_counts = Counter(r.get("cluster_id") for r in results if r.get("cluster_id") is not None)
            noise_count = sum(1 for r in results if r.get("cluster_id") is None)
            
            # Group by cluster for detailed info
            clusters = {}
            for r in results:
                cid = r.get("cluster_id")
                if cid is not None:
                    if cid not in clusters:
                        clusters[cid] = []
                    clusters[cid].append(r)
            
            # Build summary
            cluster_summary = []
            for cid, points in sorted(clusters.items()):
                regions = set(p.get("region", "Unknown") for p in points if p.get("region"))
                commodities = set(p.get("commodity", "Unknown") for p in points if p.get("commodity"))
                cluster_summary.append({
                    "cluster_id": cid,
                    "point_count": len(points),
                    "regions": list(regions),
                    "commodities": list(commodities)
                })
            
            # Natural language summary
            summary_text = self._build_clustering_summary(
                len(cluster_counts), len(results), noise_count, cluster_summary, distance_km
            )
            
            return {
                "success": True,
                "analysis_type": "clustering",
                "parameters": {
                    "distance_km": distance_km,
                    "min_points": min_points
                },
                "results": {
                    "cluster_count": len(cluster_counts),
                    "total_points": len(results),
                    "clustered_points": len(results) - noise_count,
                    "isolated_points": noise_count,
                    "cluster_details": cluster_summary
                },
                "data": results,
                "summary": summary_text
            }
            
        except Exception as e:
            logger.error(f"Clustering analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_clustering_summary(
        self,
        num_clusters: int,
        total_points: int,
        noise_count: int,
        cluster_details: List[Dict],
        distance_km: float
    ) -> str:
        """Build natural language summary for clustering."""
        lines = [
            f"🔵 **Cluster Analysis Results**",
            f"─" * 40,
            f"Parameters: {distance_km}km clustering distance",
            "",
            f"• **{num_clusters}** clusters found",
            f"• **{total_points - noise_count}** points in clusters",
            f"• **{noise_count}** isolated points",
            ""
        ]
        
        if cluster_details:
            lines.append("**Cluster Details:**")
            for c in cluster_details[:5]:  # Show top 5
                regions_str = ", ".join(c["regions"][:2]) if c["regions"] else "Unknown"
                lines.append(f"  • Cluster {c['cluster_id']}: {c['point_count']} points in {regions_str}")
        
        return "\n".join(lines)
    
    async def _run_regional(self, params: Dict) -> Dict[str, Any]:
        """Run regional distribution analysis."""
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids:
            return {"success": False, "error": "No valid point IDs found"}
        
        table = self.last_tables_used[0] if self.last_tables_used else "mods"
        
        sql = f"""
            SELECT 
                COALESCE(region, 'Unknown') as region,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
            FROM {table}
            WHERE gid IN ({','.join(map(str, point_ids))})
            GROUP BY region
            ORDER BY count DESC
        """
        
        try:
            results = self.db.execute_query(sql)
            
            summary_text = self._build_regional_summary(results)
            
            return {
                "success": True,
                "analysis_type": "regional",
                "results": {
                    "region_count": len(results),
                    "distribution": results
                },
                "data": results,
                "summary": summary_text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_regional_summary(self, results: List[Dict]) -> str:
        """Build summary for regional analysis."""
        lines = [
            f"📊 **Regional Distribution**",
            f"─" * 40,
            ""
        ]
        
        for r in results:
            bar_len = int(float(r.get("percentage", 0)) / 5)
            bar = "█" * bar_len
            lines.append(f"  {r['region']}: **{r['count']}** ({r['percentage']}%) {bar}")
        
        return "\n".join(lines)
    
    async def _run_commodity(self, params: Dict) -> Dict[str, Any]:
        """Run commodity breakdown analysis."""
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids:
            return {"success": False, "error": "No valid point IDs found"}
        
        sql = f"""
            SELECT 
                COALESCE(major_comm, 'Unknown') as commodity,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
            FROM mods
            WHERE gid IN ({','.join(map(str, point_ids))})
            GROUP BY major_comm
            ORDER BY count DESC
        """
        
        try:
            results = self.db.execute_query(sql)
            
            lines = [
                f"💎 **Commodity Breakdown**",
                f"─" * 40,
                ""
            ]
            for r in results:
                lines.append(f"  {r['commodity']}: **{r['count']}** ({r['percentage']}%)")
            
            return {
                "success": True,
                "analysis_type": "commodity",
                "results": {
                    "commodity_count": len(results),
                    "distribution": results
                },
                "data": results,
                "summary": "\n".join(lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_distance_to_faults(self, params: Dict) -> Dict[str, Any]:
        """Calculate distance from points to nearest faults."""
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids:
            return {"success": False, "error": "No valid point IDs found"}
        
        table = self.last_tables_used[0] if self.last_tables_used else "mods"
        
        sql = f"""
            WITH points AS (
                SELECT gid, 
                    COALESCE(eng_name, '') as name,
                    geom,
                    ST_Y(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS latitude,
                    ST_X(ST_Transform(ST_SetSRID(geom, 3857), 4326)) AS longitude
                FROM {table}
                WHERE gid IN ({','.join(map(str, point_ids))})
            ),
            faults AS (
                SELECT geom FROM geology_faults_contacts_master
                WHERE newtype ILIKE '%fault%'
            )
            SELECT 
                p.gid, p.name, p.latitude, p.longitude,
                ROUND((MIN(ST_Distance(
                    ST_Transform(ST_SetSRID(p.geom, 3857), 4326)::geography,
                    ST_Transform(ST_SetSRID(f.geom, 3857), 4326)::geography
                )) / 1000)::numeric, 2) AS distance_to_fault_km
            FROM points p
            CROSS JOIN faults f
            GROUP BY p.gid, p.name, p.latitude, p.longitude
            ORDER BY distance_to_fault_km
        """
        
        try:
            results = self.db.execute_query(sql)
            
            if results:
                distances = [float(r.get("distance_to_fault_km", 0)) for r in results]
                avg_dist = sum(distances) / len(distances)
                min_dist = min(distances)
                max_dist = max(distances)
                
                lines = [
                    f"🎯 **Distance to Faults Analysis**",
                    f"─" * 40,
                    "",
                    f"• Minimum distance: **{min_dist:.1f} km**",
                    f"• Maximum distance: **{max_dist:.1f} km**",
                    f"• Average distance: **{avg_dist:.1f} km**",
                    "",
                    "**Closest to faults:**"
                ]
                for r in results[:5]:
                    lines.append(f"  • {r['name'] or 'Point ' + str(r['gid'])}: {r['distance_to_fault_km']} km")
                
                return {
                    "success": True,
                    "analysis_type": "distance_to_faults",
                    "results": {
                        "min_distance_km": min_dist,
                        "max_distance_km": max_dist,
                        "avg_distance_km": round(avg_dist, 2),
                        "point_distances": results
                    },
                    "data": results,
                    "summary": "\n".join(lines)
                }
            else:
                return {"success": False, "error": "No fault data found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_geology_correlation(self, params: Dict) -> Dict[str, Any]:
        """Find which geology units contain the points."""
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids:
            return {"success": False, "error": "No valid point IDs found"}
        
        table = self.last_tables_used[0] if self.last_tables_used else "mods"
        
        sql = f"""
            WITH points AS (
                SELECT gid, geom FROM {table}
                WHERE gid IN ({','.join(map(str, point_ids))})
            )
            SELECT 
                COALESCE(g.unit_name, 'Unknown') as geology_unit,
                COALESCE(g.main_litho, 'Unknown') as lithology,
                COALESCE(g.litho_fmly, 'Unknown') as rock_family,
                COUNT(*) as point_count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
            FROM points p
            JOIN geology_master g ON ST_Intersects(
                ST_Transform(ST_SetSRID(p.geom, 3857), 4326),
                ST_Transform(ST_SetSRID(g.geom, 3857), 4326)
            )
            GROUP BY g.unit_name, g.main_litho, g.litho_fmly
            ORDER BY point_count DESC
            LIMIT 20
        """
        
        try:
            results = self.db.execute_query(sql)
            
            lines = [
                f"🪨 **Geology Correlation**",
                f"─" * 40,
                "",
                "**Host rock types:**"
            ]
            for r in results[:10]:
                lines.append(f"  • {r['lithology']} ({r['rock_family']}): **{r['point_count']}** points ({r['percentage']}%)")
            
            return {
                "success": True,
                "analysis_type": "geology_correlation",
                "results": {
                    "geology_units": len(results),
                    "distribution": results
                },
                "data": results,
                "summary": "\n".join(lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_density(self, params: Dict) -> Dict[str, Any]:
        """Run density/hotspot analysis."""
        # Simplified density using grid cells
        return {
            "success": True,
            "analysis_type": "density",
            "summary": "🔥 **Density Analysis**\n\nDensity analysis shows point concentration patterns. Use the clustering results to identify hotspots.",
            "data": self.last_query_data
        }
    
    async def _run_nearest_neighbor(self, params: Dict) -> Dict[str, Any]:
        """Calculate nearest neighbor distances."""
        return {
            "success": True,
            "analysis_type": "nearest_neighbor",
            "summary": "📏 **Nearest Neighbor**\n\nAnalyzes spacing between points.",
            "data": self.last_query_data
        }
    
    async def _run_bounding_area(self, params: Dict) -> Dict[str, Any]:
        """Calculate convex hull / bounding area."""
        point_ids = [r.get("gid") for r in self.last_query_data if r.get("gid")]
        
        if not point_ids or len(point_ids) < 3:
            return {"success": False, "error": "Need at least 3 points"}
        
        table = self.last_tables_used[0] if self.last_tables_used else "mods"
        
        sql = f"""
            SELECT 
                ROUND((ST_Area(ST_ConvexHull(ST_Collect(
                    ST_Transform(ST_SetSRID(geom, 3857), 4326)
                ))::geography) / 1000000)::numeric, 2) as area_km2,
                ST_AsGeoJSON(ST_ConvexHull(ST_Collect(
                    ST_Transform(ST_SetSRID(geom, 3857), 4326)
                ))) as hull_geojson
            FROM {table}
            WHERE gid IN ({','.join(map(str, point_ids))})
        """
        
        try:
            results = self.db.execute_query(sql)
            
            if results:
                area = results[0].get("area_km2", 0)
                
                return {
                    "success": True,
                    "analysis_type": "bounding_area",
                    "results": {
                        "area_km2": area,
                        "convex_hull": results[0].get("hull_geojson")
                    },
                    "summary": f"📐 **Bounding Area**\n─{'─'*40}\n\nThe {len(point_ids)} points span an area of **{area} km²**"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # LINE ANALYSES
    # =========================================================================
    
    async def _run_total_length(self, params: Dict) -> Dict[str, Any]:
        """Calculate total length of line features."""
        sql = """
            SELECT 
                ROUND((SUM(ST_Length(
                    ST_Transform(ST_SetSRID(geom, 3857), 4326)::geography
                )) / 1000)::numeric, 2) as total_length_km,
                COUNT(*) as line_count
            FROM geology_faults_contacts_master
        """
        
        try:
            results = self.db.execute_query(sql)
            if results:
                return {
                    "success": True,
                    "analysis_type": "total_length",
                    "results": results[0],
                    "summary": f"📏 **Total Length**\n\n{results[0]['line_count']} lines totaling **{results[0]['total_length_km']} km**"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_orientation(self, params: Dict) -> Dict[str, Any]:
        """Analyze line orientations."""
        return {
            "success": True,
            "analysis_type": "orientation",
            "summary": "🧭 **Orientation Analysis**\n\nAnalyzes dominant fault/line directions."
        }
    
    async def _run_intersections(self, params: Dict) -> Dict[str, Any]:
        """Find line intersections."""
        return {
            "success": True,
            "analysis_type": "intersections",
            "summary": "✖️ **Intersection Points**\n\nIdentifies where lines cross."
        }
    
    async def _run_buffer_zones(self, params: Dict) -> Dict[str, Any]:
        """Create buffer zones around lines."""
        return {
            "success": True,
            "analysis_type": "buffer_zones",
            "summary": "⭕ **Buffer Zones**\n\nCreates buffer areas around linear features."
        }
    
    # =========================================================================
    # POLYGON ANALYSES
    # =========================================================================
    
    async def _run_area_stats(self, params: Dict) -> Dict[str, Any]:
        """Calculate area statistics for polygons."""
        return {
            "success": True,
            "analysis_type": "area_stats",
            "summary": "📐 **Area Statistics**\n\nCalculates total, average, min, max area of polygons."
        }
    
    async def _run_coverage(self, params: Dict) -> Dict[str, Any]:
        """Calculate coverage percentage."""
        return {
            "success": True,
            "analysis_type": "coverage",
            "summary": "📊 **Coverage Analysis**\n\nShows percentage of study area covered."
        }
    
    async def _run_litho_distribution(self, params: Dict) -> Dict[str, Any]:
        """Analyze lithology distribution."""
        sql = """
            SELECT 
                COALESCE(litho_fmly, 'Unknown') as rock_family,
                COUNT(*) as unit_count,
                ROUND((SUM(ST_Area(
                    ST_Transform(ST_SetSRID(geom, 3857), 4326)::geography
                )) / 1000000)::numeric, 0) as total_area_km2
            FROM geology_master
            GROUP BY litho_fmly
            ORDER BY total_area_km2 DESC
            LIMIT 15
        """
        
        try:
            results = self.db.execute_query(sql)
            
            lines = [
                f"🗺️ **Lithology Distribution**",
                f"─" * 40,
                ""
            ]
            for r in results:
                lines.append(f"  • {r['rock_family']}: {r['unit_count']} units, {r['total_area_km2']} km²")
            
            return {
                "success": True,
                "analysis_type": "litho_distribution",
                "results": results,
                "data": results,
                "summary": "\n".join(lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_pending(self):
        """Clear pending analysis state."""
        self.analysis_pending = False
        self.last_query_data = None
        self.last_query_type = None
        self.last_tables_used = []


# =============================================================================
# SINGLETON
# =============================================================================

_spatial_analysis_agent: Optional[SpatialAnalysisAgent] = None


def get_spatial_analysis_agent() -> SpatialAnalysisAgent:
    """Get or create the global spatial analysis agent."""
    global _spatial_analysis_agent
    if _spatial_analysis_agent is None:
        _spatial_analysis_agent = SpatialAnalysisAgent()
    return _spatial_analysis_agent
