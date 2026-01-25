"""
=============================================================================
GEOSPATIAL RAG - ARABIC VOICE PROCESSOR
=============================================================================
Pipeline:
  Arabic audio -> Whisper (task=translate) -> English text
  -> Geospatial Agent (English) -> English output
  -> Google Translate (EN->AR) -> Arabic text
  -> Google TTS (AR) -> MP3 audio (base64)

This module integrates Arabic voice interaction with the geospatial RAG system.
=============================================================================
"""

import base64
import os
import tempfile
import logging
from typing import Dict, Any, List, Optional

from config import settings

logger = logging.getLogger(__name__)

# Check if dependencies are available
VOICE_AVAILABLE = False
whisper_model = None
translate_client = None
tts_client = None
gcp_credentials = None

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("WARNING: Whisper not installed. Run: pip install openai-whisper")

try:
    from google.oauth2 import service_account
    from google.cloud import translate_v3
    from google.cloud import texttospeech
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google Cloud libraries not installed. Run: pip install google-cloud-translate google-cloud-texttospeech")


def _build_gcp_credentials():
    """
    Builds Google credentials from a service account JSON key file.
    Supports:
      - GOOGLE_APPLICATION_CREDENTIALS
      - GOOGLE_SERVICE_ACCOUNT_JSON (fallback)
      - settings.google_cloud_credentials
    """
    key_path = (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or 
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or
        getattr(settings, 'google_cloud_credentials', None) or
        ""
    ).strip()

    if not key_path:
        logger.warning("No GCP credentials path set. Voice features will be limited.")
        return None

    if not os.path.isfile(key_path):
        logger.warning(f"GCP JSON key file not found: {key_path}")
        return None

    try:
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        return service_account.Credentials.from_service_account_file(
            key_path,
            scopes=scopes,
        )
    except Exception as e:
        logger.error(f"Failed to load GCP credentials: {e}")
        return None


def _initialize_voice_services():
    """Initialize Whisper and Google Cloud services."""
    global whisper_model, translate_client, tts_client, gcp_credentials, VOICE_AVAILABLE
    
    # Initialize Whisper
    if WHISPER_AVAILABLE:
        try:
            # For better Arabic accuracy, use "medium" or "large-v3"
            # "small" is fast but less accurate for Arabic
            model_name = os.getenv("WHISPER_MODEL", "small")
            if model_name == "small":
                logger.warning("⚠️  Using 'small' Whisper model - Arabic accuracy will be poor!")
                logger.warning("⚠️  For better results, set: WHISPER_MODEL=medium (or large-v3)")
            logger.info(f"Loading Whisper model: {model_name}")
            whisper_model = whisper.load_model(model_name)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            whisper_model = None
    
    # Initialize Google services
    if GOOGLE_AVAILABLE:
        gcp_credentials = _build_gcp_credentials()
        
        if gcp_credentials:
            try:
                translate_client = translate_v3.TranslationServiceClient(credentials=gcp_credentials)
                tts_client = texttospeech.TextToSpeechClient(credentials=gcp_credentials)
                logger.info("Google Cloud clients initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google clients: {e}")
    
    # Determine overall availability
    VOICE_AVAILABLE = whisper_model is not None
    
    return VOICE_AVAILABLE


# Initialize on module load
_initialize_voice_services()


class ArabicVoiceProcessor:
    """
    Handles Arabic voice input/output with:
    - Whisper for Arabic speech to English text translation
    - Google Translate for English to Arabic translation
    - Google TTS for Arabic speech synthesis
    """
    
    def __init__(self):
        self.whisper_model = whisper_model
        self.translate_client = translate_client
        self.tts_client = tts_client
        self.gcp_project_id = (
            os.getenv("GCP_PROJECT_ID") or 
            os.getenv("GOOGLE_CLOUD_PROJECT") or
            getattr(settings, 'gcp_project_id', None) or
            ""
        ).strip()
        
        # Voice configuration
        self.default_voice = os.getenv("ARABIC_TTS_VOICE", "ar-XA-Wavenet-B")
        self.whisper_model_name = os.getenv("WHISPER_MODEL", "small")
    
    def is_available(self) -> Dict[str, bool]:
        """Check which voice services are available."""
        return {
            "whisper_stt": self.whisper_model is not None,
            "google_translate": self.translate_client is not None,
            "google_tts": self.tts_client is not None,
            "full_pipeline": all([
                self.whisper_model,
                self.translate_client,
                self.tts_client,
                self.gcp_project_id
            ])
        }
    
    # -------------------------------------------------------------------------
    # Text Processing Utilities
    # -------------------------------------------------------------------------
    
    def _normalize_for_speech_ar(self, text: str) -> str:
        """Trim/collapse whitespace + add final punctuation for better cadence."""
        t = " ".join((text or "").strip().split())
        if t and t[-1] not in ".؟!":
            t += "."
        return t
    
    def _chunk_for_tts(self, text: str, max_chars: int = 350) -> List[str]:
        """
        Chunk Arabic text for more stable TTS.
        Splits by punctuation; falls back to char slicing.
        """
        t = (text or "").strip()
        if not t:
            return []

        seps = ["。", ".", "؟", "!", "…", "،", "\n"]
        chunks: List[str] = []
        cur = ""

        for ch in t:
            cur += ch
            if ch in seps and len(cur) >= 40:
                chunks.append(cur.strip())
                cur = ""
            elif len(cur) >= max_chars:
                chunks.append(cur.strip())
                cur = ""

        if cur.strip():
            chunks.append(cur.strip())

        return [c for c in chunks if c]
    
    def _clean_for_tts(self, text: str) -> str:
        """
        Clean Arabic text for TTS by removing:
        - Emojis
        - Markdown formatting (**bold**, etc.)
        - Decorative lines (──────)
        - Analysis suggestions section
        - Special formatting characters
        - Multiple spaces/newlines
        """
        import re
        
        # Remove emojis (common Unicode ranges)
        # Arabic emojis and common symbols
        text = re.sub(r'[📊🔵💎🪨📐🎯📏✖️⭕🔲🔀📈🧭]', '', text)
        # Remove other common emojis
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)  # Emoji range
        text = re.sub(r'[\U00002700-\U000027BF]', '', text)  # Dingbats
        
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)     # *italic* -> italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # `code` -> code
        text = re.sub(r'#+\s*', '', text)                # Headers
        
        # Remove decorative lines (dashes, underscores, equals)
        text = re.sub(r'[─━═─_]{3,}', '', text)  # Lines of 3+ dashes/equals
        
        # Remove analysis suggestions section (everything after "تحليل مكاني متاح" or similar)
        # This section is interactive and shouldn't be read aloud
        analysis_patterns = [
            r'تحليل مكاني متاح.*$',  # "Spatial analysis available" and everything after
            r'────────────────.*$',   # Decorative line and everything after
            r'^\s*[٠١٢٣٤٥٦٧٨٩]\s*[\.\)]\s*.*$',  # Lines starting with Arabic numerals
        ]
        for pattern in analysis_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        # Remove Arabic numerals in circles/boxes at start of lines (like ١, ٢, ٣, ٤)
        text = re.sub(r'^[\s]*[٠١٢٣٤٥٦٧٨٩]\s*[\.\)]\s*', '', text, flags=re.MULTILINE)
        
        # Remove bullet points and list markers
        text = re.sub(r'^[\s]*[•·▪▫]\s*', '', text, flags=re.MULTILINE)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
        text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines -> single newline
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)  # Remove empty lines
        
        # Final cleanup - ensure natural flow
        text = text.strip()
        
        # Replace multiple periods/spaces with single period
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    # -------------------------------------------------------------------------
    # Core Pipeline Steps
    # -------------------------------------------------------------------------
    
    async def speech_to_english(self, audio_path: str) -> Dict[str, Any]:
        """
        Arabic speech -> English text using Whisper translate.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with english_text and metadata
        """
        if not self.whisper_model:
            return {
                "success": False,
                "error": "Whisper model not loaded. Install openai-whisper."
            }
        
        try:
            # Check file size
            file_size = os.path.getsize(audio_path)
            logger.info(f"Processing audio file: {audio_path} ({file_size} bytes)")
            
            if file_size < 1000:
                return {
                    "success": False,
                    "error": "Audio file too small. Please record for longer."
                }
            
            # Two-step approach: Transcribe Arabic first, then translate
            # This is more accurate than direct translation
            logger.info("Step 1: Transcribing Arabic audio to Arabic text...")
            
            # First, transcribe Arabic to Arabic text (more accurate)
            result = self.whisper_model.transcribe(
                audio_path,
                task="transcribe",  # Transcribe (not translate) - keeps original language
                language="ar",      # Force Arabic
                fp16=False,
                temperature=0.0,
                beam_size=5,
                best_of=3,
                condition_on_previous_text=True,
                initial_prompt="هذا كلام عربي عن مناجم الذهب والمعادن.",  # Arabic prompt to guide model
            )
            
            arabic_text = (result.get("text") or "").strip()
            detected_lang = result.get("language", "ar")
            
            logger.info(f"Whisper transcription - Language: {detected_lang}, Arabic text: {arabic_text[:200] if arabic_text else 'EMPTY'}")
            
            if not arabic_text:
                # Fallback: Try direct translation if transcription fails
                logger.info("Transcription empty, trying direct translation...")
                result = self.whisper_model.transcribe(
                    audio_path,
                    task="translate",
                    language="ar",
                    fp16=False,
                    temperature=0.0,
                    beam_size=5,
                )
                english_text = (result.get("text") or "").strip()
                logger.info(f"Direct translation result: {english_text[:200] if english_text else 'EMPTY'}")
            else:
                # Step 2: Translate Arabic text to English using Google Translate
                logger.info("Step 2: Translating Arabic text to English...")
                translate_result = await self.translate_to_english(arabic_text)
                
                if translate_result.get("success"):
                    english_text = translate_result.get("english_text", "")
                    logger.info(f"Translation result: {english_text[:200]}")
                else:
                    # Fallback to direct Whisper translation
                    logger.warning("Google Translate failed, using Whisper direct translation...")
                    result = self.whisper_model.transcribe(
                        audio_path,
                        task="translate",
                        language="ar",
                        fp16=False,
                        temperature=0.0,
                    )
                    english_text = (result.get("text") or "").strip()
            
            # Final check
            if not english_text:
                english_text = ""  # Will be handled below
            
            if not english_text:
                return {
                    "success": False,
                    "error": "No speech detected. Please speak clearly and ensure your microphone is working."
                }
            
            return {
                "success": True,
                "english_text": english_text,
                "language_detected": detected_lang,
                "model_used": self.whisper_model_name
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Speech recognition failed: {str(e)}"
            }
    
    async def translate_to_english(self, arabic_text: str) -> Dict[str, Any]:
        """
        Arabic -> English via Google Translate v3.
        
        Args:
            arabic_text: Text in Arabic
            
        Returns:
            Dict with english_text
        """
        if not self.translate_client:
            return {
                "success": False,
                "error": "Google Translate client not initialized"
            }
        
        if not self.gcp_project_id:
            return {
                "success": False,
                "error": "GCP_PROJECT_ID is required for Translation"
            }
        
        try:
            parent = f"projects/{self.gcp_project_id}/locations/global"
            
            response = self.translate_client.translate_text(
                request={
                    "parent": parent,
                    "contents": [arabic_text],
                    "mime_type": "text/plain",
                    "source_language_code": "ar",
                    "target_language_code": "en",
                }
            )
            
            if not response.translations:
                return {
                    "success": False,
                    "error": "Translation returned empty result"
                }
            
            english_text = (response.translations[0].translated_text or "").strip()
            
            return {
                "success": True,
                "english_text": english_text,
                "source_text": arabic_text
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "success": False,
                "error": f"Translation failed: {str(e)}"
            }
    
    async def translate_to_arabic(self, english_text: str) -> Dict[str, Any]:
        """
        English -> Arabic via Google Translate v3.
        
        Args:
            english_text: Text in English
            
        Returns:
            Dict with arabic_text
        """
        if not self.translate_client:
            return {
                "success": False,
                "error": "Google Translate client not initialized"
            }
        
        if not self.gcp_project_id:
            return {
                "success": False,
                "error": "GCP_PROJECT_ID is required for Translation"
            }
        
        try:
            parent = f"projects/{self.gcp_project_id}/locations/global"
            
            response = self.translate_client.translate_text(
                request={
                    "parent": parent,
                    "contents": [english_text],
                    "mime_type": "text/plain",
                    "source_language_code": "en",
                    "target_language_code": "ar",
                }
            )
            
            if not response.translations:
                return {
                    "success": False,
                    "error": "Translation returned empty result"
                }
            
            arabic_text = (response.translations[0].translated_text or "").strip()
            
            return {
                "success": True,
                "arabic_text": arabic_text,
                "source_text": english_text
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "success": False,
                "error": f"Translation failed: {str(e)}"
            }
    
    async def arabic_text_to_speech(
        self, 
        arabic_text: str, 
        voice_name: str = None
    ) -> Dict[str, Any]:
        """
        Arabic text -> MP3 audio via Google TTS.
        
        Args:
            arabic_text: Text in Arabic
            voice_name: TTS voice (default: ar-XA-Wavenet-B)
            
        Returns:
            Dict with audio_base64
        """
        if not self.tts_client:
            return {
                "success": False,
                "error": "Google TTS client not initialized"
            }
        
        voice_name = voice_name or self.default_voice
        
        try:
            # Clean text for TTS (remove emojis, markdown, etc.)
            arabic_text = self._clean_for_tts(arabic_text)
            
            # Normalize text for speech
            arabic_text = self._normalize_for_speech_ar(arabic_text)
            
            # Chunk for stable TTS
            chunks = self._chunk_for_tts(arabic_text, max_chars=300)
            
            if not chunks:
                return {
                    "success": False,
                    "error": "No text to synthesize"
                }
            
            # Generate audio for each chunk
            mp3_parts: List[bytes] = []
            
            for chunk in chunks:
                synthesis_input = texttospeech.SynthesisInput(text=chunk)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="ar-XA",
                    name=voice_name
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )
                
                response = self.tts_client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                )
                mp3_parts.append(response.audio_content)
            
            # Combine all parts
            audio_bytes = b"".join(mp3_parts)
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            
            return {
                "success": True,
                "audio_base64": audio_base64,
                "audio_format": "mp3",
                "voice_used": voice_name,
                "text_length": len(arabic_text),
                "chunks_count": len(chunks),
                "audio_size_bytes": len(audio_bytes)
            }
            
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return {
                "success": False,
                "error": f"Text-to-speech failed: {str(e)}"
            }
    
    # -------------------------------------------------------------------------
    # Main Processing Pipeline
    # -------------------------------------------------------------------------
    
    async def process_arabic_audio(
        self,
        audio_data: bytes,
        audio_format: str = "webm",
        voice_name: str = None,
        return_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Arabic audio -> English text (for agent processing).
        
        This is step 1 of the voice interaction:
        - Converts Arabic speech to English text
        - The English text can then be sent to the geospatial agent
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Format of the audio (webm, wav, mp3)
            voice_name: TTS voice for response
            return_audio: Whether to include audio response
            
        Returns:
            Dict with english_query ready for agent
        """
        # Determine correct file extension based on format
        format_to_ext = {
            "webm": ".webm",
            "wav": ".wav",
            "mp3": ".mp3",
            "ogg": ".ogg",
            "m4a": ".m4a"
        }
        suffix = format_to_ext.get(audio_format.lower(), ".webm")
        
        # Save audio to temp file with correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            tmp.write(audio_data)
        
        logger.info(f"Saved audio to {tmp_path} ({len(audio_data)} bytes, format: {audio_format})")
        
        try:
            # Step 1: Arabic speech -> English text
            stt_result = await self.speech_to_english(tmp_path)
            
            if not stt_result.get("success"):
                return stt_result
            
            english_query = stt_result["english_text"]
            
            return {
                "success": True,
                "english_query": english_query,
                "original_language": "ar",
                "ready_for_agent": True,
                "whisper_model": stt_result.get("model_used")
            }
            
        finally:
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    
    async def create_arabic_response(
        self,
        english_response: str,
        voice_name: str = None,
        return_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Convert agent's English response to Arabic audio.
        
        This is step 2 of the voice interaction:
        - Translates English response to Arabic
        - Generates Arabic speech audio
        
        Args:
            english_response: The agent's response in English
            voice_name: TTS voice
            return_audio: Whether to generate audio
            
        Returns:
            Dict with arabic_text and audio_base64
        """
        result = {
            "success": True,
            "english_response": english_response
        }
        
        # Step 1: Translate to Arabic
        translate_result = await self.translate_to_arabic(english_response)
        
        if not translate_result.get("success"):
            # Return English if translation fails
            result["arabic_text"] = english_response
            result["translation_failed"] = True
            result["translation_error"] = translate_result.get("error")
        else:
            result["arabic_text"] = translate_result["arabic_text"]
        
        # Step 2: Generate audio (if requested and TTS available)
        if return_audio and self.tts_client:
            arabic_text = result.get("arabic_text", english_response)
            tts_result = await self.arabic_text_to_speech(arabic_text, voice_name)
            
            if tts_result.get("success"):
                result["audio_base64"] = tts_result["audio_base64"]
                result["audio_format"] = tts_result["audio_format"]
                result["voice_used"] = tts_result["voice_used"]
            else:
                result["tts_failed"] = True
                result["tts_error"] = tts_result.get("error")
        
        return result
    
    async def full_voice_pipeline(
        self,
        audio_data: bytes,
        agent_callback,
        audio_format: str = "webm",
        voice_name: str = None
    ) -> Dict[str, Any]:
        """
        Complete voice interaction pipeline:
        
        1. Arabic audio -> English text (Whisper)
        2. English text -> Agent processing
        3. English response -> Arabic text (Google Translate)
        4. Arabic text -> Arabic audio (Google TTS)
        
        Args:
            audio_data: Raw audio bytes from user
            agent_callback: async function(english_query) -> english_response
            audio_format: Format of the input audio (webm, wav, mp3)
            voice_name: TTS voice for response
            
        Returns:
            Complete result with all intermediate steps
        """
        # Step 1: Process audio to get English query
        audio_result = await self.process_arabic_audio(audio_data, audio_format=audio_format)
        
        if not audio_result.get("success"):
            return audio_result
        
        english_query = audio_result["english_query"]
        
        # Step 2: Process with agent
        try:
            agent_response = await agent_callback(english_query)
            
            # Extract English response text from agent result
            if isinstance(agent_response, dict):
                english_response = (
                    agent_response.get("response") or 
                    agent_response.get("description") or 
                    str(agent_response)
                )
            else:
                english_response = str(agent_response)
                
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            english_response = f"Sorry, I encountered an error processing your request."
        
        # Step 3 & 4: Create Arabic audio response
        response_result = await self.create_arabic_response(
            english_response,
            voice_name=voice_name,
            return_audio=True
        )
        
        # Combine all results
        return {
            "success": True,
            "input": {
                "english_query": english_query,
                "whisper_model": audio_result.get("whisper_model")
            },
            "agent_result": agent_response if isinstance(agent_response, dict) else {"response": agent_response},
            "output": {
                "english_response": english_response,
                "arabic_text": response_result.get("arabic_text"),
                "audio_base64": response_result.get("audio_base64"),
                "audio_format": response_result.get("audio_format", "mp3"),
                "voice_used": response_result.get("voice_used")
            }
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of voice services."""
        availability = self.is_available()
        
        return {
            "available": availability["full_pipeline"],
            "services": {
                "whisper": {
                    "available": availability["whisper_stt"],
                    "model": self.whisper_model_name if availability["whisper_stt"] else None
                },
                "google_translate": {
                    "available": availability["google_translate"],
                    "project_id": self.gcp_project_id if availability["google_translate"] else None
                },
                "google_tts": {
                    "available": availability["google_tts"],
                    "default_voice": self.default_voice if availability["google_tts"] else None
                }
            },
            "pipeline": "Arabic Audio -> English Query -> Agent -> Arabic Audio" if availability["full_pipeline"] else "Limited"
        }


# Global instance
_arabic_voice_processor: Optional[ArabicVoiceProcessor] = None


def get_arabic_voice_processor() -> ArabicVoiceProcessor:
    """Get or create the global Arabic voice processor."""
    global _arabic_voice_processor
    if _arabic_voice_processor is None:
        _arabic_voice_processor = ArabicVoiceProcessor()
    return _arabic_voice_processor
