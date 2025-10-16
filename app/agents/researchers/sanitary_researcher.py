"""Sanitary sewer specialist researcher."""
from app.agents.researchers.base_researcher import BaseResearcher


class SanitaryResearcher(BaseResearcher):
    """Specialized researcher for sanitary sewer systems."""
    
    def __init__(self):
        super().__init__(
            researcher_name="sanitary",
            discipline="sanitary",
            specialty="sanitary sewer systems including manholes, PVC/VCP pipes, and gravity sewers"
        )
    
    def get_system_prompt(self) -> str:
        return """You are a sanitary sewer specialist for construction takeoff.

Your expertise:
- Sanitary sewer materials (PVC, VCP, DI)
- Manholes (MH, SSMH symbols)
- Cover depth requirements (minimum 2.5ft general, 4.0ft under roads)
- Sanitary symbols: SS (sanitary sewer), SSMH (sanitary sewer manhole), INV (invert)
- Typical diameters: 6-18 inches for laterals and mains
- Minimum slopes: 1.0% for 4", 0.6% for 6", 0.5% for 8", 0.4% for 10-12"

Analyze for sanitary sewer pipes, inverts, manholes, and validate against standards."""

