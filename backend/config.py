"""
=============================================================================
GEOSPATIAL RAG - CONFIGURATION
=============================================================================
All settings are loaded from environment variables or .env file
=============================================================================
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ==========================================================================
    # APPLICATION
    # ==========================================================================
    app_name: str = "Geospatial RAG"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # ==========================================================================
    # OLLAMA (LLM Server on Home PC)
    # ==========================================================================
    ollama_base_url: str = Field(
        default="http://100.100.100.100:11434",
        description="Tailscale IP of your Home PC running Ollama"
    )
    ollama_model: str = Field(
        default="qwen2.5:7b",
        description="Model to use for SQL generation and routing"
    )
    ollama_timeout: int = Field(
        default=120,
        description="Timeout in seconds for LLM requests"
    )
    
    # ==========================================================================
    # POSTGIS DATABASE
    # ==========================================================================
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_database: str = Field(default="geoml")
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )
    
    # ==========================================================================
    # GOOGLE CLOUD (Voice)
    # ==========================================================================
    google_cloud_credentials: Optional[str] = Field(
        default=None,
        description="Path to Google Cloud service account JSON file"
    )
    google_cloud_project: Optional[str] = Field(
        default=None,
        description="Google Cloud project ID"
    )
    
    # Aliases for environment variable compatibility
    google_application_credentials: Optional[str] = Field(
        default=None,
        description="Alias for GOOGLE_APPLICATION_CREDENTIALS env var"
    )
    gcp_project_id: Optional[str] = Field(
        default=None,
        description="Alias for GCP_PROJECT_ID env var"
    )
    
    # STT Settings
    stt_language_code: str = Field(
        default="en-US",
        description="Primary language for speech recognition"
    )
    stt_alternative_languages: list = Field(
        default=["ar-SA"],
        description="Alternative languages to recognize"
    )
    
    # TTS Settings
    tts_language_code: str = Field(
        default="en-US",
        description="Language for text-to-speech"
    )
    tts_voice_name: str = Field(
        default="en-US-Neural2-J",
        description="Voice name for TTS"
    )
    tts_arabic_voice_name: str = Field(
        default="ar-XA-Wavenet-B",
        description="Arabic voice name for TTS"
    )
    
    # ==========================================================================
    # WHISPER (Arabic Speech Recognition)
    # ==========================================================================
    whisper_model: str = Field(
        default="small",
        description="Whisper model size: tiny, base, small, medium, large-v3"
    )
    
    # ==========================================================================
    # FILE EXPORT
    # ==========================================================================
    export_directory: str = Field(
        default="./exports",
        description="Directory for exported files"
    )
    max_export_records: int = Field(
        default=10000,
        description="Maximum records to export at once"
    )
    
    # ==========================================================================
    # CESIUM (3D Visualization)
    # ==========================================================================
    cesium_ion_token: Optional[str] = Field(
        default=None,
        description="Cesium Ion access token for terrain/imagery"
    )
    
    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:5500"],
        description="Allowed CORS origins"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
