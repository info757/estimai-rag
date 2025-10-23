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

        self.user_prompt_template = """Analyze this construction document and extract ALL utility infrastructure.

COMPREHENSIVE EXTRACTION - Extract ALL of the following categories:

═══════════════════════════════════════════════════════════════
1. MAINLINE PIPES (Primary utility lines)
═══════════════════════════════════════════════════════════════
Look for:
- Storm drains: RCP, HDPE, Corrugated HDPE (12", 15", 18", 24", 30", 48")
- Sanitary sewers: PVC, DIP, VCP (4", 6", 8", 10")
- Water mains: DIP, DI, Ductile Iron (4", 6", 8", 10", 12")

Extract: diameter, material, length, depth

═══════════════════════════════════════════════════════════════
2. LATERALS/SERVICE CONNECTIONS (Branch lines to buildings)
═══════════════════════════════════════════════════════════════
CRITICAL: These are often MISSED but represent 30-50% of total work!

Visual cues:
- Shown as DASHED or THIN lines branching off mains
- Perpendicular to main pipes
- Labeled: "4\" SS Service", "Copper Service", "6\" Fire Lateral"
- Typically 20-50 LF each

Common types:
- Sanitary laterals: "4\" SS Service", "4\" SSL", "SS Service Lateral"
- Water services: "Copper Service to meter", "1\" Service", "Copper Service"
- Fire connections: "6\" Fire Lateral", "Fire Service"

Extract: diameter, type, count (how many connections), length each

═══════════════════════════════════════════════════════════════
3. STRUCTURES (Vertical access points)
═══════════════════════════════════════════════════════════════
CRITICAL: Count each structure individually!

Manholes:
- Labels: MH-1, MH-2, SSMH, "Sanitary Sewer Manhole"
- Shown as: Circles with labels
- Extract: name, rim elevation, invert elevation

Catch Basins:
- Labels: CB-1, CB-2, "NCDOT 840.02 Concrete Catch Basin"
- Shown as: Rectangles or circles
- Often at curb/gutter locations

Drop Inlets:
- Labels: DI-1, DI-2, "NCDOT 840.14 Drop Inlet"
- Shown as: Rectangles
- Stormwater collection points

Cleanouts:
- Labels: CO, "4\" SSL Cleanout", "Cleanout"
- Small circles or symbols
- End of lateral lines

Hydrants:
- Labels: "6\" Hydrant Assembly", "Fire Hydrant"
- Shown as: Hydrant symbols
- Along water mains

═══════════════════════════════════════════════════════════════
4. FITTINGS & APPURTENANCES
═══════════════════════════════════════════════════════════════
Extract these specialty items:

- FES: "Flared End Section", "15\" FES", "24\" FES"
- Valves: "Gate Valve", "8\" Gate Valve", "Check Valve"  
- Tees, Bends, Reducers: Connection fittings
- Antiseep Collars: "Antiseep Collars w/watertight joints"
- Tie-ins: "Tie into Existing"

═══════════════════════════════════════════════════════════════
5. DEPTH/ELEVATION DATA
═══════════════════════════════════════════════════════════════
For EACH item above, look for depth information:

Depth callouts:
- "0-6'" (0 to 6 feet deep)
- "6-8'" (6 to 8 feet deep)
- "Average Depth: 9.2 ft"

Invert Elevations (IE):
- IE, INV, IE IN, IE OUT, INV IN, INV OUT
- Example: "IE 645.50", "INV IN 644.0"

Rim Elevations:
- RIM, TOP, GL, FFE, EG
- Example: "RIM 655.0", "TOP 850.0"

═══════════════════════════════════════════════════════════════
6. LEGEND/ABBREVIATIONS
═══════════════════════════════════════════════════════════════
Extract any legend or abbreviation table on this page for material decoding.

═══════════════════════════════════════════════════════════════

IMPORTANT INSTRUCTIONS:
1. Extract INDIVIDUAL items, not summary totals
2. For laterals: If you see "26 connections", create 26 separate lateral entries
3. For structures: Count each MH, CB, DI, CO individually
4. If quantities are grouped (e.g., "4\" SS Service (26)"), expand to individual items
5. ALWAYS return valid JSON enclosed in ```json``` code blocks

Return JSON (MUST be enclosed in ```json``` code blocks):
```json
{
  "pipes": [
    {
      "item_type": "mainline" | "lateral" | "structure" | "fitting",
      "discipline": "storm" | "sanitary" | "water",
      "material": "pipe material (DIP, PVC, RCP, HDPE, Copper, etc.)",
      "diameter_in": number,
      "length_ft": number or null,
      "count": number (default 1, or actual count for laterals/structures),
      "depth_ft": number or null,
      "invert_in_ft": number or null,
      "invert_out_ft": number or null,
      "rim_elevation_ft": number or null,
      "structure_name": "Full name like 'MH-1', 'CB-2', '4\" SS Service', 'NCDOT 840.02 Catch Basin'",
      "from_structure": "structure name like MH-1, CB-2" or null,
      "to_structure": "structure name" or null,
      "station_start": "station like 1+00" or null,
      "station_end": "station like 2+50" or null,
      "notes": "any additional details"
    }
  ],
  "legend": {
    "abbreviation": "full name",
    "example": "DIP: Ductile Iron Pipe"
  },
  "summary": "Brief description listing counts: X mainline pipes, Y laterals, Z structures, W fittings"
}
```

EXAMPLES:

Mainline pipe:
```json
{
  "item_type": "mainline",
  "discipline": "storm",
  "material": "RCP",
  "diameter_in": 15,
  "length_ft": 100,
  "count": 1,
  "depth_ft": 5.2,
  "structure_name": "15\" RCP"
}
```

Service lateral (if you see "26 connections"):
```json
{
  "item_type": "lateral",
  "discipline": "sanitary",
  "material": "PVC",
  "diameter_in": 4,
  "length_ft": 31.4,
  "count": 26,
  "depth_ft": 6.1,
  "structure_name": "4\" SS Service"
}
```

Structure:
```json
{
  "item_type": "structure",
  "discipline": "storm",
  "material": "Concrete",
  "diameter_in": 48,
  "length_ft": null,
  "count": 1,
  "depth_ft": 4.6,
  "rim_elevation_ft": 850.0,
  "invert_elevation_ft": 845.4,
  "structure_name": "NCDOT 840.02 Concrete Catch Basin CB-1"
}
```

Fitting:
```json
{
  "item_type": "fitting",
  "discipline": "storm",
  "material": "Concrete",
  "diameter_in": 24,
  "length_ft": null,
  "count": 1,
  "structure_name": "24\" FES (Flared End Section)"
}
```"""

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        return self.user_prompt_template

