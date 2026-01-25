"""
=============================================================================
GEOSPATIAL ORCHESTRATOR
=============================================================================
Main controller that routes user input to either:
1. SQL Generator (for data queries)
2. Spatial Analysis Agent (for analysis requests)

Flow:
    User Input → Is it an analysis request?
                    ↓ NO              ↓ YES
              SQL Generator      Analysis Agent
                    ↓                   ↓
              Execute Query      Run Analysis
                    ↓                   ↓
              Return Data +      Return Results +
              Suggest Analyses   Visualization
=============================================================================
"""

import logging
from typing import Dict, Any, Optional, Tuple

from tools.tool1_sql_generator import get_sql_generator
from tools.spatial_analysis_agent import get_spatial_analysis_agent
from tools.analysis_visualizer import get_analysis_visualizer

logger = logging.getLogger(__name__)


class GeospatialOrchestrator:
    """
    Main orchestrator for geospatial queries and analysis.
    
    Handles:
    - Routing between SQL generator and analysis agent
    - Storing query results for subsequent analysis
    - Generating visualization data
    """
    
    def __init__(self):
        self.sql_generator = get_sql_generator()
        self.analysis_agent = get_spatial_analysis_agent()
        self.visualizer = get_analysis_visualizer()
        
        # State tracking
        self.last_query_result = None
        self.pending_analysis = False
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return appropriate response.
        
        Args:
            user_input: Natural language query or analysis request
            
        Returns:
            Response dict with data, visualizations, and suggestions
        """
        user_input = user_input.strip()
        
        if not user_input:
            return {
                "success": False,
                "error": "Empty input",
                "response": "Please enter a query."
            }
        
        # Check if this is an analysis request (number or keyword)
        # This now works even without pending analysis (for explicit requests like "do cluster analysis")
        is_analysis, analysis_key = self.analysis_agent.is_analysis_request(user_input)
        
        if is_analysis and analysis_key:
            # For explicit analysis requests, try to use last query data if available
            data_to_use = None
            if self.last_query_result and self.last_query_result.get("data"):
                data_to_use = self.last_query_result["data"]
            
            return await self._handle_analysis_request(analysis_key, data=data_to_use)
        else:
            # Clear any pending analysis state when new query comes in
            self.analysis_agent.clear_pending()
            return await self._handle_data_query(user_input)
    
    async def _handle_data_query(self, query: str) -> Dict[str, Any]:
        """
        Handle a data query (goes to SQL generator).
        """
        logger.info(f"Processing data query: {query[:100]}...")
        
        try:
            # Execute the SQL query
            result = await self.sql_generator.execute(query)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Query failed"),
                    "response": f"Sorry, I couldn't process that query: {result.get('error', 'Unknown error')}",
                    "sql_query": result.get("sql_query")
                }
            
            # Store for potential analysis
            self.last_query_result = result
            
            # Get analysis suggestions
            data = result.get("data", [])
            query_type = result.get("query_type", "point")
            tables_used = result.get("tables_used", [])
            
            suggestions = self.analysis_agent.get_analysis_suggestions(
                data=data,
                query_type=query_type,
                tables_used=tables_used,
                original_query=query
            )
            
            # Store SQL for potential re-use
            self.analysis_agent.last_sql = result.get("sql_query")
            
            # Build response
            row_count = result.get("row_count", 0)
            description = result.get("description", "")
            
            # Build visualization for map
            visualization = self._build_query_visualization(data, query_type, tables_used)
            
            response_text = self._build_query_response(
                description=description,
                row_count=row_count,
                query_type=query_type,
                suggestions=suggestions,
                data=data,
                tables_used=tables_used
            )
            
            return {
                "success": True,
                "response": response_text,
                "data": data,
                "row_count": row_count,
                "query_type": query_type,
                "sql_query": result.get("sql_query"),
                "visualization": visualization,
                "analysis_available": suggestions.get("can_analyze", False),
                "analysis_options": suggestions.get("analyses_available", [])
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"An error occurred: {str(e)}"
            }
    
    async def _handle_analysis_request(
        self, 
        analysis_key: str, 
        data: list = None,
        custom_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle an analysis request.
        
        Args:
            analysis_key: Analysis type to run
            data: Optional data to analyze (if None, uses last query result)
            custom_params: Custom parameters for analysis
        """
        logger.info(f"Processing analysis request: {analysis_key}")
        
        try:
            # Use provided data or fall back to last query result
            analysis_data = data
            if analysis_data is None:
                if self.last_query_result and self.last_query_result.get("data"):
                    analysis_data = self.last_query_result["data"]
                else:
                    return {
                        "success": False,
                        "error": "No data available for analysis",
                        "response": "Please run a query first to get data for analysis."
                    }
            
            # Run the analysis on the provided data with custom parameters
            result = await self.analysis_agent.run_analysis(
                analysis_key, 
                data=analysis_data,
                custom_params=custom_params
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Analysis failed"),
                    "response": f"Analysis failed: {result.get('error', 'Unknown error')}"
                }
            
            # Generate visualization
            visualization = self.visualizer.generate_visualization(
                analysis_type=result.get("analysis_type"),
                analysis_results=result,
                data=result.get("data", [])
            )
            
            return {
                "success": True,
                "response": result.get("summary", "Analysis completed."),
                "analysis_type": result.get("analysis_type"),
                "results": result.get("results"),
                "data": result.get("data"),
                "visualization": visualization,
                "is_analysis_result": True
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "response": f"Analysis error: {str(e)}"
            }
    
    async def run_analysis_on_data(
        self, 
        analysis_key: str, 
        data: list,
        custom_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run analysis on provided data (for filtered/current table data).
        
        Args:
            analysis_key: Analysis type to run
            data: Data to analyze
            custom_params: Custom parameters (e.g., cluster_distance_km)
            
        Returns:
            Analysis results with visualization
        """
        return await self._handle_analysis_request(analysis_key, data=data, custom_params=custom_params)
    
    def _build_query_visualization(
        self,
        data: list,
        query_type: str,
        tables_used: list = None
    ) -> Dict[str, Any]:
        """Build visualization data for query results."""
        import json as json_module
        
        features = []
        
        for row in data:
            # Handle polygon/line data (check first since they have geojson_geom)
            if "geojson_geom" in row and row["geojson_geom"]:
                try:
                    geom = row["geojson_geom"]
                    if isinstance(geom, str):
                        geom = json_module.loads(geom)
                    
                    features.append({
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {
                            k: v for k, v in row.items()
                            if k not in ["geom", "geojson_geom"]
                        }
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse geojson_geom: {e}")
            
            # Handle point data (latitude/longitude columns)
            elif query_type == "point":
                lat = row.get("latitude") or row.get("lat")
                lon = row.get("longitude") or row.get("lon") or row.get("lng")
                
                if lat and lon:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            k: v for k, v in row.items()
                            if k not in ["geom", "geojson_geom", "latitude", "longitude", "lat", "lon", "lng"]
                        }
                    })
        
        result = {
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            },
            "layer_type": query_type,
            "feature_count": len(features)
        }
        
        # Check if this is a spatial join (points with geology polygons)
        # If so, also fetch and return the involved polygon boundaries
        tables_used = tables_used or []
        is_spatial_join = (
            query_type == "point" and 
            'geology_master' in tables_used and
            ('mods' in tables_used or 'borholes' in tables_used or 'surface_samples' in tables_used)
        )
        
        if is_spatial_join and data:
            polygon_data = self._fetch_spatial_join_polygons(data)
            if polygon_data:
                result["polygon_overlay"] = polygon_data
        
        return result
    
    def _fetch_spatial_join_polygons(self, point_data: list) -> Optional[Dict[str, Any]]:
        """
        Fetch the polygon boundaries for a spatial join query.
        Uses spatial intersection to find ALL polygons that contain the points.
        Returns polygons with point counts.
        """
        from database import get_postgis_client
        import json as json_module
        
        try:
            db = get_postgis_client()
            
            if not point_data:
                return None
            
            # Get point GIDs and coordinates
            point_gids = []
            point_coords = []
            
            for row in point_data:
                gid = row.get("gid")
                if gid:
                    point_gids.append(int(gid))
                
                lat = row.get("latitude") or row.get("lat")
                lon = row.get("longitude") or row.get("lon") or row.get("lng")
                if lat and lon:
                    point_coords.append((float(lon), float(lat)))
            
            # Use spatial join to find ALL polygons containing these points
            if point_gids:
                # Most efficient: Use GIDs to find polygons via spatial join
                gids_list = ", ".join(map(str, point_gids[:1000]))  # Limit to avoid query size issues
                query = f"""
                SELECT DISTINCT
                    g.gid,
                    g.unit_name,
                    g.litho_fmly,
                    g.main_litho,
                    ST_AsGeoJSON(
                        ST_Transform(
                            ST_Simplify(g.geom, 200),
                            4326
                        )
                    ) AS geojson_geom,
                    COUNT(DISTINCT m.gid) AS point_count
                FROM geology_master g
                INNER JOIN mods m ON ST_Intersects(
                    ST_Transform(ST_SetSRID(g.geom, 3857), 4326),
                    ST_Transform(ST_SetSRID(m.geom, 3857), 4326)
                )
                WHERE m.gid IN ({gids_list})
                GROUP BY g.gid, g.unit_name, g.litho_fmly, g.main_litho, g.geom
                ORDER BY point_count DESC
                LIMIT 500;
                """
            elif point_coords and len(point_coords) <= 500:
                # Fallback: Use coordinates (slower but works)
                # Create point geometries and find intersecting polygons
                coords_values = ", ".join([f"({lon}, {lat})" for lon, lat in point_coords])
                query = f"""
                WITH point_geoms AS (
                    SELECT ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS geom
                    FROM (VALUES {coords_values}) AS points(lon, lat)
                )
                SELECT DISTINCT
                    g.gid,
                    g.unit_name,
                    g.litho_fmly,
                    g.main_litho,
                    ST_AsGeoJSON(
                        ST_Transform(
                            ST_Simplify(g.geom, 200),
                            4326
                        )
                    ) AS geojson_geom,
                    (SELECT COUNT(*) 
                     FROM point_geoms p 
                     WHERE ST_Intersects(
                         ST_Transform(ST_SetSRID(g.geom, 3857), 4326),
                         p.geom
                     )) AS point_count
                FROM geology_master g
                WHERE EXISTS (
                    SELECT 1 FROM point_geoms p
                    WHERE ST_Intersects(
                        ST_Transform(ST_SetSRID(g.geom, 3857), 4326),
                        p.geom
                    )
                )
                LIMIT 500;
                """
            else:
                # Too many points or no coordinates - fallback to name matching
                logger.warning("Too many points or no coordinates, using name-based matching")
                return self._fetch_polygons_by_name(point_data)
            
            result = db.execute_query(query)
            
            if not result:
                # Fallback: Use name-based matching if spatial query fails
                logger.warning("Spatial query failed, falling back to name-based matching")
                return self._fetch_polygons_by_name(point_data)
            
            # Build polygon features with point counts
            polygon_features = []
            for row in result:
                if row.get("geojson_geom"):
                    try:
                        geom = row["geojson_geom"]
                        if isinstance(geom, str):
                            geom = json_module.loads(geom)
                        
                        polygon_features.append({
                            "type": "Feature",
                            "geometry": geom,
                            "properties": {
                                "gid": int(row.get("gid", 0)),  # Unique identifier for each polygon
                                "unit_name": row.get("unit_name", "Unknown"),
                                "litho_fmly": row.get("litho_fmly"),
                                "main_litho": row.get("main_litho"),
                                "point_count": int(row.get("point_count", 0))
                            }
                        })
                    except Exception as e:
                        logger.debug(f"Failed to parse polygon geom: {e}")
            
            if not polygon_features:
                return None
            
            logger.info(f"Fetched {len(polygon_features)} polygons for spatial join overlay")
            
            return {
                "geojson": {
                    "type": "FeatureCollection",
                    "features": polygon_features
                },
                "layer_type": "polygon",
                "feature_count": len(polygon_features),
                "is_overlay": True
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch spatial join polygons: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to name-based matching
            return self._fetch_polygons_by_name(point_data)
    
    def _fetch_polygons_by_name(self, point_data: list) -> Optional[Dict[str, Any]]:
        """Fallback method: Fetch polygons by matching unit names."""
        from database import get_postgis_client
        import json as json_module
        
        try:
            db = get_postgis_client()
            
            # Get unique geology identifiers from the point data
            geology_names = set()
            geology_field = None
            
            # Find which geology field is present
            for field in ['geology', 'unit_name', 'litho_fmly']:
                if point_data and field in point_data[0]:
                    geology_field = field
                    break
            
            if not geology_field:
                return None
            
            # Count points per geology type
            geology_counts = {}
            for row in point_data:
                geo_name = row.get(geology_field)
                if geo_name:
                    geology_counts[geo_name] = geology_counts.get(geo_name, 0) + 1
                    geology_names.add(geo_name)
            
            if not geology_names:
                return None
            
            # Build query to fetch polygon boundaries
            names_list = "', '".join([n.replace("'", "''") for n in geology_names])
            
            query = f"""
            SELECT 
                gid,
                unit_name,
                litho_fmly,
                main_litho,
                ST_AsGeoJSON(
                    ST_Transform(
                        ST_Simplify(geom, 200),
                        4326
                    )
                ) AS geojson_geom
            FROM geology_master
            WHERE unit_name IN ('{names_list}')
            LIMIT 500;
            """
            
            result = db.execute_query(query)
            
            if not result:
                return None
            
            # Build polygon features with point counts
            polygon_features = []
            for row in result:
                if row.get("geojson_geom"):
                    try:
                        geom = row["geojson_geom"]
                        if isinstance(geom, str):
                            geom = json_module.loads(geom)
                        
                        unit_name = row.get("unit_name", "Unknown")
                        point_count = geology_counts.get(unit_name, 0)
                        
                        polygon_features.append({
                            "type": "Feature",
                            "geometry": geom,
                            "properties": {
                                "gid": int(row.get("gid", 0)),  # Unique identifier for each polygon
                                "unit_name": unit_name,
                                "litho_fmly": row.get("litho_fmly"),
                                "main_litho": row.get("main_litho"),
                                "point_count": point_count
                            }
                        })
                    except Exception as e:
                        logger.debug(f"Failed to parse polygon geom: {e}")
            
            if not polygon_features:
                return None
            
            return {
                "geojson": {
                    "type": "FeatureCollection",
                    "features": polygon_features
                },
                "layer_type": "polygon",
                "feature_count": len(polygon_features),
                "is_overlay": True
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch polygons by name: {e}")
            return None
    
    def _build_query_response(
        self,
        description: str,
        row_count: int,
        query_type: str,
        suggestions: Dict[str, Any],
        data: list = None,
        tables_used: list = None
    ) -> str:
        """Build the response text for a query with intelligent summarization."""
        
        type_word = {
            "point": "point",
            "line": "line",
            "polygon": "area"
        }.get(query_type, "feature")
        
        plural = "s" if row_count != 1 else ""
        
        lines = []
        
        if description:
            lines.append(description)
            lines.append("")
        
        lines.append(f"Found **{row_count}** {type_word}{plural}.")
        
        # Generate intelligent summary based on data
        if data and row_count > 0:
            summary = self._generate_data_summary(data, query_type, tables_used or [])
            if summary:
                lines.append("")
                lines.append("**Summary:**")
                lines.append(summary)
        
        # Add analysis suggestions if available
        if suggestions.get("can_analyze") and suggestions.get("suggestion_text"):
            lines.append("")
            lines.append(suggestions["suggestion_text"])
        
        return "\n".join(lines)
    
    def _generate_data_summary(
        self,
        data: list,
        query_type: str,
        tables_used: list
    ) -> str:
        """
        Generate an intelligent summary of the retrieved data.
        
        - For spatial joins (points + polygons): count points per polygon type
        - For points: summarize by commodity, region, or other key fields
        - For polygons/lines: summarize by type
        """
        if not data:
            return ""
        
        summary_parts = []
        
        # Check if this is a spatial join (points with geology info)
        is_spatial_join = (
            'geology_master' in tables_used or 
            any('litho' in str(row.keys()).lower() or 'geology' in str(row.keys()).lower() 
                for row in data[:1])
        )
        
        # For spatial joins: count points per geology type
        if is_spatial_join and query_type == "point":
            geology_counts = {}
            geology_field = None
            
            # Find the geology field
            for field in ['litho_fmly', 'geology', 'unit_name', 'family_dv', 'rock_type']:
                if field in data[0]:
                    geology_field = field
                    break
            
            if geology_field:
                for row in data:
                    geo_type = row.get(geology_field, 'Unknown')
                    if geo_type and geo_type != 'Unknown':
                        # Truncate long names
                        if len(str(geo_type)) > 30:
                            geo_type = str(geo_type)[:27] + "..."
                        geology_counts[geo_type] = geology_counts.get(geo_type, 0) + 1
                
                if geology_counts:
                    # Sort by count, take top 5
                    sorted_counts = sorted(geology_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                    geo_summary = ", ".join([f"{name}: **{count}**" for name, count in sorted_counts])
                    
                    if len(geology_counts) > 5:
                        geo_summary += f" (+{len(geology_counts) - 5} more types)"
                    
                    summary_parts.append(f"By geology type: {geo_summary}")
        
        # Summarize by commodity (for mineral deposits)
        if query_type == "point":
            commodity_field = None
            for field in ['major_comm', 'commodity', 'mineral', 'minor_comm']:
                if field in data[0]:
                    commodity_field = field
                    break
            
            if commodity_field:
                commodity_counts = {}
                for row in data:
                    comm = row.get(commodity_field, '')
                    if comm and comm.strip():
                        # Handle multiple commodities separated by ;
                        comms = [c.strip() for c in str(comm).split(';') if c.strip()]
                        for c in comms[:2]:  # Take first 2 if multiple
                            if len(c) > 20:
                                c = c[:17] + "..."
                            commodity_counts[c] = commodity_counts.get(c, 0) + 1
                
                if commodity_counts and len(commodity_counts) > 1:
                    sorted_comms = sorted(commodity_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                    comm_summary = ", ".join([f"{name}: **{count}**" for name, count in sorted_comms])
                    summary_parts.append(f"By commodity: {comm_summary}")
        
        # Summarize by region
        if 'region' in data[0]:
            region_counts = {}
            for row in data:
                region = row.get('region', '')
                if region and region.strip():
                    region_counts[region] = region_counts.get(region, 0) + 1
            
            if region_counts and len(region_counts) > 1:
                sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:4]
                region_summary = ", ".join([f"{name}: **{count}**" for name, count in sorted_regions])
                if len(region_counts) > 4:
                    region_summary += f" (+{len(region_counts) - 4} more)"
                summary_parts.append(f"By region: {region_summary}")
        
        # For lines (faults): summarize by type
        if query_type == "line":
            type_field = None
            for field in ['newtype', 'fault_type', 'type', 'ltype']:
                if field in data[0]:
                    type_field = field
                    break
            
            if type_field:
                type_counts = {}
                for row in data:
                    t = row.get(type_field, 'Unknown')
                    if t:
                        type_counts[t] = type_counts.get(t, 0) + 1
                
                if type_counts:
                    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:4]
                    type_summary = ", ".join([f"{name}: **{count}**" for name, count in sorted_types])
                    summary_parts.append(f"By type: {type_summary}")
        
        # For polygons: summarize by lithology
        if query_type == "polygon":
            litho_field = None
            for field in ['litho_fmly', 'family_dv', 'rock_type', 'unit_name']:
                if field in data[0]:
                    litho_field = field
                    break
            
            if litho_field:
                litho_counts = {}
                for row in data:
                    litho = row.get(litho_field, 'Unknown')
                    if litho and litho != 'Unknown':
                        if len(str(litho)) > 25:
                            litho = str(litho)[:22] + "..."
                        litho_counts[litho] = litho_counts.get(litho, 0) + 1
                
                if litho_counts:
                    sorted_litho = sorted(litho_counts.items(), key=lambda x: x[1], reverse=True)[:4]
                    litho_summary = ", ".join([f"{name}: **{count}**" for name, count in sorted_litho])
                    summary_parts.append(f"By lithology: {litho_summary}")
        
        # Combine all summaries
        return "\n".join(summary_parts) if summary_parts else ""
    
    def clear_state(self):
        """Clear all stored state."""
        self.last_query_result = None
        self.pending_analysis = False
        self.analysis_agent.clear_pending()


# =============================================================================
# SIMPLE API WRAPPER
# =============================================================================

class SimpleGeospatialAPI:
    """
    Simple API wrapper for easy integration.
    
    Usage:
        api = SimpleGeospatialAPI()
        result = await api.query("show gold deposits in Makkah")
        print(result["response"])
        
        # User selects analysis
        result = await api.query("1")  # Run clustering
        print(result["response"])
    """
    
    def __init__(self):
        self.orchestrator = GeospatialOrchestrator()
    
    async def query(self, user_input: str) -> Dict[str, Any]:
        """Process a user query or analysis request."""
        return await self.orchestrator.process(user_input)
    
    def reset(self):
        """Reset all state."""
        self.orchestrator.clear_state()


# =============================================================================
# SINGLETON
# =============================================================================

_orchestrator: Optional[GeospatialOrchestrator] = None


def get_orchestrator() -> GeospatialOrchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GeospatialOrchestrator()
    return _orchestrator
