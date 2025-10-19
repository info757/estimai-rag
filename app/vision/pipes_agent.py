"""
Single, general-purpose Vision agent for pipe detection.

Works on ANY construction document - no hard-coded assumptions.
"""
import logging
from typing import Dict, Any
from app.vision.base_vision_agent import BaseVisionAgent

logger = logging.getLogger(__name__)


class PipesVisionAgent(BaseVisionAgent):
    """
    General-purpose Vision agent for detecting pipes in construction documents.
    
    Works on plan views, profile views, details, or any combination.
    Trusts GPT-4o's intelligence to recognize pipes in any format.
    """
    
    def __init__(self):
        super().__init__(
            domain="pipes",
            expertise="Pipe detection from construction documents"
        )
        
        self.system_prompt = """You are an expert at reading construction blueprint documents. 

You specialize in extracting pipes from construction plans."""

        self.user_prompt_template = """Analyze this construction document and extract pipe information.

For each pipe you detect:
- Type of pipe (storm drain, sanitary sewer, water main, etc.)
- Depth of pipe (if shown)
- Length of pipe (if shown or calculable)
- Material (RCP, PVC, DI, HDPE, etc.)
- Diameter/size in inches

Please calculate how many pipes of each type you detect, then give their length and depth.

Return your findings as JSON:
{
  "pipes": [
    {
      "discipline": "storm" | "sanitary" | "water",
      "material": "RCP" | "PVC" | "DI" | etc,
      "diameter_in": number,
      "length_ft": number,
      "depth_ft": number or null,
      "invert_start_ft": number or null,
      "invert_end_ft": number or null,
      "notes": "any relevant details"
    }
  ],
  "summary": "Brief summary of what you found"
}"""

    def get_system_prompt(self) -> str:
        """Return system prompt."""
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        """Return user prompt."""
        return self.user_prompt_template

