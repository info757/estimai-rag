"""
Base Vision Agent - foundation for specialized Vision agents.

Vision agents are STATELESS image processors with domain-specific expertise.
Each agent analyzes images independently without state management.
"""
import logging
import os
import json
import re
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)


class BaseVisionAgent:
    """
    Base class for specialized Vision agents.
    
    Vision agents are lightweight, focused image processors that:
    - Analyze ONE image at a time (stateless)
    - Have domain-specific prompts
    - Return raw findings without validation
    - Run independently in parallel
    
    This is different from RAG Researchers which:
    - Have state management (ResearcherState)
    - Access knowledge base for validation
    - Maintain context across multiple analyses
    """
    
    def __init__(self, domain: str, expertise: str):
        """
        Initialize Vision agent.
        
        Args:
            domain: Agent domain (e.g., "plan_pipes", "earthwork")
            expertise: Brief description of expertise
        """
        self.domain = domain
        self.expertise = expertise
        self.system_prompt = ""  # Must be set by subclass
        self.user_prompt_template = ""  # Must be set by subclass
        
        logger.info(f"[Vision:{domain}] Initialized - {expertise}")
    
    async def analyze(
        self,
        image_b64: str,
        api_key: str,
        model: str = "gpt-4o",
        max_tokens: int = 8000,
        temperature: float = 0,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Analyze image with domain-specific expertise.
        
        STATELESS: Each call is independent. No memory of previous calls.
        
        Args:
            image_b64: Base64-encoded PNG image
            api_key: OpenAI API key
            model: Vision model to use
            max_tokens: Maximum response tokens
            temperature: Model temperature
            timeout: Request timeout
        
        Returns:
            Dict with domain-specific findings
        """
        logger.info(f"[Vision:{self.domain}] Analyzing image...")
        
        # Make API request
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": self.user_prompt_template},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}",
                                        "detail": "high"  # High-detail mode for better accuracy
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            content = data["choices"][0]["message"]["content"]
            
            # Extract JSON from response
            result = self._parse_json_response(content)
            
            findings_count = len(result.get("findings", result.get("pipes", [])))
            logger.info(f"[Vision:{self.domain}] Analysis complete - {findings_count} items found")
            
            return result
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from Vision LLM response."""
        try:
            # Try to find JSON block
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning(f"[Vision:{self.domain}] No JSON found in response")
                return {"summary": content, "findings": []}
        except json.JSONDecodeError as e:
            logger.error(f"[Vision:{self.domain}] JSON parse error: {e}")
            return {"summary": content, "findings": [], "error": str(e)}

