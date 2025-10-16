"""Water system specialist researcher."""
from app.agents.researchers.base_researcher import BaseResearcher


class WaterResearcher(BaseResearcher):
    """Specialized researcher for water distribution systems."""
    
    def __init__(self):
        super().__init__(
            researcher_name="water",
            discipline="water",
            specialty="water mains including DI pipes, hydrants, and pressurized systems"
        )
    
    def get_system_prompt(self) -> str:
        return """You are a water distribution specialist for construction takeoff.

Your expertise:
- Water main materials (DI, PVC, HDPE for pressurized systems)
- Hydrants, gate valves, service lines
- Cover depth requirements (minimum 3.0ft, 4.5ft in frost zones)
- Water symbols: WM (water main), HYD (hydrant), GV (gate valve), WSL (water service)
- Typical diameters: 4-24 inches (6-12 inches most common)
- Pressurized systems (no minimum slope required)

Analyze for water mains, hydrants, and validate materials for pressure ratings."""

