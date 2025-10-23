"""
Legend Vision Agent - Extracts abbreviations, symbols, and specifications from title/legend pages.

This agent is specialized for reading title pages, legend boxes, and abbreviation tables
to extract critical contextual information that aids in interpreting the rest of the PDF.
"""
import logging
from typing import Dict, Any
from app.vision.base_vision_agent import BaseVisionAgent

logger = logging.getLogger(__name__)


class LegendVisionAgent(BaseVisionAgent):
    """
    Specialized Vision agent for extracting legend and abbreviation data.
    """
    
    def __init__(self):
        super().__init__(
            domain="legend",
            expertise="Legend, abbreviation, and symbol extraction from title pages"
        )
        
        self.system_prompt = """You are an expert at reading construction drawing title pages, legends, and abbreviation tables.

Your expertise:
- Extracting abbreviation tables (RCP, SS, WM, DIP, etc.)
- Reading symbol legends (circles, squares, line types)
- Identifying specification codes (NCDOT, ASTM, etc.)
- Capturing project information (name, location, engineer)
- Understanding measurement standards (scale, units)
"""

        self.user_prompt_template = """Analyze this construction drawing page for LEGEND and ABBREVIATION data.

═══════════════════════════════════════════════════════════════
WHAT TO EXTRACT
═══════════════════════════════════════════════════════════════

1. **ABBREVIATIONS** (Critical!)
   Look for tables or lists showing:
   - Material abbreviations: RCP, PVC, DI, DIP, HDPE, VCP, CMP, etc.
   - Discipline abbreviations: SS, STM, SD, WM, FM, etc.
   - Structure abbreviations: MH, CB, DI, CO, HYD, GV, etc.
   - Measurement abbreviations: LF, SY, CY, EA, etc.
   
   Format: "RCP = Reinforced Concrete Pipe"

2. **SYMBOLS**
   Look for symbol legends showing:
   - Structure symbols: circles (manholes), rectangles (catch basins), etc.
   - Line types: solid (existing), dashed (proposed), colored lines
   - Size indicators: how diameter is shown
   
   Format: "Circle with MH = Manhole"

3. **SPECIFICATIONS**
   Look for specification references:
   - NCDOT codes: 840.02, 840.14, 840.53, etc.
   - ASTM standards: ASTM D3034, etc.
   - Local standards
   
   Format: "NCDOT 840.02 = Concrete Catch Basin"

4. **PROJECT INFORMATION**
   Extract:
   - Project name
   - Location/address
   - Sheet number/title
   - Date
   - Engineer/firm name
   - Scale

5. **MEASUREMENT STANDARDS**
   Look for:
   - Scale (e.g., "1\" = 20'")
   - Units (feet, inches)
   - North arrow direction
   - Coordinate system

═══════════════════════════════════════════════════════════════
EXTRACTION PRIORITY
═══════════════════════════════════════════════════════════════

**HIGH PRIORITY** (extract these first):
1. Material abbreviations (RCP, PVC, DI, etc.)
2. Discipline abbreviations (SS, STM, WM, etc.)
3. Structure abbreviations (MH, CB, CO, etc.)

**MEDIUM PRIORITY**:
4. Specification codes (NCDOT, ASTM, etc.)
5. Symbol descriptions
6. Line type meanings

**LOW PRIORITY**:
7. Project info (name, location, etc.)
8. Measurement standards (scale, units)

═══════════════════════════════════════════════════════════════
IMPORTANT INSTRUCTIONS
═══════════════════════════════════════════════════════════════

1. **Be thorough**: Extract EVERY abbreviation you find
2. **Be precise**: Copy exact text from the legend
3. **Categorize**: Tag each item as "material", "discipline", "structure", "spec", etc.
4. **Handle variations**: "SS" might appear as "SS", "S.S.", or "SANITARY SEWER"
5. **ALWAYS return valid JSON** enclosed in ```json``` code blocks

═══════════════════════════════════════════════════════════════

Return JSON (MUST be enclosed in ```json``` code blocks):
```json
{
  "is_legend_page": true/false,
  "abbreviations": [
    {
      "abbr": "RCP",
      "full_name": "Reinforced Concrete Pipe",
      "category": "material"
    },
    {
      "abbr": "SS",
      "full_name": "Sanitary Sewer",
      "category": "discipline"
    },
    {
      "abbr": "MH",
      "full_name": "Manhole",
      "category": "structure"
    }
  ],
  "symbols": [
    {
      "symbol": "circle",
      "meaning": "Manhole",
      "discipline": "sanitary",
      "visual_description": "Circle with MH label"
    },
    {
      "symbol": "dashed_line",
      "meaning": "Proposed utility",
      "type": "line",
      "visual_description": "Dashed line indicates proposed work"
    }
  ],
  "specifications": [
    {
      "code": "NCDOT 840.02",
      "description": "Concrete Catch Basin",
      "category": "structure"
    }
  ],
  "project_info": {
    "name": "Dawn Ridge Homes",
    "location": "North Carolina",
    "sheet_number": "C-301",
    "sheet_title": "Utility Plan",
    "date": "2025-04-01",
    "engineer": "ABC Engineering",
    "scale": "1 inch = 20 feet"
  },
  "measurement_standards": {
    "scale": "1 inch = 20 feet",
    "units": "feet",
    "north": "up",
    "coordinate_system": "state plane"
  },
  "summary": "Brief description of what legend/abbreviation data was found"
}
```

EXAMPLES:

Material Abbreviation:
```json
{
  "abbr": "DIP",
  "full_name": "Ductile Iron Pipe",
  "category": "material"
}
```

Discipline Abbreviation:
```json
{
  "abbr": "STM",
  "full_name": "Storm Drain",
  "category": "discipline"
}
```

Symbol:
```json
{
  "symbol": "rectangle",
  "meaning": "Catch Basin",
  "discipline": "storm",
  "visual_description": "Rectangle with CB label"
}
```

Specification:
```json
{
  "code": "NCDOT 840.14",
  "description": "Drop Inlet",
  "category": "structure"
}
```

If this is NOT a legend/title page:
```json
{
  "is_legend_page": false,
  "abbreviations": [],
  "symbols": [],
  "specifications": [],
  "summary": "This page contains utility plans, not legend data"
}
```"""

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def get_user_prompt(self) -> str:
        return self.user_prompt_template

