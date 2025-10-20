"""
Clean, general-purpose Vision agent for pipe detection.
Uses pure prompt-based approach - trusts GPT-4o intelligence.
"""
import logging
from typing import Dict, Any
from app.vision.base_vision_agent import BaseVisionAgent

logger = logging.getLogger(__name__)


class PipesVisionAgent(BaseVisionAgent):
    """
    General-purpose Vision agent for detecting pipes in construction documents.
    """
    
    def __init__(self):
        super().__init__(
            domain="pipes",
            expertise="Pipe detection from construction blueprints"
        )
        
        self.system_prompt = """You are an expert at reading construction blueprint documents. 

You specialize in extracting the type of pipe, the depth of the pipe and the length of the pipe."""

        self.user_prompt_template = """Analyze this construction document.

Extract individual pipes only, not summary totals or aggregates. Do not extract lines that show totals or have missing diameter/material. Please calculate how many pipes of each type you detect. Then give their length and then give their depth.

ALSO: If there is a legend or abbreviations table on this page, extract it. This is critical for decoding material abbreviations like "FPVC", "SRPE", "DI", etc.

Return JSON:
{
  "pipes": [
    {
      "discipline": "storm" | "sanitary" | "water",
      "material": "pipe material",
      "diameter_in": number,
      "length_ft": number,
      "depth_ft": number or null
    }
  ],
  "legend": {
    "abbreviation": "full name",
    "example": "FPVC: Fabric Reinforced PVC Pipe"
  },
  "summary": "Brief description of what you found"
}"""

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        return self.user_prompt_template

