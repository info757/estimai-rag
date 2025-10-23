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

        self.user_prompt_template = """Analyze this construction document for GRADING, EROSION CONTROL, and SITE WORK.

═══════════════════════════════════════════════════════════════
1. GRADING & EARTHWORK
═══════════════════════════════════════════════════════════════
- Contour Lines: Existing grade vs. Proposed grade contours
- Spot Elevations: "EG 845.5" (Existing), "FG 846.0" (Finished/Proposed)
- Cut/Fill Areas: Areas marked as CUT or FILL with quantities
- Grid Elevations: Tables showing elevations at grid points
- Slope Indicators: Arrows showing slope direction and grade
- Grading Notes: Notes about compaction, topsoil stripping, etc.

═══════════════════════════════════════════════════════════════
2. EROSION CONTROL (CRITICAL - Often marked as "EC" or "Phase 1/2 EC")
═══════════════════════════════════════════════════════════════
Look for these items (shown on plans or in tables):

Temporary Measures:
- **Silt Fence** / **Diversion Ditch**: Wavy lines on site perimeter (measure in LF)
- **Construction Entrance**: Gravel pad at site entrance (measure in SY)
- **Inlet Protection**: Circles/symbols around storm inlets
  - "Block and Gravel Inlet Protection"
  - "Sediment Tube Inlet Protection"  
  - Count: number of inlets (EA)
- **Concrete Washout**: Designated area for concrete truck washout (EA)
- **Baffles**: Filter barriers in pond/detention basin (LF)
- **Skimmer**: Oil/sediment skimmer in pond (EA, often "3\" Skimmer")

Permanent Measures:
- **Slope Matting**: Hatched areas on slopes (measure in SY)
  - "Ditch Matting - SC140"
  - "Slope Matting"
- **Grassing/Seeding**: Areas to be seeded (measure in AC or SY)

═══════════════════════════════════════════════════════════════
3. SITE IMPROVEMENTS
═══════════════════════════════════════════════════════════════
- **Retaining Walls**: Thick lines with height callouts (measure in LF, note height)
  - Example: "Retaining Wall along Northern Perimeter: 384.5 LF x 8-10 ft"
- **Fencing**: Perimeter or specialty fencing (measure in LF)
  - "Chain Link Fence"
  - "Privacy Fence"  
  - "Fencing around Wet Pond"
  - "Retaining Wall Fencing"

═══════════════════════════════════════════════════════════════

IMPORTANT:
1. Extract quantities: LF (linear feet), SY (square yards), AC (acres), EA (each)
2. Look in tables, notes, and on-plan callouts
3. ALWAYS return valid JSON enclosed in ```json``` code blocks

Return JSON (MUST be enclosed in ```json``` code blocks):
```json
{
  "is_grading_plan": true/false,
  "grading_data": {
    "spot_elevations": [
      {
        "type": "existing" | "proposed",
        "elevation_ft": number,
        "location": "description",
        "station": "station if applicable"
      }
    ],
    "contours": {
      "existing_contours": ["elevations found"],
      "proposed_contours": ["elevations found"],
      "contour_interval": "e.g., 1 ft"
    },
    "cut_fill_areas": [
      {
        "type": "cut" | "fill",
        "area_description": "location",
        "volume_cy": number or null,
        "notes": "any notes"
      }
    ],
    "grading_notes": ["note 1", "note 2"]
  },
  "erosion_control": [
    {
      "item": "Silt Fence",
      "quantity": number,
      "unit": "LF" | "SY" | "EA" | "AC",
      "phase": "Phase 1 EC" | "Phase 2 EC" | null,
      "notes": "any notes"
    }
  ],
  "site_work": [
    {
      "item": "Retaining Wall",
      "quantity": number,
      "unit": "LF",
      "height_ft": number or null,
      "location": "description",
      "notes": "any notes"
    }
  ],
  "summary": "Brief description: X erosion control items, Y site improvements, grading data found/not found"
}
```

EXAMPLES:

Erosion Control:
```json
{
  "item": "Diversion Ditch",
  "quantity": 1748.97,
  "unit": "LF",
  "phase": "Phase 1 EC",
  "notes": null
}
```

Site Work:
```json
{
  "item": "Retaining Wall along Northern Perimeter",
  "quantity": 384.5,
  "unit": "LF",
  "height_ft": 9.0,
  "location": "Northern property line",
  "notes": "8-10 ft height"
}
```

If this is NOT a relevant document:
```json
{
  "is_grading_plan": false,
  "erosion_control": [],
  "site_work": [],
  "summary": "This is a utility plan, no grading/erosion control data"
}
```"""

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        return self.user_prompt_template

