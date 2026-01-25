"""
=============================================================================
GEOSPATIAL RAG - TOOL 2: 2D VISUALIZER (FULL GEOMETRY)
=============================================================================
Handles:
- Points (mods, borholes, surface_samples) 
- Polygons (geology_master) - actual polygon geometry
- Lines (geology_faults_contacts_master) - actual line geometry

Fixed:
- Better coordinate validation and debugging
- Logging for skipped rows
- Handles edge cases better
=============================================================================
"""

import logging
import json
from typing import Dict, Any, List, Optional

from database.postgis_client import get_postgis_client

logger = logging.getLogger(__name__)


class Visualizer2D:
    """Prepares geospatial data for 2D/3D map visualization."""
    
    def __init__(self):
        self.db = get_postgis_client()
    
    def _validate_coordinates(self, lat: float, lon: float) -> tuple:
        """
        Validate and fix coordinates for Saudi Arabia region.
        Returns (lat, lon) or (None, None) if invalid.
        """
        if lat is None or lon is None:
            return None, None
        
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert coordinates to float: lat={lat}, lon={lon}")
            return None, None
        
        # Check for NaN or Inf
        import math
        if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
            logger.warning(f"Invalid coordinate values (NaN/Inf): lat={lat}, lon={lon}")
            return None, None
        
        # Saudi Arabia bounds check (with some buffer)
        lat_valid = 10 <= lat <= 35
        lon_valid = 30 <= lon <= 60
        
        if lat_valid and lon_valid:
            return lat, lon
        
        # Check if coordinates are swapped (common mistake)
        if 30 <= lat <= 60 and 10 <= lon <= 35:
            logger.warning(f"Swapped coordinates detected, fixing: ({lat}, {lon}) -> ({lon}, {lat})")
            return lon, lat
        
        # Even if outside Saudi bounds, still return them (might be valid edge cases)
        # Just log a warning
        if not (lat_valid and lon_valid):
            logger.debug(f"Coordinates outside Saudi bounds (may be valid): lat={lat}, lon={lon}")
        
        return lat, lon
    
    def _detect_geometry_type(self, data: List[Dict], query_type: str = None) -> str:
        """Detect geometry type from data or query_type."""
        
        # Use query_type if provided - this is the most reliable
        if query_type in ['polygon', 'line', 'point']:
            logger.info(f"Using provided query_type: {query_type}")
            return query_type
        
        if not data:
            logger.warning("No data provided, defaulting to 'point'")
            return 'point'
        
        row = data[0]
        
        # Check for GeoJSON geometry column
        if 'geojson_geom' in row:
            try:
                geom = json.loads(row['geojson_geom']) if isinstance(row['geojson_geom'], str) else row['geojson_geom']
                geom_type = geom.get('type', '').lower()
                if 'polygon' in geom_type:
                    logger.info("Detected geometry type from geojson_geom: polygon")
                    return 'polygon'
                if 'line' in geom_type or 'string' in geom_type:
                    logger.info("Detected geometry type from geojson_geom: line")
                    return 'line'
            except Exception as e:
                logger.warning(f"Error parsing geojson_geom: {e}")
        
        # Check for point columns
        if 'latitude' in row and 'longitude' in row:
            logger.info("Detected geometry type from lat/lon columns: point")
            return 'point'
        
        logger.warning("Could not detect geometry type, defaulting to 'point'")
        return 'point'
    
    def _build_point_geojson(self, data: List[Dict]) -> Dict[str, Any]:
        """Build GeoJSON for point data."""
        features = []
        skipped_null = 0
        skipped_invalid = 0
        
        for row in data:
            lat = row.get('latitude')
            lon = row.get('longitude')
            
            # Check for null values before validation
            if lat is None or lon is None:
                skipped_null += 1
                continue
            
            lat, lon = self._validate_coordinates(lat, lon)
            if lat is None or lon is None:
                skipped_invalid += 1
                continue
            
            # Build properties (exclude geometry fields)
            properties = {}
            for k, v in row.items():
                if k.lower() not in ['latitude', 'longitude', 'geom', 'geojson_geom']:
                    if v is not None:
                        properties[k] = v if isinstance(v, (int, float, bool)) else str(v)
            
            properties['_geometry_type'] = 'point'
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]  # GeoJSON uses [lon, lat] order
                },
                "properties": properties
            })
        
        # Log statistics
        total = len(data)
        valid = len(features)
        if skipped_null > 0 or skipped_invalid > 0:
            logger.warning(
                f"Point GeoJSON: {valid}/{total} valid features. "
                f"Skipped: {skipped_null} null coords, {skipped_invalid} invalid coords"
            )
        else:
            logger.info(f"Point GeoJSON: Built {valid} features from {total} rows")
        
        return {"type": "FeatureCollection", "features": features}
    
    def _build_polygon_geojson(self, data: List[Dict]) -> Dict[str, Any]:
        """Build GeoJSON for polygon data (geology_master)."""
        features = []
        skipped_no_geom = 0
        skipped_parse_error = 0
        
        for row in data:
            geojson_str = row.get('geojson_geom')
            if not geojson_str:
                skipped_no_geom += 1
                continue
            
            try:
                geometry = json.loads(geojson_str) if isinstance(geojson_str, str) else geojson_str
            except (json.JSONDecodeError, TypeError) as e:
                skipped_parse_error += 1
                logger.debug(f"Failed to parse geojson_geom: {e}")
                continue
            
            # Build properties
            properties = {}
            for k, v in row.items():
                if k.lower() not in ['geom', 'geojson_geom']:
                    if v is not None:
                        properties[k] = v if isinstance(v, (int, float, bool)) else str(v)
            
            properties['_geometry_type'] = 'polygon'
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": properties
            })
        
        # Log statistics
        total = len(data)
        valid = len(features)
        if skipped_no_geom > 0 or skipped_parse_error > 0:
            logger.warning(
                f"Polygon GeoJSON: {valid}/{total} valid features. "
                f"Skipped: {skipped_no_geom} no geom, {skipped_parse_error} parse errors"
            )
        else:
            logger.info(f"Polygon GeoJSON: Built {valid} features from {total} rows")
        
        return {"type": "FeatureCollection", "features": features}
    
    def _build_line_geojson(self, data: List[Dict]) -> Dict[str, Any]:
        """Build GeoJSON for line data (faults/contacts)."""
        features = []
        skipped_no_geom = 0
        skipped_parse_error = 0
        
        for row in data:
            geojson_str = row.get('geojson_geom')
            if not geojson_str:
                skipped_no_geom += 1
                continue
            
            try:
                geometry = json.loads(geojson_str) if isinstance(geojson_str, str) else geojson_str
            except (json.JSONDecodeError, TypeError) as e:
                skipped_parse_error += 1
                logger.debug(f"Failed to parse geojson_geom: {e}")
                continue
            
            # Build properties
            properties = {}
            for k, v in row.items():
                if k.lower() not in ['geom', 'geojson_geom']:
                    if v is not None:
                        properties[k] = v if isinstance(v, (int, float, bool)) else str(v)
            
            properties['_geometry_type'] = 'line'
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": properties
            })
        
        # Log statistics
        total = len(data)
        valid = len(features)
        if skipped_no_geom > 0 or skipped_parse_error > 0:
            logger.warning(
                f"Line GeoJSON: {valid}/{total} valid features. "
                f"Skipped: {skipped_no_geom} no geom, {skipped_parse_error} parse errors"
            )
        else:
            logger.info(f"Line GeoJSON: Built {valid} features from {total} rows")
        
        return {"type": "FeatureCollection", "features": features}
    
    def to_geojson(self, data: List[Dict], query_type: str = None) -> Dict[str, Any]:
        """Convert query results to GeoJSON based on geometry type."""
        
        if not data:
            logger.warning("to_geojson called with empty data")
            return {"type": "FeatureCollection", "features": []}
        
        # Debug: log first row structure
        logger.info(f"to_geojson: Processing {len(data)} rows, query_type={query_type}")
        logger.debug(f"First row keys: {list(data[0].keys())}")
        
        geom_type = self._detect_geometry_type(data, query_type)
        
        if geom_type == 'polygon':
            return self._build_polygon_geojson(data)
        elif geom_type == 'line':
            return self._build_line_geojson(data)
        else:
            return self._build_point_geojson(data)
    
    def get_bounds(self, geojson: Dict[str, Any]) -> Dict[str, float]:
        """Calculate bounding box from GeoJSON."""
        if not geojson.get("features"):
            logger.warning("get_bounds called with no features")
            return None
        
        lats = []
        lons = []
        
        for feature in geojson["features"]:
            geom = feature.get("geometry", {})
            coords = self._extract_all_coords(geom)
            for lon, lat in coords:
                lons.append(lon)
                lats.append(lat)
        
        if not lats or not lons:
            logger.warning("No valid coordinates found for bounds calculation")
            return None
        
        bounds = {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "center_lat": sum(lats) / len(lats),
            "center_lon": sum(lons) / len(lons)
        }
        
        logger.info(f"Calculated bounds: center=({bounds['center_lat']:.4f}, {bounds['center_lon']:.4f})")
        return bounds
    
    def _extract_all_coords(self, geometry: Dict) -> List[tuple]:
        """Extract all coordinate pairs from any geometry type."""
        coords = []
        geom_type = geometry.get('type', '')
        geom_coords = geometry.get('coordinates', [])
        
        if geom_type == 'Point':
            if len(geom_coords) >= 2:
                coords.append((geom_coords[0], geom_coords[1]))
        
        elif geom_type == 'LineString':
            for c in geom_coords:
                if len(c) >= 2:
                    coords.append((c[0], c[1]))
        
        elif geom_type == 'MultiLineString':
            for line in geom_coords:
                for c in line:
                    if len(c) >= 2:
                        coords.append((c[0], c[1]))
        
        elif geom_type == 'Polygon':
            for ring in geom_coords:
                for c in ring:
                    if len(c) >= 2:
                        coords.append((c[0], c[1]))
        
        elif geom_type == 'MultiPolygon':
            for polygon in geom_coords:
                for ring in polygon:
                    for c in ring:
                        if len(c) >= 2:
                            coords.append((c[0], c[1]))
        
        return coords
    
    def prepare_visualization(
        self,
        data: List[Dict[str, Any]],
        layer_name: str = "Query Results",
        color: str = "#3388ff",
        popup_fields: Optional[List[str]] = None,
        query_type: str = None
    ) -> Dict[str, Any]:
        """
        Main method to prepare visualization data.
        Called by main.py!
        """
        logger.info(f"prepare_visualization: {len(data)} rows, layer_name='{layer_name}', query_type={query_type}")
        
        # Debug: Check for coordinates in raw data
        if data:
            sample = data[0]
            has_lat = 'latitude' in sample and sample['latitude'] is not None
            has_lon = 'longitude' in sample and sample['longitude'] is not None
            has_geojson = 'geojson_geom' in sample and sample['geojson_geom'] is not None
            logger.info(f"Raw data check - has_latitude: {has_lat}, has_longitude: {has_lon}, has_geojson_geom: {has_geojson}")
            if has_lat and has_lon:
                logger.info(f"Sample coordinates: lat={sample['latitude']}, lon={sample['longitude']}")
        
        geojson = self.to_geojson(data, query_type)
        bounds = self.get_bounds(geojson)
        
        # Detect layer type
        layer_type = "point"
        if geojson.get("features"):
            first_props = geojson["features"][0].get("properties", {})
            layer_type = first_props.get("_geometry_type", "point")
        
        # Infer popup fields
        if popup_fields is None and geojson.get("features"):
            first_props = geojson["features"][0].get("properties", {})
            popup_fields = [k for k in list(first_props.keys())[:10] if not k.startswith('_')]
        
        result = {
            "layer_name": layer_name,
            "geojson": geojson,
            "bounds": bounds,
            "feature_count": len(geojson.get("features", [])),
            "layer_type": layer_type,
            "style": {"color": color, "fillColor": color},
            "popup_fields": popup_fields
        }
        
        logger.info(f"Visualization prepared: {result['feature_count']} features, layer_type='{layer_type}'")
        
        # CRITICAL: Warn if we lost data
        if len(data) > 0 and result['feature_count'] == 0:
            logger.error(
                f"CRITICAL: All {len(data)} rows were filtered out! "
                f"Check coordinate columns in SQL query."
            )
        elif result['feature_count'] < len(data):
            logger.warning(
                f"Data loss: {len(data)} input rows -> {result['feature_count']} output features "
                f"({len(data) - result['feature_count']} rows filtered)"
            )
        
        return result
    
    def create_heatmap_data(
        self, 
        data: List[Dict], 
        lat_field: str = "latitude", 
        lon_field: str = "longitude",
        weight_field: str = None
    ) -> List[List[float]]:
        """Prepare heatmap data as [[lat, lon, weight], ...]"""
        heatmap_data = []
        skipped = 0
        
        for row in data:
            lat, lon = self._validate_coordinates(row.get(lat_field), row.get(lon_field))
            if lat and lon:
                weight = float(row.get(weight_field, 1.0)) if weight_field else 1.0
                heatmap_data.append([lat, lon, weight])
            else:
                skipped += 1
        
        if skipped > 0:
            logger.warning(f"Heatmap: Skipped {skipped} rows with invalid coordinates")
        
        logger.info(f"Heatmap data: {len(heatmap_data)} valid points")
        return heatmap_data
    
    def create_cluster_config(
        self, 
        data: List[Dict], 
        layer_name: str = "Clustered",
        max_cluster_radius: int = 50
    ) -> Dict[str, Any]:
        """Prepare cluster config for marker clustering."""
        geojson = self.to_geojson(data, query_type='point')
        
        return {
            "layer_name": layer_name,
            "geojson": geojson,
            "bounds": self.get_bounds(geojson),
            "feature_count": len(geojson.get("features", [])),
            "cluster_options": {"maxClusterRadius": max_cluster_radius}
        }
    
    def debug_data(self, data: List[Dict], limit: int = 3) -> None:
        """Debug helper to inspect data structure."""
        if not data:
            logger.info("DEBUG: Data is empty")
            return
        
        logger.info(f"DEBUG: Total rows: {len(data)}")
        logger.info(f"DEBUG: Columns: {list(data[0].keys())}")
        
        for i, row in enumerate(data[:limit]):
            logger.info(f"DEBUG: Row {i}:")
            for k, v in row.items():
                v_str = str(v)[:100] if v else "None"
                logger.info(f"  {k}: {v_str}")


_visualizer_2d: Optional[Visualizer2D] = None

def get_visualizer_2d() -> Visualizer2D:
    """Get or create the global 2D visualizer."""
    global _visualizer_2d
    if _visualizer_2d is None:
        _visualizer_2d = Visualizer2D()
    return _visualizer_2d