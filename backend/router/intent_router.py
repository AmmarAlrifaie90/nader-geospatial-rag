"""
=============================================================================
GEOSPATIAL RAG - INTENT ROUTER
=============================================================================
LLM-based router that classifies user intent and routes to appropriate tool
=============================================================================
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from llm.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Available tools in the system."""
    SQL_QUERY = "sql_query"          # Tool 1: Generate and execute SQL
    VISUALIZE_2D = "visualize_2d"    # Tool 2: 2D map visualization
    VISUALIZE_3D = "visualize_3d"    # Tool 3: 3D CesiumJS visualization
    ANALYZE = "analyze"               # Tool 4: Spatial analysis
    EXPORT = "export"                 # Tool 5: Export to file
    VOICE = "voice"                   # Tool 6: Voice I/O (handled separately)
    GENERAL = "general"               # General conversation


ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a geospatial mining database system.

Your job is to classify user queries into one of these categories:

1. sql_query - User wants to find, search, count, or list data from the database
   Examples: "Find all gold deposits", "Show me boreholes in region X", "How many samples have copper?"

2. visualize_2d - User explicitly wants to see data on a 2D map
   Examples: "Show on map", "Plot the locations", "Display on a map", "Map these points"

3. visualize_3d - User explicitly wants 3D visualization
   Examples: "Show in 3D", "3D view", "Create 3D visualization", "Show terrain"

4. analyze - User wants spatial or statistical analysis
   Examples: "Cluster analysis", "Find patterns", "Statistics of", "Buffer analysis", "What's the correlation"

5. export - User wants to download/export data as a file
   Examples: "Export to GeoJSON", "Download as shapefile", "Save as file", "Export the results"

6. general - General questions, greetings, help requests
   Examples: "Hello", "What can you do?", "Help", "Explain this"

RULES:
- If a query involves finding data WITHOUT explicit visualization request, choose sql_query
- Only choose visualize_2d or visualize_3d if user EXPLICITLY mentions map/3D/visualization
- Analysis requires analytical keywords (statistics, patterns, clustering, correlation, buffer)
- Export requires download/export/save keywords with file format mentions

Respond with ONLY a JSON object:
{
    "tool": "tool_name",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "sub_intent": "optional specific intent"
}
"""


class IntentRouter:
    """Routes user queries to appropriate tools using LLM classification."""
    
    def __init__(self):
        self.ollama = get_ollama_client()
        self.default_tool = ToolType.SQL_QUERY
    
    async def classify(self, query: str) -> Dict[str, Any]:
        """
        Classify user query into a tool category.
        
        Args:
            query: User's natural language query
            
        Returns:
            Classification result with tool, confidence, and metadata
        """
        # Quick pattern matching for obvious cases (saves LLM call)
        quick_result = self._quick_classify(query)
        if quick_result:
            return quick_result
        
        # Use LLM for complex classification
        try:
            result = await self.ollama.generate_json(
                prompt=f"Classify this query: \"{query}\"",
                system=ROUTER_SYSTEM_PROMPT,
                temperature=0.0
            )
            
            # Validate tool name
            tool = result.get("tool", "sql_query")
            if tool not in [t.value for t in ToolType]:
                tool = "sql_query"
            
            return {
                "tool": ToolType(tool),
                "confidence": result.get("confidence", 0.8),
                "reason": result.get("reason", "LLM classification"),
                "sub_intent": result.get("sub_intent"),
                "original_query": query
            }
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fallback to SQL query
            return {
                "tool": ToolType.SQL_QUERY,
                "confidence": 0.5,
                "reason": f"Fallback due to error: {e}",
                "original_query": query
            }
    
    def _quick_classify(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Quick pattern-based classification for obvious cases.
        Returns None if LLM should be used.
        """
        query_lower = query.lower().strip()
        
        # Greetings and general
        greetings = ["hello", "hi", "hey", "help", "what can you do", "مرحبا", "السلام"]
        if any(query_lower.startswith(g) for g in greetings) or len(query_lower) < 10:
            return {
                "tool": ToolType.GENERAL,
                "confidence": 0.95,
                "reason": "Greeting or short query detected",
                "original_query": query
            }
        
        # Explicit 3D visualization
        if any(kw in query_lower for kw in ["3d", "three dimension", "cesium", "terrain view"]):
            return {
                "tool": ToolType.VISUALIZE_3D,
                "confidence": 0.9,
                "reason": "3D visualization keyword detected",
                "original_query": query
            }
        
        # Explicit 2D visualization
        map_keywords = ["show on map", "on a map", "plot on map", "display map", "map view"]
        if any(kw in query_lower for kw in map_keywords):
            return {
                "tool": ToolType.VISUALIZE_2D,
                "confidence": 0.9,
                "reason": "2D map keyword detected",
                "original_query": query
            }
        
        # Export keywords
        export_keywords = ["export", "download", "save as", "shapefile", "geojson file"]
        if any(kw in query_lower for kw in export_keywords):
            return {
                "tool": ToolType.EXPORT,
                "confidence": 0.9,
                "reason": "Export keyword detected",
                "original_query": query
            }
        
        # Analysis keywords
        analysis_keywords = [
            "analyze", "analysis", "cluster", "pattern", "statistics",
            "correlation", "buffer zone", "density", "distribution"
        ]
        if any(kw in query_lower for kw in analysis_keywords):
            return {
                "tool": ToolType.ANALYZE,
                "confidence": 0.85,
                "reason": "Analysis keyword detected",
                "original_query": query
            }
        
        # No quick match - use LLM
        return None
    
    async def route(self, query: str) -> Dict[str, Any]:
        """
        Classify and prepare routing information.
        
        Returns complete routing context for tool execution.
        """
        classification = await self.classify(query)
        
        return {
            **classification,
            "requires_llm": classification["tool"] in [
                ToolType.SQL_QUERY,
                ToolType.ANALYZE
            ],
            "requires_visualization": classification["tool"] in [
                ToolType.VISUALIZE_2D,
                ToolType.VISUALIZE_3D
            ],
            "requires_export": classification["tool"] == ToolType.EXPORT
        }


# Global router instance
_router: Optional[IntentRouter] = None


def get_router() -> IntentRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router
