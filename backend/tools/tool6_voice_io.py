"""
=============================================================================
GEOSPATIAL RAG - TOOL 6: VOICE I/O
=============================================================================
Speech-to-Text and Text-to-Speech using Google Cloud APIs
Supports both English and Arabic
=============================================================================
"""

import logging
import os
import base64
from typing import Dict, Any, Optional, Tuple
import io

from config import settings

logger = logging.getLogger(__name__)

# These will be imported conditionally
speech_client = None
texttospeech_client = None


def _init_google_clients():
    """Initialize Google Cloud clients."""
    global speech_client, texttospeech_client
    
    if settings.google_cloud_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_cloud_credentials
    
    try:
        from google.cloud import speech_v1 as speech
        from google.cloud import texttospeech_v1 as texttospeech
        
        speech_client = speech.SpeechClient()
        texttospeech_client = texttospeech.TextToSpeechClient()
        
        logger.info("Google Cloud clients initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Google Cloud clients: {e}")
        return False


class VoiceIO:
    """Handles Speech-to-Text and Text-to-Speech operations."""
    
    def __init__(self):
        self.initialized = _init_google_clients()
        
        # Language configurations
        self.languages = {
            "en": {
                "stt_code": "en-US",
                "tts_code": "en-US",
                "tts_voice": settings.tts_voice_name,
                "name": "English"
            },
            "ar": {
                "stt_code": "ar-SA",
                "tts_code": "ar-XA",
                "tts_voice": settings.tts_arabic_voice_name,
                "name": "Arabic"
            }
        }
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        audio_format: str = "webm",
        language: str = "auto"
    ) -> Dict[str, Any]:
        """
        Convert speech audio to text.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (webm, wav, mp3, ogg)
            language: Language code (en, ar, auto for detection)
            
        Returns:
            Transcription result with text and detected language
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Google Cloud Speech client not initialized. Check credentials."
            }
        
        try:
            from google.cloud import speech_v1 as speech
            
            # Determine encoding
            encoding_map = {
                "webm": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                "wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "mp3": speech.RecognitionConfig.AudioEncoding.MP3,
                "ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                "flac": speech.RecognitionConfig.AudioEncoding.FLAC,
            }
            
            encoding = encoding_map.get(audio_format.lower(), speech.RecognitionConfig.AudioEncoding.WEBM_OPUS)
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=48000 if audio_format == "webm" else 16000,
                language_code="en-US",  # Primary language
                alternative_language_codes=["ar-SA"],  # Also detect Arabic
                enable_automatic_punctuation=True,
                model="latest_long",
            )
            
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Perform recognition
            response = speech_client.recognize(config=config, audio=audio)
            
            if not response.results:
                return {
                    "success": True,
                    "text": "",
                    "confidence": 0,
                    "language": "unknown",
                    "message": "No speech detected"
                }
            
            # Get best result
            result = response.results[0]
            alternative = result.alternatives[0]
            
            # Detect language from result
            detected_language = "en"
            if hasattr(result, 'language_code'):
                if "ar" in result.language_code.lower():
                    detected_language = "ar"
            
            return {
                "success": True,
                "text": alternative.transcript,
                "confidence": alternative.confidence,
                "language": detected_language,
                "language_name": self.languages[detected_language]["name"]
            }
            
        except Exception as e:
            logger.error(f"Speech-to-text failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def text_to_speech(
        self,
        text: str,
        language: str = "en",
        voice_gender: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert
            language: Language code (en, ar)
            voice_gender: "male", "female", or "neutral"
            
        Returns:
            Audio data as base64 and metadata
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Google Cloud TextToSpeech client not initialized. Check credentials."
            }
        
        try:
            from google.cloud import texttospeech_v1 as texttospeech
            
            # Get language config
            lang_config = self.languages.get(language, self.languages["en"])
            
            # Set up synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_config["tts_code"],
                name=lang_config["tts_voice"],
            )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
            )
            
            # Generate speech
            response = texttospeech_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Encode to base64
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            return {
                "success": True,
                "audio_base64": audio_base64,
                "audio_format": "mp3",
                "language": language,
                "language_name": lang_config["name"],
                "text_length": len(text),
                "audio_size_bytes": len(response.audio_content)
            }
            
        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection based on character sets.
        
        Returns:
            Language code (en, ar)
        """
        # Check for Arabic characters
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        
        if arabic_chars > len(text) * 0.3:  # More than 30% Arabic
            return "ar"
        return "en"
    
    async def process_voice_query(
        self,
        audio_data: bytes,
        audio_format: str = "webm"
    ) -> Dict[str, Any]:
        """
        Complete voice query processing pipeline.
        
        1. Convert speech to text
        2. Detect language
        3. Return transcription ready for query processing
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format
            
        Returns:
            Processed query with text and metadata
        """
        # Speech to text
        stt_result = await self.speech_to_text(audio_data, audio_format)
        
        if not stt_result["success"]:
            return stt_result
        
        text = stt_result["text"]
        
        if not text.strip():
            return {
                "success": False,
                "error": "No speech detected in audio"
            }
        
        return {
            "success": True,
            "query_text": text,
            "detected_language": stt_result["language"],
            "confidence": stt_result["confidence"],
            "ready_for_processing": True
        }
    
    async def speak_response(
        self,
        text: str,
        auto_detect_language: bool = True
    ) -> Dict[str, Any]:
        """
        Convert response text to speech with auto language detection.
        
        Args:
            text: Response text to speak
            auto_detect_language: Whether to auto-detect language
            
        Returns:
            Audio data and metadata
        """
        language = "en"
        if auto_detect_language:
            language = self.detect_language(text)
        
        return await self.text_to_speech(text, language)
    
    def get_supported_languages(self) -> Dict[str, Any]:
        """Get information about supported languages."""
        return {
            "supported_languages": [
                {"code": "en", "name": "English", "stt": True, "tts": True},
                {"code": "ar", "name": "Arabic", "stt": True, "tts": True}
            ],
            "default_language": "en",
            "auto_detection": True
        }


# Global instance
_voice_io: Optional[VoiceIO] = None


def get_voice_io() -> VoiceIO:
    """Get or create the global voice I/O handler."""
    global _voice_io
    if _voice_io is None:
        _voice_io = VoiceIO()
    return _voice_io
