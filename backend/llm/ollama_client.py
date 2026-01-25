"""
=============================================================================
GEOSPATIAL RAG - OLLAMA CLIENT
=============================================================================
Handles communication with Ollama LLM server on Home PC
=============================================================================
"""

import httpx
import json
import re
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for communicating with Ollama LLM server."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        
        # Remove trailing slash if present
        self.base_url = self.base_url.rstrip("/")
        
        logger.info(f"Ollama client initialized: {self.base_url} using {self.model}")
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Creativity (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Generated text response
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("response", "")
                
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise TimeoutError(f"LLM request timed out after {self.timeout} seconds")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise ConnectionError(f"LLM server error: {e.response.status_code}")
            
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise ConnectionError(
                f"Cannot connect to LLM server at {self.base_url}. "
                "Make sure Ollama is running on your Home PC and Tailscale is connected."
            )
    
    async def chat(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> str:
        """
        Chat completion with message history.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            temperature: Creativity setting
            max_tokens: Maximum tokens to generate
            
        Returns:
            Assistant's response
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from the LLM.
        
        Args:
            prompt: The user prompt (should ask for JSON output)
            system: Optional system prompt
            temperature: Creativity (0.0 recommended for JSON)
            
        Returns:
            Parsed JSON dictionary
        """
        # Make JSON instruction very strict
        json_instruction = """
CRITICAL: You MUST respond with ONLY a valid JSON object. 
- NO text before the JSON
- NO text after the JSON
- NO markdown code blocks
- NO explanations
- Start with { and end with }
- Example format: {"key": "value"}
"""
        
        json_system = (system or "") + json_instruction
        
        # Enhance prompt to explicitly request JSON
        enhanced_prompt = f"{prompt}\n\nIMPORTANT: Respond with ONLY valid JSON, nothing else."
        
        response = await self.generate(
            prompt=enhanced_prompt,
            system=json_system,
            temperature=temperature,
            max_tokens=2048
        )
        
        # Clean up response more aggressively
        response = response.strip()
        
        # Remove markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif response.startswith("```"):
            response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
        
        # Try to extract JSON if there's text before/after
        # Look for first { and last }
        first_brace = response.find("{")
        last_brace = response.rfind("}")
        
        if first_brace >= 0 and last_brace > first_brace:
            response = response[first_brace:last_brace + 1]
        
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response. First 500 chars: {response[:500]}")
            logger.error(f"JSON Error: {e}")
            
            # Try to fix common issues
            # Remove trailing commas
            response = re.sub(r',\s*}', '}', response)
            response = re.sub(r',\s*]', ']', response)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Last resort: try to extract any JSON-like structure
                import re as regex_module
                json_match = regex_module.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
                
                raise ValueError(f"LLM did not return valid JSON. Response: {response[:200]}...")
    
    async def health_check(self) -> bool:
        """
        Check if Ollama server is reachable and model is loaded.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                
                # Check if our model is available
                model_base = self.model.split(":")[0]
                available = any(model_base in m for m in models)
                
                if not available:
                    logger.warning(
                        f"Model {self.model} not found. Available: {models}"
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global client instance
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create the global Ollama client."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
