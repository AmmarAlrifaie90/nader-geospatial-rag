"""
=============================================================================
GEOSPATIAL RAG - MAIN APPLICATION
=============================================================================
FastAPI backend for geospatial mining database RAG system
=============================================================================
"""

import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from config import settings
from router import get_router, ToolType
from tools import (
    get_sql_generator,
    get_visualizer_2d,
    get_visualizer_3d,
    get_analyzer,
    get_exporter,
    get_voice_io,
    get_orchestrator,
)
from llm import get_ollama_client
from database import get_postgis_client
from rag import get_rag_orchestrator, get_vector_store
from rag.indexer import get_indexer

# Configure logging FIRST (before using logger)
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ML Predictor (optional - won't fail if not installed)
try:
    from ml import get_mineral_predictor, get_prospectivity_predictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML module not available. Install xgboost, lightgbm, category_encoders")


# =============================================================================
# LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Geospatial RAG application...")
    
    # Check connections
    try:
        db = get_postgis_client()
        if db.health_check():
            logger.info("✓ PostGIS database connected")
        else:
            logger.warning("✗ PostGIS database not available")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
    
    try:
        ollama = get_ollama_client()
        if await ollama.health_check():
            logger.info("✓ Ollama LLM server connected")
        else:
            logger.warning("✗ Ollama LLM server not available")
    except Exception as e:
        logger.error(f"✗ LLM connection failed: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Geospatial RAG application...")


# =============================================================================
# APPLICATION
# =============================================================================

app = FastAPI(
    title="Geospatial RAG API",
    description="Natural language interface for PostGIS mining database",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODELS
# =============================================================================

class QueryRequest(BaseModel):
    """Natural language query request."""
    query: str = Field(..., description="Natural language query")
    include_visualization: bool = Field(default=False, description="Include visualization data")
    max_results: Optional[int] = Field(default=None, description="Maximum results to return (None = no limit, only use if user explicitly requests a number)")


class QueryResponse(BaseModel):
    """Query response with data and metadata."""
    success: bool
    tool_used: str
    data: Optional[List[Dict[str, Any]]] = None
    visualization: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    description: Optional[str] = None
    row_count: Optional[int] = None
    error: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Spatial analysis request."""
    query: str = Field(..., description="Analysis request in natural language")


class ExportRequest(BaseModel):
    """Export request."""
    query: str = Field(..., description="Query for data to export")
    format: str = Field(default="geojson", description="Export format: geojson or shapefile")
    filename: Optional[str] = Field(default=None, description="Custom filename")


class VoiceQueryRequest(BaseModel):
    """Voice query with base64 audio."""
    audio_base64: str = Field(..., description="Base64 encoded audio")
    audio_format: str = Field(default="webm", description="Audio format")


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "query": "/api/query",
            "rag_query": "/api/rag/query",
            "rag_index": "/api/rag/index",
            "rag_stats": "/api/rag/stats",
            "visualize_2d": "/api/visualize/2d",
            "visualize_3d": "/api/visualize/3d",
            "analyze": "/api/analyze",
            "export": "/api/export",
            "voice": "/api/voice/query",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Check health of all services."""
    db = get_postgis_client()
    ollama = get_ollama_client()
    
    db_healthy = db.health_check()
    llm_healthy = await ollama.health_check()
    
    return {
        "status": "healthy" if (db_healthy and llm_healthy) else "degraded",
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "llm": "healthy" if llm_healthy else "unhealthy"
        }
    }


# =============================================================================
# MAIN QUERY ENDPOINT (with routing)
# =============================================================================

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Main query endpoint with automatic routing.
    
    The router will classify the query and route to the appropriate tool.
    """
    try:
        # Route the query
        router = get_router()
        route_result = await router.route(request.query)
        
        tool = route_result["tool"]
        logger.info(f"Query routed to: {tool.value} (confidence: {route_result['confidence']:.2f})")
        
        # Handle based on tool type
        if tool == ToolType.SQL_QUERY:
            return await _handle_sql_query(request)
        
        elif tool == ToolType.VISUALIZE_2D:
            return await _handle_2d_visualization(request)
        
        elif tool == ToolType.VISUALIZE_3D:
            return await _handle_3d_visualization(request)
        
        elif tool == ToolType.ANALYZE:
            return await _handle_analysis(request)
        
        elif tool == ToolType.EXPORT:
            return await _handle_export_from_query(request)
        
        elif tool == ToolType.GENERAL:
            return await _handle_general(request)
        
        else:
            # Default to SQL query
            return await _handle_sql_query(request)
            
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_sql_query(request: QueryRequest) -> QueryResponse:
    """Handle SQL generation and execution."""
    sql_gen = get_sql_generator()
    result = await sql_gen.execute(request.query, request.max_results)
    
    visualization = None
    if request.include_visualization and result.get("success") and result.get("data"):
        viz = get_visualizer_2d()
        visualization = viz.prepare_visualization(
            result["data"],
            query_type=result.get("query_type")
        )
    
    return QueryResponse(
        success=result.get("success", False),
        tool_used="sql_query",
        data=result.get("data"),
        visualization=visualization,
        sql_query=result.get("sql_query"),
        description=result.get("description"),
        row_count=result.get("row_count"),
        error=result.get("error")
    )


async def _handle_2d_visualization(request: QueryRequest) -> QueryResponse:
    """Handle 2D map visualization."""
    # First get the data
    sql_gen = get_sql_generator()
    result = await sql_gen.execute(request.query, request.max_results)
    
    if not result.get("success") or not result.get("data"):
        return QueryResponse(
            success=False,
            tool_used="visualize_2d",
            error=result.get("error", "No data to visualize")
        )
    
    # Prepare visualization
    viz = get_visualizer_2d()
    visualization = viz.prepare_visualization(
        result["data"],
        query_type=result.get("query_type")
    )
    
    return QueryResponse(
        success=True,
        tool_used="visualize_2d",
        data=result["data"],
        visualization=visualization,
        sql_query=result.get("sql_query"),
        row_count=result.get("row_count")
    )


async def _handle_3d_visualization(request: QueryRequest) -> QueryResponse:
    """Handle 3D CesiumJS visualization."""
    # First get the data
    sql_gen = get_sql_generator()
    result = await sql_gen.execute(request.query, request.max_results)
    
    if not result.get("success") or not result.get("data"):
        return QueryResponse(
            success=False,
            tool_used="visualize_3d",
            error=result.get("error", "No data to visualize")
        )
    
    # Prepare 3D visualization
    viz = get_visualizer_3d()
    visualization = viz.create_3d_config(result["data"])
    
    return QueryResponse(
        success=True,
        tool_used="visualize_3d",
        data=result["data"],
        visualization=visualization,
        sql_query=result.get("sql_query"),
        row_count=result.get("row_count")
    )


async def _handle_analysis(request: QueryRequest) -> QueryResponse:
    """Handle spatial analysis."""
    analyzer = get_analyzer()
    result = await analyzer.analyze(request.query)
    
    # Flatten results for response
    data = []
    for name, res in result.get("results", {}).items():
        if "data" in res:
            data.extend(res["data"])
    
    return QueryResponse(
        success=result.get("success", False),
        tool_used="analyze",
        data=data[:request.max_results] if data else None,
        description=result.get("interpretation"),
        row_count=len(data) if data else 0
    )


async def _handle_export_from_query(request: QueryRequest) -> QueryResponse:
    """Handle export request from natural language."""
    # Determine format from query
    query_lower = request.query.lower()
    format = "geojson"
    if "shapefile" in query_lower or "shp" in query_lower:
        format = "shapefile"
    
    # Get data first
    sql_gen = get_sql_generator()
    result = await sql_gen.execute(request.query, request.max_results)
    
    if not result.get("success") or not result.get("data"):
        return QueryResponse(
            success=False,
            tool_used="export",
            error=result.get("error", "No data to export")
        )
    
    # Export
    exporter = get_exporter()
    export_result = exporter.export(result["data"], format)
    
    return QueryResponse(
        success=export_result.get("success", False),
        tool_used="export",
        description=f"Exported {export_result.get('record_count', 0)} records to {export_result.get('filename', 'file')}",
        row_count=export_result.get("record_count"),
        error=export_result.get("error")
    )


async def _handle_general(request: QueryRequest) -> QueryResponse:
    """Handle general conversation."""
    return QueryResponse(
        success=True,
        tool_used="general",
        description=(
            "I'm a geospatial assistant for the mining database. I can help you:\n\n"
            "• **Search data**: 'Find all gold deposits', 'Show boreholes in region X'\n"
            "• **Visualize on map**: 'Show gold sites on a map'\n"
            "• **3D visualization**: 'Show boreholes in 3D'\n"
            "• **Analyze**: 'Cluster analysis of mineral sites'\n"
            "• **Export**: 'Export copper sites to GeoJSON'\n\n"
            "What would you like to explore?"
        )
    )


# =============================================================================
# DIRECT TOOL ENDPOINTS
# =============================================================================

@app.post("/api/visualize/2d")
async def visualize_2d(request: QueryRequest):
    """Direct 2D visualization endpoint."""
    return await _handle_2d_visualization(request)


@app.post("/api/visualize/3d")
async def visualize_3d(request: QueryRequest):
    """Direct 3D visualization endpoint."""
    return await _handle_3d_visualization(request)


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    """Direct analysis endpoint."""
    analyzer = get_analyzer()
    result = await analyzer.analyze(request.query)
    return result


@app.post("/api/export")
async def export_data(request: ExportRequest):
    """Export query results to file."""
    # Get data
    sql_gen = get_sql_generator()
    result = await sql_gen.execute(request.query, None)  # No limit - return all data
    
    if not result.get("success") or not result.get("data"):
        raise HTTPException(status_code=400, detail=result.get("error", "No data"))
    
    # Export
    exporter = get_exporter()
    export_result = exporter.export(result["data"], request.format, request.filename)
    
    if not export_result.get("success"):
        raise HTTPException(status_code=500, detail=export_result.get("error"))
    
    return export_result


@app.get("/api/export/download/{filename}")
async def download_export(filename: str):
    """Download exported file."""
    exporter = get_exporter()
    filepath = os.path.join(exporter.export_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream"
    )


# =============================================================================
# VOICE ENDPOINTS
# =============================================================================

# Arabic Voice Processor (Whisper + Google Translate + TTS)
try:
    from voice import get_arabic_voice_processor, VOICE_AVAILABLE
    ARABIC_VOICE_AVAILABLE = VOICE_AVAILABLE
except ImportError:
    ARABIC_VOICE_AVAILABLE = False
    logger.warning("Arabic voice module not available")


class ArabicVoiceRequest(BaseModel):
    """Arabic voice query request."""
    audio_base64: str = Field(..., description="Base64 encoded audio (Arabic speech)")
    audio_format: str = Field(default="wav", description="Audio format (wav, webm, mp3)")
    voice: str = Field(default="ar-XA-Wavenet-B", description="TTS voice for response")
    return_audio: bool = Field(default=True, description="Include audio response")


@app.get("/api/voice/status")
async def voice_status():
    """Get voice services status."""
    result = {
        "legacy_voice": {
            "available": True,
            "description": "Google Cloud STT/TTS (English/Arabic)"
        },
        "arabic_voice": {
            "available": ARABIC_VOICE_AVAILABLE,
            "description": "Whisper Arabic -> English -> Agent -> Arabic TTS pipeline"
        }
    }
    
    if ARABIC_VOICE_AVAILABLE:
        processor = get_arabic_voice_processor()
        result["arabic_voice"]["details"] = processor.get_status()
    
    return result


@app.post("/api/voice/arabic")
async def arabic_voice_query(request: ArabicVoiceRequest):
    """
    Process Arabic voice query through the full pipeline:
    
    1. Arabic speech -> English text (Whisper)
    2. English text -> Geospatial Agent
    3. English response -> Arabic text (Google Translate)
    4. Arabic text -> Arabic audio (Google TTS)
    
    Returns both the agent result and Arabic audio response.
    """
    if not ARABIC_VOICE_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Arabic voice processing not available. Install: openai-whisper google-cloud-translate google-cloud-texttospeech"
        )
    
    import base64 as b64
    
    # Decode audio
    try:
        audio_data = b64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {e}")
    
    processor = get_arabic_voice_processor()
    orchestrator = get_orchestrator()
    
    # Define agent callback
    async def agent_callback(english_query: str):
        """Process English query through geospatial agent."""
        result = await orchestrator.process(english_query)
        return result
    
    # Run full pipeline
    result = await processor.full_voice_pipeline(
        audio_data=audio_data,
        agent_callback=agent_callback,
        audio_format=request.audio_format,
        voice_name=request.voice
    )
    
    return result


@app.post("/api/voice/arabic/transcribe")
async def arabic_transcribe(request: ArabicVoiceRequest):
    """
    Transcribe Arabic audio to English text only (no agent processing).
    
    Useful for:
    - Testing Whisper transcription
    - Getting text before sending to agent
    """
    if not ARABIC_VOICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Arabic voice processing not available")
    
    import base64 as b64
    
    try:
        audio_data = b64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {e}")
    
    processor = get_arabic_voice_processor()
    result = await processor.process_arabic_audio(audio_data, audio_format=request.audio_format)
    
    return result


@app.post("/api/voice/arabic/respond")
async def arabic_respond(
    english_text: str = Query(..., description="English text to convert to Arabic audio"),
    voice: str = Query(default="ar-XA-Wavenet-B", description="TTS voice")
):
    """
    Convert English text to Arabic audio response.
    
    Useful for:
    - Converting agent responses to Arabic speech
    - Testing translation and TTS
    """
    if not ARABIC_VOICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Arabic voice processing not available")
    
    processor = get_arabic_voice_processor()
    result = await processor.create_arabic_response(
        english_response=english_text,
        voice_name=voice,
        return_audio=True
    )
    
    return result


@app.post("/api/voice/query")
async def voice_query(request: VoiceQueryRequest):
    """Process voice query (legacy - English focused)."""
    import base64
    
    voice = get_voice_io()
    
    # Decode audio
    try:
        audio_data = base64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {e}")
    
    # Speech to text
    stt_result = await voice.process_voice_query(audio_data, request.audio_format)
    
    if not stt_result.get("success"):
        return stt_result
    
    # Process the query
    query_request = QueryRequest(query=stt_result["query_text"], include_visualization=True)
    query_result = await process_query(query_request)
    
    # Generate voice response
    response_text = query_result.description or f"Found {query_result.row_count} results."
    tts_result = await voice.speak_response(response_text)
    
    return {
        "transcription": stt_result,
        "query_result": query_result.dict(),
        "voice_response": tts_result
    }


@app.post("/api/voice/tts")
async def text_to_speech(text: str = Query(...), language: str = Query(default="auto")):
    """Convert text to speech."""
    voice = get_voice_io()
    
    if language == "auto":
        result = await voice.speak_response(text)
    else:
        result = await voice.text_to_speech(text, language)
    
    return result


# =============================================================================
# AGENT ENDPOINT (with Spatial Analysis)
# =============================================================================

class AgentRequest(BaseModel):
    """Agent request with spatial analysis support."""
    query: str = Field(..., description="Natural language query or analysis selection")
    max_results: Optional[int] = Field(default=500, description="Maximum results to return")
    data: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional data to use for analysis (current table data)")


class AnalysisOnDataRequest(BaseModel):
    """Request to run analysis on provided data."""
    analysis_key: str = Field(..., description="Analysis type (e.g., 'clustering', 'regional')")
    data: List[Dict[str, Any]] = Field(..., description="Data to analyze (from current table)")
    cluster_distance_km: Optional[float] = Field(default=None, description="Custom cluster distance in km")


class AgentResponse(BaseModel):
    """Agent response with analysis support."""
    success: bool
    response: str
    data: Optional[List[Dict[str, Any]]] = None
    visualization: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    row_count: Optional[int] = None
    query_type: Optional[str] = None
    analysis_available: Optional[bool] = None
    analysis_options: Optional[List[Dict[str, Any]]] = None
    is_analysis_result: Optional[bool] = None
    analysis_type: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/agent", response_model=AgentResponse)
async def agent_query(request: AgentRequest):
    """
    Main agent endpoint with automatic routing and spatial analysis.
    
    Features:
    - Routes queries to SQL generator
    - Suggests spatial analyses based on results
    - Executes analysis when user selects one (by number or keyword)
    - Generates visualization data for maps and charts
    - Can use provided data for analysis (from filtered table)
    
    Example flow:
    1. User: "show gold deposits in Makkah" → Returns data + analysis suggestions
    2. User: "1" or "clustering" → Runs cluster analysis on the results
    3. User: "do cluster analysis" (with filtered data) → Runs on current table data
    """
    try:
        orchestrator = get_orchestrator()
        
        # If data is provided and query is an analysis request, use the provided data
        if request.data and len(request.data) > 0:
            # Check if this is an analysis request
            from tools.spatial_analysis_agent import get_spatial_analysis_agent
            agent = get_spatial_analysis_agent()
            is_analysis, analysis_key = agent.is_analysis_request(request.query)
            
            if is_analysis and analysis_key:
                # Run analysis on provided data
                result = await orchestrator.run_analysis_on_data(analysis_key, request.data)
            else:
                # Regular query processing
                result = await orchestrator.process(request.query)
        else:
            # Regular query processing
            result = await orchestrator.process(request.query)
        
        return AgentResponse(
            success=result.get("success", False),
            response=result.get("response", ""),
            data=result.get("data"),
            visualization=result.get("visualization"),
            sql_query=result.get("sql_query"),
            row_count=result.get("row_count"),
            query_type=result.get("query_type"),
            analysis_available=result.get("analysis_available"),
            analysis_options=result.get("analysis_options"),
            is_analysis_result=result.get("is_analysis_result"),
            analysis_type=result.get("analysis_type"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        return AgentResponse(
            success=False,
            response=f"Error: {str(e)}",
            error=str(e)
        )


# =============================================================================
# ANALYSIS ON DATA ENDPOINT
# =============================================================================

@app.post("/api/analysis/run", response_model=AgentResponse)
async def run_analysis_on_data(request: AnalysisOnDataRequest):
    """
    Run analysis on provided data (from current filtered table).
    
    This allows running analysis on:
    - Filtered data from polygon selections
    - Current table data
    - Any provided dataset
    
    Example:
    - User filters polygons → gets 50 points
    - User clicks "Cluster Analysis" or types "do cluster analysis"
    - Frontend sends the 50 points to this endpoint
    - Analysis runs on those 50 points only
    """
    try:
        orchestrator = get_orchestrator()
        
        # Prepare custom parameters (e.g., cluster distance)
        custom_params = {}
        if request.cluster_distance_km is not None:
            custom_params["distance_km"] = float(request.cluster_distance_km)
            logger.info(f"Using custom cluster distance: {custom_params['distance_km']} km")
        else:
            logger.info(f"No custom cluster distance provided, using default (5 km)")
        
        # Run analysis on provided data with custom parameters
        result = await orchestrator.run_analysis_on_data(
            analysis_key=request.analysis_key,
            data=request.data,
            custom_params=custom_params if custom_params else None
        )
        
        return AgentResponse(
            success=result.get("success", False),
            response=result.get("response", ""),
            data=result.get("data"),
            visualization=result.get("visualization"),
            sql_query=None,
            row_count=len(request.data) if request.data else 0,
            query_type="point",  # Analysis is typically on points
            analysis_available=False,
            analysis_options=None,
            is_analysis_result=True,
            analysis_type=result.get("analysis_type"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Analysis on data failed: {e}")
        import traceback
        traceback.print_exc()
        return AgentResponse(
            success=False,
            response=f"Analysis error: {str(e)}",
            error=str(e)
        )


# =============================================================================
# DATABASE INFO ENDPOINTS
# =============================================================================

@app.get("/api/database/tables")
async def get_tables():
    """Get list of database tables."""
    db = get_postgis_client()
    tables = db.get_all_tables()
    
    result = []
    for table in tables:
        count = db.get_table_count(table)
        bounds = db.get_table_bounds(table)
        result.append({
            "name": table,
            "row_count": count,
            "bounds": bounds
        })
    
    return {"tables": result}


@app.get("/api/database/schema/{table_name}")
async def get_table_schema(table_name: str):
    """Get schema for a specific table."""
    db = get_postgis_client()
    schema = db.get_table_schema(table_name)
    return {"table": table_name, "columns": schema}


# =============================================================================
# RAG ENDPOINTS (Agentic RAG + LLM)
# =============================================================================

class RAGQueryRequest(BaseModel):
    """RAG query request."""
    query: str = Field(..., description="Natural language query")
    use_agentic: bool = Field(default=False, description="Use agentic iterative refinement")
    max_context_chunks: int = Field(default=5, description="Maximum context chunks to retrieve")


@app.post("/api/rag/query")
async def rag_query(request: RAGQueryRequest):
    """
    Process query using RAG (Retrieval-Augmented Generation).
    
    This implements true RAG:
    1. Retrieves relevant context from vector store
    2. Augments LLM prompt with retrieved context
    3. Generates response using augmented context
    """
    try:
        rag = get_rag_orchestrator()
        
        if request.use_agentic:
            result = await rag.agentic_process(request.query)
        else:
            result = await rag.process_query(
                request.query,
                max_context_chunks=request.max_context_chunks
            )
        
        return {
            "success": True,
            "query": result.get("query"),
            "response": result.get("response") or result.get("final_response"),
            "context_used": result.get("context_chunks_used") or len(result.get("iterations", [])),
            "context_summary": result.get("context_summary"),
            "iterations": result.get("iterations")
        }
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/index")
async def index_knowledge_base(background_tasks: BackgroundTasks):
    """
    Index knowledge base into vector store.
    
    This indexes:
    - Database schema
    - Query patterns
    - Data samples
    """
    try:
        indexer = get_indexer()
        
        # Run indexing in background
        background_tasks.add_task(indexer.index_all)
        
        return {
            "success": True,
            "message": "Indexing started in background. Check /api/rag/stats for progress."
        }
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/stats")
async def get_rag_stats():
    """Get statistics about the vector store."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_collection_stats()
        
        return {
            "success": True,
            "collections": stats,
            "total_documents": sum(
                c.get("document_count", 0) for c in stats.values()
                if isinstance(c, dict) and "document_count" in c
            )
        }
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/reset")
async def reset_vector_store():
    """Reset vector store (for re-indexing)."""
    try:
        vector_store = get_vector_store()
        vector_store.reset()
        
        return {
            "success": True,
            "message": "Vector store reset. Run /api/rag/index to re-index."
        }
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MACHINE LEARNING ENDPOINTS
# =============================================================================

class MLPredictRequest(BaseModel):
    """ML prediction request."""
    query: str = Field(..., description="Natural language query to get data for prediction")


class MLPredictResponse(BaseModel):
    """ML prediction response."""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    predictions_summary: Optional[Dict[str, Any]] = None
    visualization: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    error: Optional[str] = None


@app.get("/api/ml/status")
async def ml_status():
    """Check ML model status."""
    if not ML_AVAILABLE:
        return {
            "available": False,
            "message": "ML dependencies not installed. Run: pip install xgboost lightgbm catboost category_encoders joblib"
        }
    
    try:
        predictor = get_mineral_predictor()
        info = predictor.get_model_info()
        return {
            "available": True,
            "model_loaded": info["is_loaded"],
            "threshold": info["threshold"],
            "required_features": info["required_features"]
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


@app.post("/api/ml/predict", response_model=MLPredictResponse)
async def ml_predict(request: MLPredictRequest):
    """
    Run ML predictions on query results.
    
    1. Executes the natural language query to get mineral deposit data
    2. Runs the ensemble ML model to predict High Value vs Background
    3. Returns data with predictions and visualization
    """
    if not ML_AVAILABLE:
        return MLPredictResponse(
            success=False,
            error="ML module not available. Install required packages."
        )
    
    try:
        # Get the predictor
        predictor = get_mineral_predictor()
        
        if not predictor.is_loaded:
            return MLPredictResponse(
                success=False,
                error="ML models not loaded. Check if model files exist."
            )
        
        # Execute the query to get data
        sql_gen = get_sql_generator()
        query_result = await sql_gen.execute(request.query)
        
        if not query_result.get("success"):
            return MLPredictResponse(
                success=False,
                error=query_result.get("error", "Query failed"),
                sql_query=query_result.get("sql_query")
            )
        
        if not query_result.get("data"):
            return MLPredictResponse(
                success=False,
                error="No data returned from query",
                sql_query=query_result.get("sql_query")
            )
        
        # Add ML predictions
        result_with_predictions = predictor.predict_from_query_result(query_result)
        
        # Build visualization with prediction colors
        data = result_with_predictions.get("data", [])
        features = []
        
        for row in data:
            lat = row.get("latitude") or row.get("lat")
            lon = row.get("longitude") or row.get("lon") or row.get("lng")
            
            if lat and lon:
                # Color based on prediction
                is_high = row.get("ml_prediction") == "High Value"
                prob = row.get("ml_probability", 0)
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": {
                        **{k: v for k, v in row.items() if k not in ["geom", "geojson_geom"]},
                        "color": "#22c55e" if is_high else "#ef4444",  # Green for high, red for background
                        "radius": 8 + (prob * 10) if is_high else 6  # Larger for high value
                    }
                })
        
        visualization = {
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            },
            "layer_type": "point",
            "legend": [
                {"label": "High Value", "color": "#22c55e"},
                {"label": "Background", "color": "#ef4444"}
            ]
        }
        
        return MLPredictResponse(
            success=True,
            data=data,
            predictions_summary=result_with_predictions.get("ml_predictions"),
            visualization=visualization,
            sql_query=query_result.get("sql_query")
        )
        
    except Exception as e:
        logger.error(f"ML prediction failed: {e}")
        return MLPredictResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/ml/predict-data")
async def ml_predict_data(data: List[Dict[str, Any]]):
    """
    Run ML predictions on provided data directly.
    
    Expects a list of dicts with required features:
    - elevation, quad, reg_struct, host_rocks, country_ro, gitology, alteration, min_morpho
    """
    if not ML_AVAILABLE:
        raise HTTPException(status_code=503, detail="ML module not available")
    
    try:
        predictor = get_mineral_predictor()
        
        if not predictor.is_loaded:
            raise HTTPException(status_code=503, detail="ML models not loaded")
        
        results = predictor.predict(data)
        
        high_value_count = sum(1 for r in results if r.get("ml_prediction") == "High Value")
        
        return {
            "success": True,
            "predictions": results,
            "summary": {
                "total": len(results),
                "high_value": high_value_count,
                "background": len(results) - high_value_count
            }
        }
        
    except Exception as e:
        logger.error(f"ML prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROSPECTIVITY ML ENDPOINTS (Multi-Class: Low/Medium/High)
# =============================================================================

class ProspectivityPredictRequest(BaseModel):
    """Prospectivity prediction request."""
    longitude: float = Field(..., description="Longitude of the location")
    latitude: float = Field(..., description="Latitude of the location")
    elevation: Optional[float] = Field(0, description="Elevation in meters")
    # Mods features (user input)
    quad: Optional[str] = None
    reg_struct: Optional[str] = None
    host_rocks: Optional[str] = None
    country_ro: Optional[str] = None
    gitology: Optional[str] = None
    alteration: Optional[str] = None
    min_morpho: Optional[str] = None
    # Auto features (from database)
    litho_fmly: Optional[str] = None
    family_dv: Optional[str] = None
    family_sdv: Optional[str] = None
    main_litho: Optional[str] = None
    met_facies: Optional[str] = None
    distance_to_nearest_line_m: Optional[float] = None
    lines_within_5000m: Optional[int] = None
    distance_to_nearest_line_d: Optional[float] = None
    dikes_within_5000m: Optional[int] = None


@app.get("/api/prospectivity/status")
async def prospectivity_status():
    """Check prospectivity model status."""
    if not ML_AVAILABLE:
        return {
            "available": False,
            "message": "ML dependencies not installed"
        }
    
    try:
        predictor = get_prospectivity_predictor()
        info = predictor.get_model_info()
        return {
            "available": True,
            "model_loaded": info["is_loaded"],
            "model_type": info.get("model_type"),
            "num_features": info.get("num_features"),
            "classes": info.get("classes")
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/prospectivity/form-fields")
async def get_prospectivity_form_fields():
    """Get form field definitions for prospectivity prediction."""
    if not ML_AVAILABLE:
        raise HTTPException(status_code=503, detail="ML module not available")
    
    predictor = get_prospectivity_predictor()
    return predictor.get_feature_definitions()


@app.get("/api/prospectivity/geology-at-point")
async def get_geology_at_point(lng: float, lat: float):
    """
    Get geology information at a specific point.
    Returns polygon features if point is inside a geology polygon.
    """
    db = get_postgis_client()
    
    try:
        # Query to find geology polygon containing the point
        query = f"""
        SELECT 
            litho_fmly,
            family_dv,
            family_sdv,
            main_litho,
            met_facies
        FROM geology_master
        WHERE ST_Contains(
            geom, 
            ST_Transform(ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326), 3857)
        )
        LIMIT 1;
        """
        
        result = db.execute_query(query)
        
        if result and len(result) > 0:
            row = result[0]
            return {
                "success": True,
                "inside_polygon": True,
                "geology": {
                    "litho_fmly": row.get("litho_fmly"),
                    "family_dv": row.get("family_dv"),
                    "family_sdv": row.get("family_sdv"),
                    "main_litho": row.get("main_litho"),
                    "met_facies": row.get("met_facies")
                }
            }
        else:
            return {
                "success": True,
                "inside_polygon": False,
                "geology": None
            }
            
    except Exception as e:
        logger.error(f"Geology query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prospectivity/distances-at-point")
async def get_distances_at_point(lng: float, lat: float):
    """
    Get distance to nearest faults and dikes at a specific point.
    """
    db = get_postgis_client()
    
    try:
        # Convert point to EPSG:3857 for distance calculation
        point_3857 = f"ST_Transform(ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326), 3857)"
        
        # Distance to nearest fault
        fault_query = f"""
        SELECT 
            MIN(ST_Distance({point_3857}, geom)) AS distance_to_nearest_line_m,
            COUNT(*) FILTER (WHERE ST_DWithin({point_3857}, geom, 5000)) AS lines_within_5000m
        FROM geology_faults_contacts_master
        WHERE ST_DWithin({point_3857}, geom, 50000);
        """
        
        fault_result = db.execute_query(fault_query)
        
        fault_dist = 50000  # Default max
        faults_nearby = 0
        if fault_result and len(fault_result) > 0:
            fault_dist = fault_result[0].get("distance_to_nearest_line_m") or 50000
            faults_nearby = fault_result[0].get("lines_within_5000m") or 0
        
        # Distance to nearest dike
        dike_dist = 50000
        dikes_nearby = 0
        try:
            dike_query = f"""
            SELECT 
                MIN(ST_Distance({point_3857}, geom)) AS distance_to_nearest_line_d,
                COUNT(*) FILTER (WHERE ST_DWithin({point_3857}, geom, 5000)) AS dikes_within_5000m
            FROM geology_dikes_master
            WHERE ST_DWithin({point_3857}, geom, 50000);
            """
            
            dike_result = db.execute_query(dike_query)
            if dike_result and len(dike_result) > 0:
                dike_dist = dike_result[0].get("distance_to_nearest_line_d") or 50000
                dikes_nearby = dike_result[0].get("dikes_within_5000m") or 0
        except:
            pass  # Dikes table may not exist
        
        return {
            "success": True,
            "distances": {
                "distance_to_nearest_line_m": round(fault_dist, 2),
                "lines_within_5000m": int(faults_nearby),
                "distance_to_nearest_line_d": round(dike_dist, 2),
                "dikes_within_5000m": int(dikes_nearby)
            }
        }
        
    except Exception as e:
        logger.error(f"Distance query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prospectivity/geology-polygons")
async def get_geology_polygons_simplified():
    """
    Get simplified geology polygon boundaries for map display.
    Returns GeoJSON with simplified geometries for performance.
    """
    db = get_postgis_client()
    
    try:
        # Get simplified polygons for display (tolerance ~500m at equator)
        query = """
        SELECT 
            gid,
            litho_fmly,
            ST_AsGeoJSON(
                ST_Transform(
                    ST_Simplify(geom, 500),
                    4326
                )
            ) AS geojson_geom
        FROM geology_master
        LIMIT 5000;
        """
        
        result = db.execute_query(query)
        
        features = []
        for row in result:
            if row.get("geojson_geom"):
                import json
                geom = json.loads(row["geojson_geom"])
                features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "gid": row.get("gid"),
                        "litho_fmly": row.get("litho_fmly"),
                        "valid": True  # Mark as valid selection zone
                    }
                })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        logger.error(f"Geology polygons query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prospectivity/predict")
async def prospectivity_predict(request: ProspectivityPredictRequest):
    """
    Run prospectivity prediction for a location.
    
    If geology/distance features are not provided, they will be fetched from the database.
    """
    if not ML_AVAILABLE:
        raise HTTPException(status_code=503, detail="ML module not available")
    
    try:
        predictor = get_prospectivity_predictor()
        
        if not predictor.is_loaded:
            raise HTTPException(
                status_code=503, 
                detail="Prospectivity model not loaded. Run: python ml/train_prospectivity.py"
            )
        
        # Convert request to dict
        input_data = request.model_dump()
        
        # If geology features not provided, fetch from database
        if not input_data.get("litho_fmly"):
            geology_response = await get_geology_at_point(request.longitude, request.latitude)
            if geology_response.get("inside_polygon") and geology_response.get("geology"):
                for key, value in geology_response["geology"].items():
                    if value:
                        input_data[key] = value
        
        # If distance features not provided, fetch from database
        if input_data.get("distance_to_nearest_line_m") is None:
            dist_response = await get_distances_at_point(request.longitude, request.latitude)
            if dist_response.get("success") and dist_response.get("distances"):
                for key, value in dist_response["distances"].items():
                    input_data[key] = value
        
        # Run prediction
        result = predictor.predict(input_data)
        
        if result.get("success"):
            # Add color for visualization
            prediction = result.get("prediction")
            colors = {"Low": "#ef4444", "Medium": "#f59e0b", "High": "#22c55e"}
            result["color"] = colors.get(prediction, "#6b7280")
        
        return result
        
    except Exception as e:
        logger.error(f"Prospectivity prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"ML prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
