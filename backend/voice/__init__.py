"""
Voice processing module for Geospatial RAG.
Supports Arabic speech with Whisper -> LLM -> Google Translate -> TTS pipeline.
"""

from .arabic_voice_processor import (
    ArabicVoiceProcessor,
    get_arabic_voice_processor,
    VOICE_AVAILABLE
)

__all__ = [
    "ArabicVoiceProcessor",
    "get_arabic_voice_processor", 
    "VOICE_AVAILABLE"
]
