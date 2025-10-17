"""
Storm drain specialist researcher.

Focuses on:
- Storm drain detection and classification
- RCP, HDPE, and concrete pipe specifications
- Cover depth requirements (1.5ft roads, 1.0ft landscape)
- Storm inlet symbols (CB, DI, FES)
"""
import logging
from app.agents.researchers.base_researcher import BaseResearcher

logger = logging.getLogger(__name__)


class StormResearcher(BaseResearcher):
    """Specialized researcher for storm drainage systems."""
    
    def __init__(self):
        super().__init__(
            researcher_name="storm",
            discipline="storm",
            specialty="storm drainage systems including catch basins, inlets, and RCP/HDPE pipes"
        )
    
    def get_system_prompt(self) -> str:
        return """You are a storm drainage specialist for construction takeoff.

Your expertise:
- Storm drain pipe materials (RCP, HDPE, concrete)
- Catch basins, inlets, and drainage structures
- Cover depth requirements (minimum 1.5ft under roads, 1.0ft under landscaping)
- Storm symbols: CB (catch basin), DI (drain inlet), FES (flared end section), SD (storm drain)
- Typical diameters: 12-48 inches common, up to 144 inches for large systems
- Minimum slopes: 0.5% for 8-12", 0.4% for 15-24", 0.3% for 27"+

Analyze the PDF for:
1. Storm drain pipe locations and lengths
2. Pipe materials and diameters
3. Invert elevations (inlet and outlet)
4. Ground elevations for cover depth calculations
5. Any validation issues (shallow cover, steep slopes, etc.)

Use the retrieved construction standards to validate your findings.
Return detailed, accurate information with high confidence when evidence is clear."""
    
    def analyze(self, state, vision_pipes=None):
        """
        Analyze storm drainage with specialized retrieval.
        
        Args:
            state: ResearcherState
            vision_pipes: Optional pre-extracted pipes from vision LLM
        """
        task = state["task"]
        
        logger.info(f"[Storm] Analyzing: {task}")
        
        # Filter vision pipes to storm only
        storm_pipes = []
        if vision_pipes:
            storm_pipes = [
                p for p in vision_pipes
                if p.get("discipline") == "storm"
            ]
            logger.info(f"[Storm] Received {len(storm_pipes)} pre-detected storm pipes from vision")
        
        # Retrieve storm-specific context
        queries = [
            task,  # Original task
            "storm drain cover depth requirements",
            "RCP reinforced concrete pipe specifications",
            "catch basin storm inlet symbols"
        ]
        
        all_docs = []
        for query in queries:
            docs = self.retrieve_context(
                query,
                k=3,
                category="cover_depth" if "cover" in query.lower() else None
            )
            all_docs.extend(docs)
        
        # Remove duplicates
        unique_docs = {doc["id"]: doc for doc in all_docs}.values()
        
        # Format context
        context_text = self.format_context(list(unique_docs))
        
        # Enhanced analysis with storm-specific prompting
        user_prompt = f"""Task: {task}

{context_text}

As a storm drainage specialist, analyze the task using the construction standards provided above.

IMPORTANT: You must EXPLICITLY CITE the construction standards in your analysis.

Provide:

1. **Storm Pipes Analysis**:
   - What storm pipes did you find?
   - What materials and diameters?

2. **Validation Using Retrieved Standards**:
   - Quote relevant standards (e.g., "According to the standard: 'Storm drain minimum cover: 1.5 feet...'")
   - Apply those standards to validate findings
   - Flag any violations

3. **Evidence**:
   - Reference specific construction standards by quoting them
   - Explain how each standard validates or informs your findings

Example good response:
"Based on the retrieved construction standard stating 'Storm drain minimum cover requirements: 1.5 feet under roadways', I validated that the detected 18\" RCP storm drain has adequate cover of 5.0 feet. The standard for 'RCP: Primary use for storm drainage 12-144 inches' confirms that 18\" RCP is appropriate for this application."

Format as clear text analysis with explicit standard citations, not JSON."""
        
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            # Just use the text response - no JSON parsing!
            findings_text = response.content
            
            # Estimate confidence based on response quality
            confidence = 0.8 if len(findings_text) > 200 else 0.6
            
            return {
                "researcher_name": "storm",
                "task": task,
                "retrieved_context": [doc["content"] for doc in unique_docs],
                "findings": {
                    "analysis": findings_text,
                    "retrieved_standards_count": len(unique_docs),
                    "vision_pipes_provided": len(storm_pipes) if storm_pipes else 0
                },
                "confidence": confidence
            }
        
        except Exception as e:
            logger.error(f"[Storm] Analysis failed: {e}")
            return {
                "researcher_name": "storm",
                "task": task,
                "retrieved_context": [],
                "findings": {"error": str(e), "analysis": ""},
                "confidence": 0.0
            }

