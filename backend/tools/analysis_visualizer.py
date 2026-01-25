"""
=============================================================================
ANALYSIS VISUALIZER
=============================================================================
Generates visualization data for spatial analysis results:
1. GeoJSON with color-coded features for Mapbox
2. Chart.js compatible data structures
3. Legend information
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
import json
import colorsys

logger = logging.getLogger(__name__)


# =============================================================================
# COLOR PALETTES
# =============================================================================

# Categorical colors (for clusters, regions, commodities) - bright, visible colors
CATEGORICAL_COLORS = [
    "#e41a1c",  # Red
    "#377eb8",  # Blue
    "#4daf4a",  # Green
    "#984ea3",  # Purple
    "#ff7f00",  # Orange
    "#f781bf",  # Pink
    "#00d4aa",  # Cyan/Teal
    "#ffdd00",  # Yellow
    "#a65628",  # Brown
    "#66c2a5",  # Mint
    "#fc8d62",  # Coral
    "#8da0cb",  # Lavender
]

# Color for unclustered/isolated points (bright, visible on dark maps)
UNCLUSTERED_COLOR = "#ffffff"  # White - stands out on dark maps

# Sequential colors (for density, distance)
SEQUENTIAL_COLORS = [
    "#ffffcc",  # Light yellow
    "#c7e9b4",
    "#7fcdbb",
    "#41b6c4",
    "#2c7fb8",
    "#253494",  # Dark blue
]

# Diverging colors (for comparison)
DIVERGING_COLORS = [
    "#d73027",  # Red
    "#fc8d59",
    "#fee08b",
    "#d9ef8b",
    "#91cf60",
    "#1a9850",  # Green
]


def get_color(index: int, palette: List[str] = None) -> str:
    """Get a color from the palette, cycling if needed."""
    palette = palette or CATEGORICAL_COLORS
    return palette[index % len(palette)]


def generate_gradient_colors(n: int, start_color: str = "#ffffcc", end_color: str = "#253494") -> List[str]:
    """Generate n colors in a gradient."""
    if n <= 1:
        return [start_color]
    
    # Simple linear interpolation in RGB space
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(*rgb)
    
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)
    
    colors = []
    for i in range(n):
        t = i / (n - 1)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)
        colors.append(rgb_to_hex((r, g, b)))
    
    return colors


class AnalysisVisualizer:
    """
    Generates visualization data for analysis results.
    """
    
    def __init__(self):
        pass
    
    # =========================================================================
    # MAIN VISUALIZATION GENERATOR
    # =========================================================================
    
    def generate_visualization(
        self,
        analysis_type: str,
        analysis_results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate visualization data based on analysis type.
        
        Returns:
            {
                "geojson": GeoJSON FeatureCollection with styled features,
                "chart_data": Chart.js compatible data,
                "legend": Legend items,
                "layer_style": Mapbox layer style hints
            }
        """
        if analysis_type == "clustering":
            return self._viz_clustering(analysis_results, data)
        elif analysis_type == "regional":
            return self._viz_regional(analysis_results, data)
        elif analysis_type == "commodity":
            return self._viz_commodity(analysis_results, data)
        elif analysis_type == "distance_to_faults":
            return self._viz_distance(analysis_results, data)
        elif analysis_type == "geology_correlation":
            return self._viz_geology(analysis_results, data)
        elif analysis_type == "litho_distribution":
            return self._viz_litho(analysis_results, data)
        else:
            # Default: just return points with default styling
            return self._viz_default(data)
    
    # =========================================================================
    # CLUSTERING VISUALIZATION
    # =========================================================================
    
    def _viz_clustering(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for clustering analysis."""
        
        # Assign colors to clusters
        cluster_colors = {}
        cluster_idx = 0
        
        features = []
        for point in data:
            cluster_id = point.get("cluster_id")
            
            if cluster_id is None:
                # Use bright white for unclustered points (visible on dark map)
                color = UNCLUSTERED_COLOR
                cluster_name = "Unclustered"
            else:
                if cluster_id not in cluster_colors:
                    cluster_colors[cluster_id] = get_color(cluster_idx)
                    cluster_idx += 1
                color = cluster_colors[cluster_id]
                cluster_name = f"Cluster {cluster_id}"
            
            lat = point.get("latitude")
            lon = point.get("longitude")
            
            if lat and lon:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": {
                        "gid": point.get("gid"),
                        "name": point.get("name", ""),
                        "cluster_id": cluster_id,
                        "cluster_name": cluster_name,
                        "color": color,
                        "commodity": point.get("commodity", ""),
                        "region": point.get("region", "")
                    }
                })
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Chart data - cluster sizes (use same colors as map)
        cluster_details = results.get("results", {}).get("cluster_details", [])
        isolated_count = results.get("results", {}).get("isolated_points", 0)
        
        chart_labels = [f"Cluster {c['cluster_id']}" for c in cluster_details]
        chart_values = [c["point_count"] for c in cluster_details]
        chart_colors = [cluster_colors.get(c["cluster_id"], CATEGORICAL_COLORS[0]) for c in cluster_details]
        
        # Add unclustered if there are any
        if isolated_count > 0:
            chart_labels.append("Unclustered")
            chart_values.append(isolated_count)
            chart_colors.append(UNCLUSTERED_COLOR)
        
        chart_data = {
            "type": "doughnut",
            "data": {
                "labels": chart_labels,
                "datasets": [{
                    "data": chart_values,
                    "backgroundColor": chart_colors
                }]
            }
        }
        
        # Legend (same colors as map points)
        legend = [
            {"label": f"Cluster {cid}", "color": color}
            for cid, color in sorted(cluster_colors.items())
        ]
        if isolated_count > 0:
            legend.append({"label": "Unclustered", "color": UNCLUSTERED_COLOR})
        
        return {
            "geojson": geojson,
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": {
                "type": "circle",
                "paint": {
                    "circle-color": ["get", "color"],
                    "circle-radius": 8,
                    "circle-stroke-color": "#000000",  # Black stroke for better visibility
                    "circle-stroke-width": 2
                }
            }
        }
    
    # =========================================================================
    # REGIONAL VISUALIZATION
    # =========================================================================
    
    def _viz_regional(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for regional distribution."""
        
        distribution = results.get("results", {}).get("distribution", [])
        
        # Assign colors to regions
        region_colors = {}
        for i, item in enumerate(distribution):
            region_colors[item["region"]] = get_color(i)
        
        # Chart data - bar chart
        chart_data = {
            "type": "bar",
            "data": {
                "labels": [d["region"] for d in distribution],
                "datasets": [{
                    "label": "Count",
                    "data": [d["count"] for d in distribution],
                    "backgroundColor": [region_colors.get(d["region"], "#808080") for d in distribution]
                }]
            },
            "options": {
                "indexAxis": "y",
                "plugins": {
                    "legend": {"display": False}
                }
            }
        }
        
        # Legend
        legend = [
            {"label": region, "color": color, "count": next((d["count"] for d in distribution if d["region"] == region), 0)}
            for region, color in region_colors.items()
        ]
        
        return {
            "geojson": None,  # Would need original points with region info
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": None
        }
    
    # =========================================================================
    # COMMODITY VISUALIZATION
    # =========================================================================
    
    def _viz_commodity(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for commodity breakdown."""
        
        distribution = results.get("results", {}).get("distribution", [])
        
        # Assign colors to commodities
        commodity_colors = {}
        for i, item in enumerate(distribution):
            commodity_colors[item["commodity"]] = get_color(i)
        
        # Chart data - pie chart
        chart_data = {
            "type": "pie",
            "data": {
                "labels": [d["commodity"] for d in distribution],
                "datasets": [{
                    "data": [d["count"] for d in distribution],
                    "backgroundColor": [commodity_colors.get(d["commodity"], "#808080") for d in distribution]
                }]
            }
        }
        
        # Legend
        legend = [
            {"label": commodity, "color": color}
            for commodity, color in commodity_colors.items()
        ]
        
        return {
            "geojson": None,
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": None
        }
    
    # =========================================================================
    # DISTANCE VISUALIZATION
    # =========================================================================
    
    def _viz_distance(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for distance analysis."""
        
        point_distances = results.get("results", {}).get("point_distances", [])
        
        if not point_distances:
            return self._viz_default(data)
        
        # Calculate color breaks
        distances = [float(p.get("distance_to_fault_km", 0)) for p in point_distances]
        min_dist = min(distances)
        max_dist = max(distances)
        
        # Generate gradient colors
        n_breaks = 6
        colors = generate_gradient_colors(n_breaks, "#1a9850", "#d73027")  # Green (close) to Red (far)
        
        def get_distance_color(dist):
            if max_dist == min_dist:
                return colors[0]
            normalized = (dist - min_dist) / (max_dist - min_dist)
            idx = min(int(normalized * (n_breaks - 1)), n_breaks - 1)
            return colors[idx]
        
        # Build GeoJSON
        features = []
        for point in point_distances:
            lat = point.get("latitude")
            lon = point.get("longitude")
            dist = float(point.get("distance_to_fault_km", 0))
            
            if lat and lon:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": {
                        "gid": point.get("gid"),
                        "name": point.get("name", ""),
                        "distance_km": dist,
                        "color": get_distance_color(dist)
                    }
                })
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Chart - histogram of distances
        chart_data = {
            "type": "bar",
            "data": {
                "labels": ["0-5km", "5-10km", "10-20km", "20-50km", "50+km"],
                "datasets": [{
                    "label": "Points",
                    "data": [
                        sum(1 for d in distances if d <= 5),
                        sum(1 for d in distances if 5 < d <= 10),
                        sum(1 for d in distances if 10 < d <= 20),
                        sum(1 for d in distances if 20 < d <= 50),
                        sum(1 for d in distances if d > 50),
                    ],
                    "backgroundColor": colors[:5] if len(colors) >= 5 else colors
                }]
            }
        }
        
        # Legend
        legend = [
            {"label": f"≤{int(min_dist + (max_dist-min_dist)*i/5)}km", "color": colors[i]}
            for i in range(min(5, len(colors)))
        ]
        
        return {
            "geojson": geojson,
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": {
                "type": "circle",
                "paint": {
                    "circle-color": ["get", "color"],
                    "circle-radius": 8,
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 1
                }
            }
        }
    
    # =========================================================================
    # GEOLOGY VISUALIZATION
    # =========================================================================
    
    def _viz_geology(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for geology correlation."""
        
        distribution = results.get("results", {}).get("distribution", [])
        
        # Assign colors to rock families
        rock_colors = {}
        for i, item in enumerate(distribution):
            rock_colors[item["rock_family"]] = get_color(i)
        
        # Chart data
        chart_data = {
            "type": "bar",
            "data": {
                "labels": [d["rock_family"] for d in distribution[:10]],
                "datasets": [{
                    "label": "Points",
                    "data": [d["point_count"] for d in distribution[:10]],
                    "backgroundColor": [rock_colors.get(d["rock_family"], "#808080") for d in distribution[:10]]
                }]
            },
            "options": {
                "indexAxis": "y"
            }
        }
        
        legend = [
            {"label": rock, "color": color}
            for rock, color in list(rock_colors.items())[:10]
        ]
        
        return {
            "geojson": None,
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": None
        }
    
    # =========================================================================
    # LITHOLOGY VISUALIZATION
    # =========================================================================
    
    def _viz_litho(
        self,
        results: Dict[str, Any],
        data: List[Dict]
    ) -> Dict[str, Any]:
        """Generate visualization for lithology distribution."""
        
        distribution = results.get("data", [])
        
        # Assign colors
        litho_colors = {}
        for i, item in enumerate(distribution):
            litho_colors[item["rock_family"]] = get_color(i)
        
        # Chart data - horizontal bar
        chart_data = {
            "type": "bar",
            "data": {
                "labels": [d["rock_family"] for d in distribution],
                "datasets": [{
                    "label": "Area (km²)",
                    "data": [float(d["total_area_km2"]) for d in distribution],
                    "backgroundColor": [litho_colors.get(d["rock_family"], "#808080") for d in distribution]
                }]
            },
            "options": {
                "indexAxis": "y"
            }
        }
        
        legend = [
            {"label": rock, "color": color}
            for rock, color in litho_colors.items()
        ]
        
        return {
            "geojson": None,
            "chart_data": chart_data,
            "legend": legend,
            "layer_style": None
        }
    
    # =========================================================================
    # DEFAULT VISUALIZATION
    # =========================================================================
    
    def _viz_default(self, data: List[Dict]) -> Dict[str, Any]:
        """Generate default visualization for data."""
        
        features = []
        for point in data:
            lat = point.get("latitude") or point.get("lat")
            lon = point.get("longitude") or point.get("lon") or point.get("lng")
            
            if lat and lon:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": {
                        "gid": point.get("gid"),
                        "name": point.get("eng_name", point.get("name", "")),
                        "color": "#22c55e"
                    }
                })
        
        return {
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            },
            "chart_data": None,
            "legend": [{"label": "Features", "color": "#22c55e"}],
            "layer_style": {
                "type": "circle",
                "paint": {
                    "circle-color": "#22c55e",
                    "circle-radius": 6,
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 1
                }
            }
        }


# =============================================================================
# SINGLETON
# =============================================================================

_visualizer: Optional[AnalysisVisualizer] = None


def get_analysis_visualizer() -> AnalysisVisualizer:
    """Get or create the global analysis visualizer."""
    global _visualizer
    if _visualizer is None:
        _visualizer = AnalysisVisualizer()
    return _visualizer
