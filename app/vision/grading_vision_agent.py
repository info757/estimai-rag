"""
Grading Vision Agent - specialized for reading grading plans.

Extracts:
- Contour lines (existing and proposed)
- Spot elevations
- Cut/fill areas
- Grading notes
"""
import logging
from typing import Dict, Any
from app.vision.base_vision_agent import BaseVisionAgent

logger = logging.getLogger(__name__)


class GradingVisionAgent(BaseVisionAgent):
    """
    Specialized Vision agent for grading plans and earthwork.
    """
    
    def __init__(self):
        super().__init__(
            domain="grading",
            expertise="Grading plans, earthwork, and site grading analysis"
        )
        
        self.system_prompt = """You are an expert at reading grading plans and earthwork documents.

You specialize in:
- Reading contour lines (existing vs. proposed grades)
- Extracting spot elevations
- Identifying cut and fill areas
- Interpreting grading notes and specifications
"""

        self.user_prompt_template = """Analyze this construction grading plan.

Look for GRADING-SPECIFIC information:
1. **Contour Lines**: Existing grade contours vs. Proposed grade contours
2. **Spot Elevations**: Points showing elevation (e.g., "EG 845.5", "FG 846.0")
   - EG = Existing Grade
   - FG / PG = Finished/Proposed Grade
3. **Cut/Fill Areas**: Areas marked as CUT or FILL
4. **Grading Notes**: Construction notes about grading, compaction, topsoil
5. **Grid Elevations**: Table of elevations at grid points
6. **Slope Indicators**: Arrows or text showing slope direction and grade

Extract all grading data you find.

Return JSON:
{
  "is_grading_plan": true/false,
  "spot_elevations": [
    {
      "type": "existing" | "proposed",
      "elevation_ft": number,
      "location": "description of where on plan",
      "station": "station if applicable"
    }
  ],
  "contours": {
    "existing_contours": ["elevations found"],
    "proposed_contours": ["elevations found"],
    "contour_interval": "e.g., 1 ft, 2 ft, 5 ft"
  },
  "cut_fill_areas": [
    {
      "type": "cut" | "fill",
      "area_description": "location/extent",
      "estimated_depth_ft": number or null,
      "notes": "any specific notes"
    }
  ],
  "grading_notes": [
    "Note 1: Topsoil stripping depth",
    "Note 2: Compaction requirements",
    "etc."
  ],
  "grid_data": [
    {
      "grid_point": "e.g., A-1, B-2",
      "existing_elevation_ft": number or null,
      "proposed_elevation_ft": number or null,
      "cut_fill_ft": number (positive = fill, negative = cut)
    }
  ],
  "summary": "Brief description of grading work shown"
}

If this is NOT a grading plan, return:
{
  "is_grading_plan": false,
  "summary": "This appears to be a [type of plan] plan, not a grading plan"
}
"""

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        return self.user_prompt_template

