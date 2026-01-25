"""
=============================================================================
GEOSPATIAL RAG - TOOL 3: 3D VISUALIZER (FIXED)
=============================================================================
Prepares data for CesiumJS 3D globe visualization
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
import json
import re

from config import settings

logger = logging.getLogger(__name__)


class Visualizer3D:
    """Prepares geospatial data for CesiumJS 3D visualization."""
    
    def __init__(self):
        self.cesium_token = settings.cesium_ion_token
    
    def to_czml(
        self,
        data: List[Dict[str, Any]],
        lat_field: str = "latitude",
        lon_field: str = "longitude",
        height_field: str = "elevation",
        name_field: str = "eng_name",
        document_name: str = "Geospatial Data"
    ) -> List[Dict[str, Any]]:
        """
        Convert query results to CZML format for CesiumJS.
        """
        # CZML document packet (required first)
        czml = [
            {
                "id": "document",
                "name": document_name,
                "version": "1.0"
            }
        ]
        
        logger.info(f"Converting {len(data)} records to CZML")
        
        for i, row in enumerate(data):
            # Try multiple field names for latitude
            lat = None
            for field in [lat_field, 'latitude', 'lat', 'y']:
                if field in row and row[field] is not None:
                    try:
                        lat = float(row[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Try multiple field names for longitude
            lon = None
            for field in [lon_field, 'longitude', 'lon', 'x']:
                if field in row and row[field] is not None:
                    try:
                        lon = float(row[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if lat is None or lon is None:
                logger.warning(f"Skipping row {i}: no valid coordinates. Row keys: {list(row.keys())}")
                continue
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.warning(f"Skipping row {i}: invalid coordinates lat={lat}, lon={lon}")
                continue
            
            # Get height (default to 100m for visibility)
            height = 100
            if height_field in row and row[height_field]:
                try:
                    height_str = str(row[height_field])
                    # Extract number from string like "1500m" or "1500 meters"
                    match = re.search(r'[\d.]+', height_str)
                    if match:
                        height = float(match.group()) + 100  # Add 100m for visibility
                except (ValueError, TypeError):
                    height = 100
            
            # Get name
            name = None
            for field in [name_field, 'eng_name', 'name', 'arb_name', 'borehole_i', 'sampleid']:
                if field in row and row[field]:
                    name = str(row[field])
                    break
            if not name:
                name = f"Point {i+1}"
            
            # Build description HTML from all properties
            description_parts = []
            for key, value in row.items():
                if key not in [lat_field, lon_field, 'geom', 'geometry'] and value is not None:
                    description_parts.append(f"<tr><td><b>{key}</b></td><td>{value}</td></tr>")
            description_html = f"<table>{''.join(description_parts)}</table>" if description_parts else ""
            
            # Create CZML packet for this point
            packet = {
                "id": f"point_{i}",
                "name": name,
                "description": description_html,
                "position": {
                    "cartographicDegrees": [lon, lat, height]
                },
                "point": {
                    "color": {
                        "rgba": [255, 165, 0, 255]  # Orange
                    },
                    "pixelSize": 15,
                    "outlineColor": {
                        "rgba": [255, 255, 255, 255]  # White outline
                    },
                    "outlineWidth": 3,
                    "heightReference": "RELATIVE_TO_GROUND"
                },
                "label": {
                    "text": name[:25] if name else "",
                    "font": "14pt sans-serif",
                    "style": "FILL_AND_OUTLINE",
                    "outlineWidth": 2,
                    "outlineColor": {
                        "rgba": [0, 0, 0, 255]
                    },
                    "verticalOrigin": "BOTTOM",
                    "pixelOffset": {
                        "cartesian2": [0, -20]
                    },
                    "showBackground": True,
                    "backgroundColor": {
                        "rgba": [0, 0, 0, 180]
                    }
                }
            }
            czml.append(packet)
            logger.info(f"Added point: {name} at ({lat}, {lon})")
        
        logger.info(f"Created CZML with {len(czml) - 1} points")
        return czml
    
    def create_3d_config(
        self,
        data: List[Dict[str, Any]],
        layer_name: str = "3D Points"
    ) -> Dict[str, Any]:
        """
        Create complete 3D visualization configuration.
        """
        if not data:
            logger.warning("No data provided for 3D visualization")
            return {
                "layer_name": layer_name,
                "czml": [],
                "geojson": {"type": "FeatureCollection", "features": []},
                "bounds": None,
                "feature_count": 0
            }
        
        logger.info(f"Creating 3D config for {len(data)} records")
        logger.info(f"Sample record keys: {list(data[0].keys()) if data else 'N/A'}")
        
        # Generate CZML
        czml = self.to_czml(data, document_name=layer_name)
        
        # Also generate GeoJSON as fallback
        geojson = self._to_geojson(data)
        
        # Calculate bounds from the data
        lats = []
        lons = []
        
        for row in data:
            lat = self._get_lat(row)
            lon = self._get_lon(row)
            if lat is not None and lon is not None:
                lats.append(lat)
                lons.append(lon)
        
        bounds = None
        if lats and lons:
            # Add padding to bounds
            lat_padding = max(0.5, (max(lats) - min(lats)) * 0.2)
            lon_padding = max(0.5, (max(lons) - min(lons)) * 0.2)
            
            bounds = {
                "west": min(lons) - lon_padding,
                "south": min(lats) - lat_padding,
                "east": max(lons) + lon_padding,
                "north": max(lats) + lat_padding,
                "min_lon": min(lons) - lon_padding,
                "min_lat": min(lats) - lat_padding,
                "max_lon": max(lons) + lon_padding,
                "max_lat": max(lats) + lat_padding,
                "center_lon": sum(lons) / len(lons),
                "center_lat": sum(lats) / len(lats)
            }
            logger.info(f"Bounds calculated: center=({bounds['center_lat']:.4f}, {bounds['center_lon']:.4f})")
        
        return {
            "layer_name": layer_name,
            "czml": czml,
            "geojson": geojson,
            "bounds": bounds,
            "feature_count": len(czml) - 1,  # Subtract document packet
            "data": data  # Include raw data as fallback
        }
    
    def _get_lat(self, row: Dict) -> Optional[float]:
        """Extract latitude from row."""
        for field in ['latitude', 'lat', 'y']:
            if field in row and row[field] is not None:
                try:
                    return float(row[field])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _get_lon(self, row: Dict) -> Optional[float]:
        """Extract longitude from row."""
        for field in ['longitude', 'lon', 'x']:
            if field in row and row[field] is not None:
                try:
                    return float(row[field])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _to_geojson(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert to GeoJSON as fallback."""
        features = []
        
        for i, row in enumerate(data):
            lat = self._get_lat(row)
            lon = self._get_lon(row)
            
            if lat is None or lon is None:
                continue
            
            # Build properties (exclude geometry fields)
            properties = {k: v for k, v in row.items() 
                         if k not in ['geom', 'geometry', 'latitude', 'longitude', 'lat', 'lon']
                         and v is not None}
            
            feature = {
                "type": "Feature",
                "id": i,
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": properties
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }


# Global instance
_visualizer_3d: Optional[Visualizer3D] = None


def get_visualizer_3d() -> Visualizer3D:
    """Get or create the global 3D visualizer."""
    global _visualizer_3d
    if _visualizer_3d is None:
        _visualizer_3d = Visualizer3D()
    return _visualizer_3d