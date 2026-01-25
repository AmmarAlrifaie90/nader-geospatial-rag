"""
=============================================================================
GEOSPATIAL RAG - TOOL 5: FILE EXPORTER
=============================================================================
Exports query results to GeoJSON and Shapefile formats
=============================================================================
"""

import logging
import os
import json
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime

import geopandas as gpd
from shapely.geometry import Point
import fiona

from config import settings
from database.postgis_client import get_postgis_client

logger = logging.getLogger(__name__)


class FileExporter:
    """Exports geospatial data to various file formats."""
    
    def __init__(self):
        self.db = get_postgis_client()
        self.export_dir = settings.export_directory
        self.max_records = settings.max_export_records
        
        # Ensure export directory exists
        os.makedirs(self.export_dir, exist_ok=True)
    
    def _data_to_geodataframe(
        self,
        data: List[Dict[str, Any]],
        lat_field: str = "latitude",
        lon_field: str = "longitude"
    ) -> gpd.GeoDataFrame:
        """Convert list of dicts to GeoDataFrame."""
        
        # Filter records with valid coordinates
        valid_data = []
        for row in data:
            lat = row.get(lat_field)
            lon = row.get(lon_field)
            if lat is not None and lon is not None:
                try:
                    row["geometry"] = Point(float(lon), float(lat))
                    valid_data.append(row)
                except (ValueError, TypeError):
                    continue
        
        if not valid_data:
            raise ValueError("No valid coordinates found in data")
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(valid_data, crs="EPSG:4326")
        
        # Remove lat/lon columns (now in geometry)
        for col in [lat_field, lon_field, "geom"]:
            if col in gdf.columns:
                gdf = gdf.drop(columns=[col])
        
        return gdf
    
    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate unique filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def export_to_geojson(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        lat_field: str = "latitude",
        lon_field: str = "longitude"
    ) -> Dict[str, Any]:
        """
        Export data to GeoJSON file.
        
        Args:
            data: List of records with coordinates
            filename: Optional custom filename
            lat_field: Name of latitude field
            lon_field: Name of longitude field
            
        Returns:
            Export result with file path
        """
        if len(data) > self.max_records:
            return {
                "success": False,
                "error": f"Too many records ({len(data)}). Maximum is {self.max_records}."
            }
        
        try:
            gdf = self._data_to_geodataframe(data, lat_field, lon_field)
            
            if filename is None:
                filename = self._generate_filename("export", "geojson")
            elif not filename.endswith(".geojson"):
                filename += ".geojson"
            
            filepath = os.path.join(self.export_dir, filename)
            
            # Export to GeoJSON
            gdf.to_file(filepath, driver="GeoJSON")
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            return {
                "success": True,
                "format": "GeoJSON",
                "filename": filename,
                "filepath": filepath,
                "record_count": len(gdf),
                "file_size_bytes": file_size,
                "file_size_human": self._human_readable_size(file_size),
                "crs": "EPSG:4326"
            }
            
        except Exception as e:
            logger.error(f"GeoJSON export failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_to_shapefile(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        lat_field: str = "latitude",
        lon_field: str = "longitude"
    ) -> Dict[str, Any]:
        """
        Export data to Shapefile (zipped).
        
        Args:
            data: List of records with coordinates
            filename: Optional custom filename (without extension)
            lat_field: Name of latitude field
            lon_field: Name of longitude field
            
        Returns:
            Export result with zip file path
        """
        if len(data) > self.max_records:
            return {
                "success": False,
                "error": f"Too many records ({len(data)}). Maximum is {self.max_records}."
            }
        
        try:
            gdf = self._data_to_geodataframe(data, lat_field, lon_field)
            
            # Shapefile has 10-char field name limit - truncate long names
            gdf.columns = [col[:10] if col != "geometry" else col for col in gdf.columns]
            
            if filename is None:
                filename = self._generate_filename("export", "shp")
            
            base_name = filename.replace(".shp", "").replace(".zip", "")
            
            # Create temporary directory for shapefile components
            with tempfile.TemporaryDirectory() as temp_dir:
                shp_path = os.path.join(temp_dir, f"{base_name}.shp")
                
                # Export shapefile
                gdf.to_file(shp_path, driver="ESRI Shapefile")
                
                # Create zip file with all shapefile components
                zip_filename = f"{base_name}.zip"
                zip_filepath = os.path.join(self.export_dir, zip_filename)
                
                # Remove existing zip if present
                if os.path.exists(zip_filepath):
                    os.remove(zip_filepath)
                
                # Create zip archive
                shutil.make_archive(
                    os.path.join(self.export_dir, base_name),
                    'zip',
                    temp_dir
                )
            
            file_size = os.path.getsize(zip_filepath)
            
            return {
                "success": True,
                "format": "Shapefile (zipped)",
                "filename": zip_filename,
                "filepath": zip_filepath,
                "record_count": len(gdf),
                "file_size_bytes": file_size,
                "file_size_human": self._human_readable_size(file_size),
                "crs": "EPSG:4326",
                "note": "Shapefile field names truncated to 10 characters"
            }
            
        except Exception as e:
            logger.error(f"Shapefile export failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def export(
        self,
        data: List[Dict[str, Any]],
        format: str = "geojson",
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export data to specified format.
        
        Args:
            data: Query result data
            format: "geojson" or "shapefile"
            filename: Optional custom filename
            
        Returns:
            Export result
        """
        format_lower = format.lower().strip()
        
        if format_lower in ["geojson", "json", "geo"]:
            return self.export_to_geojson(data, filename)
        elif format_lower in ["shapefile", "shp", "shape"]:
            return self.export_to_shapefile(data, filename)
        else:
            return {
                "success": False,
                "error": f"Unsupported format: {format}. Use 'geojson' or 'shapefile'."
            }
    
    def get_export_as_bytes(self, filepath: str) -> bytes:
        """Read exported file as bytes for download."""
        with open(filepath, "rb") as f:
            return f.read()
    
    def cleanup_old_exports(self, max_age_hours: int = 24):
        """Remove export files older than specified hours."""
        import time
        
        cutoff = time.time() - (max_age_hours * 3600)
        
        for filename in os.listdir(self.export_dir):
            filepath = os.path.join(self.export_dir, filename)
            if os.path.isfile(filepath):
                if os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
                    logger.info(f"Cleaned up old export: {filename}")
    
    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List all exported files."""
        exports = []
        for filename in os.listdir(self.export_dir):
            filepath = os.path.join(self.export_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                exports.append({
                    "filename": filename,
                    "filepath": filepath,
                    "size_bytes": stat.st_size,
                    "size_human": self._human_readable_size(stat.st_size),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return sorted(exports, key=lambda x: x["created"], reverse=True)


# Global instance
_exporter: Optional[FileExporter] = None


def get_exporter() -> FileExporter:
    """Get or create the global file exporter."""
    global _exporter
    if _exporter is None:
        _exporter = FileExporter()
    return _exporter
