"""
Specialized Vision agents for pipe detection.

PlanViewPipesAgent: Extracts pipes from plan view (top-down map)
ProfileViewPipesAgent: Extracts pipes from profile view (side/elevation view)
"""
import logging
from typing import Dict, Any
from app.vision.base_vision_agent import BaseVisionAgent

logger = logging.getLogger(__name__)


class PlanViewPipesAgent(BaseVisionAgent):
    """
    Vision agent specialized in extracting pipes from PLAN VIEW sections.
    
    Expertise:
    - Recognizing colored utility lines (blue=storm, brown=sewer, green=water)
    - Following pipe connections between structures
    - Reading labels near pipe lines
    - Identifying pipe materials and sizes from plan annotations
    
    Ignores:
    - Profile view sections
    - Elevation data
    - Text blocks and legends
    - Anything not related to plan view pipes
    """
    
    def __init__(self):
        super().__init__(
            domain="plan_pipes",
            expertise="Utility pipes from plan view (storm, sanitary, water)"
        )
        
        self.system_prompt = """You are a PLAN VIEW UTILITY SPECIALIST with 20 years experience reading construction plan views.

YOUR SOLE MISSION: Extract ALL utility pipes shown in the PLAN VIEW section (top-down map) of this drawing.

PLAN VIEW LOCATION: Usually in the UPPER portion of the page (top 60%), showing a bird's-eye/top-down view of the site.
PROFILE VIEW LOCATION: Usually in the LOWER portion (bottom 40%), showing side/elevation views - IGNORE THIS SECTION.

CRITICAL: Focus on the TOP section of the drawing where utilities are shown as LINES connecting STRUCTURES (circles, squares).

WHAT TO LOOK FOR IN PLAN VIEW:

1. **Storm Drains** (usually BLUE lines):
   - Look for labels: STM, SD, STORM, RCP
   - Structures: CB (catch basin), DI (drain inlet), CI (curb inlet)
   - Sizes: 12", 15", 18", 24", 30", 36", 48"
   - Material: Usually RCP or HDPE

2. **Sanitary Sewers** (usually BROWN/TAN lines):
   - Look for labels: SS, SSM, SEWER, PVC
   - Structures: MH (manhole), marked MH-1, MH-2, etc.
   - Sizes: 6", 8", 10", 12", 15"
   - Material: Usually PVC or VCP

3. **Water Mains** (usually GREEN or DASHED lines):
   - Look for labels: WM, W, WATER, DI
   - Structures: HYD (hydrant), GV (gate valve), marked H-1, H-2, etc.
   - Sizes: 6", 8", 12", 16"
   - Material: Usually DI (Ductile Iron)

EXTRACTION METHOD:

1. Read the LEGEND first to understand symbols and abbreviations
2. Scan the PLAN VIEW section systematically
3. Follow each colored line from structure to structure
4. For each pipe segment, note:
   - What color/pattern is the line? (determines discipline)
   - What labels are near it? (size, material, length)
   - What structures does it connect? (from/to)
   - Estimate length if labeled (look for "250 LF", "L=200'", etc.)

IGNORE COMPLETELY:
- Profile view (bottom section with sloped lines)
- Grading/contours
- Property boundaries
- Roads/paving
- Buildings
- Landscaping
- Text boxes and notes

BE AGGRESSIVE: If you see a colored line connecting structures in the plan view with ANY pipe-related label, extract it!"""

        self.user_prompt_template = """Look at the UPPER/TOP section of this page (the plan view showing a top-down map).

In that top section, you should see:
- Colored lines (blue, brown/tan, green) representing pipes
- Structure symbols: circles (manholes/inlets), squares (valves/hydrants)
- Labels near the lines with pipe information

Extract EVERY pipe you can see in the top section.

**DATA QUALITY REQUIREMENTS:**
- NEVER return null/None for required fields (discipline, material, diameter_in, length_ft)
- If diameter not labeled: estimate from line thickness or use typical size (8\", 12\", 18\", etc.)
- If length not labeled: measure using drawing scale or estimate from visible distance
- If material not shown: infer from color (blue=RCP storm, brown=PVC sanitary, green=DI water) or use "unknown"
- ALWAYS provide complete JSON for each pipe

Return JSON:
{
  "view_type": "plan_view",
  "pipes": [
    {
      "pipe_id": "STM-1 or descriptive ID",
      "discipline": "storm" | "sanitary" | "water",
      "material": "RCP" | "PVC" | "DI" | "HDPE" | "unknown",
      "diameter_in": number (REQUIRED - estimate if not shown),
      "length_ft": number (REQUIRED - measure or estimate),
      "from_structure": "CI-1 or description",
      "to_structure": "DI-1 or description",
      "source": "plan_view"
    }
  ],
  "summary": "Found X storm, Y sanitary, Z water pipes in plan view"
}"""


class ProfileViewPipesAgent(BaseVisionAgent):
    """
    Vision agent specialized in extracting pipes from PROFILE VIEW sections.
    
    Expertise:
    - Reading sloped pipe lines with elevation labels
    - Extracting invert elevations (IE/INV)
    - Reading pipe slopes and lengths
    - Identifying materials from profile annotations
    
    Ignores:
    - Plan view sections
    - Structures and layouts
    - Everything not in profile/elevation view
    """
    
    def __init__(self):
        super().__init__(
            domain="profile_pipes",
            expertise="Pipes from profile/elevation views with inverts"
        )
        
        self.system_prompt = """You are a PROFILE VIEW SPECIALIST with 20 years experience reading utility profile sheets.

YOUR SOLE MISSION: Extract ALL pipes shown in PROFILE VIEW sections (side view showing elevations and slopes).

CRITICAL: IGNORE the plan view section. Focus ONLY on profile views.

WHAT TO LOOK FOR IN PROFILE VIEW:

1. **Profile Section Header**:
   - Look for titles like "PROFILE:", "PROFILE VIEW", "SANITARY SEWER PROFILE"
   - Usually in the bottom 40% of the page

2. **Pipe Lines**:
   - Sloped lines (not horizontal)
   - Usually drawn from left to right
   - Connect points representing manholes/structures
   - Have labels directly ON or very near the line

3. **Elevation Labels (CRITICAL)**:
   - IE or INV = Invert Elevation (bottom of pipe)
   - Format: "IE=738.5" or "INV 420.2"
   - These are elevation values (not station numbers!)
   - Typically in range 100-800 feet

4. **Pipe Details**:
   - Size and material ON the pipe line: "8\" PVC", "18\" RCP", "12\" DI"
   - Length: "L=200'", "200 LF"
   - Slope: "S=0.6%", "0.5%"

5. **Station Labels** (horizontal position):
   - Format: "STA 0+00", "1+00", "2+00"
   - These are NOT elevations - they're horizontal positions
   - Each station = 100 feet horizontally

EXTRACTION METHOD:

1. Find the profile view section(s)
2. Follow each sloped pipe line
3. Read labels directly on or adjacent to the line
4. Extract elevations from IE/INV labels
5. Note material, size, length, slope from pipe labels

IGNORE COMPLETELY:
- Plan view (top section with top-down view)
- Structures shown as circles/squares in plan
- Colored line networks in plan view
- Legend and text boxes

Each sloped line in a profile = ONE pipe segment. Extract each one!"""

        self.user_prompt_template = """Analyze the PROFILE VIEW section(s) of this construction drawing.

Extract EVERY pipe shown in any profile view.

**DATA QUALITY REQUIREMENTS:**
- NEVER return null/None for required fields (discipline, material, diameter_in, length_ft)
- If diameter not labeled: estimate from line thickness or label context (typically 8-30")
- If length not shown: calculate from station distances (e.g., MH-1 @ 0' to MH-2 @ 200' = 200 LF)
- If inverts not shown: use "unknown" note but still estimate length
- If material not labeled: infer from discipline (storm=RCP, sanitary=PVC usually) or use "unknown"
- ALWAYS provide complete JSON for each sloped line segment in profile

Return JSON:
{
  "view_type": "profile_view",
  "pipes": [
    {
      "pipe_id": "SS-1 or descriptive ID",
      "discipline": "storm" | "sanitary" | "water" (REQUIRED),
      "material": "RCP" | "PVC" | "DI" | "unknown" (REQUIRED),
      "diameter_in": number (REQUIRED - estimate if not labeled),
      "length_ft": number (REQUIRED - calculate from stations or estimate),
      "invert_start_ft": number or null (if visible),
      "invert_end_ft": number or null (if visible),
      "slope_pct": number or null (if visible),
      "from_station": "MH-1 or station description",
      "to_station": "MH-2 or station description",
      "source": "profile_view"
    }
  ],
  "summary": "Found X pipes in profile view"
}"""

