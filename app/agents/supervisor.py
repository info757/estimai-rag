"""
Supervisor Agent - coordinates specialized researchers.

The supervisor:
1. Receives PDF analysis from Main Agent
2. Deploys appropriate researchers based on what's in the PDF
3. Collects and validates researcher findings
4. Resolves conflicts between researchers
5. Consolidates data for Main Agent
"""
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.models import SupervisorState, ResearcherState
from app.agents.researchers.storm_researcher import StormResearcher
from app.agents.researchers.sanitary_researcher import SanitaryResearcher
from app.agents.researchers.water_researcher import WaterResearcher
from app.agents.researchers.elevation_researcher import ElevationResearcher
from app.agents.researchers.legend_researcher import LegendResearcher
from app.agents.researchers.api_researcher import APIResearcher

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Supervisor coordinates multiple specialized researchers.
    
    Acts as middle management between Main Agent and Researchers.
    """
    
    def __init__(self):
        """Initialize supervisor with all researchers."""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )
        
        # Initialize all researchers
        self.researchers = {
            "storm": StormResearcher(),
            "sanitary": SanitaryResearcher(),
            "water": WaterResearcher(),
            "elevation": ElevationResearcher(),
            "legend": LegendResearcher()
        }
        
        # Initialize API researcher for low-confidence augmentation
        self.api_researcher = APIResearcher()
        
        logger.info("Supervisor initialized with 5 researchers + API augmentation")
    
    def plan_research(self, pdf_summary: str) -> List[Dict[str, str]]:
        """
        Analyze PDF summary and decide which researchers to deploy.
        
        Args:
            pdf_summary: Summary from Main Agent describing PDF content
        
        Returns:
            List of tasks for researchers
        """
        logger.info("Planning research tasks...")
        
        prompt = f"""Based on this PDF summary, determine which researchers to deploy and what tasks to assign them.

PDF Summary:
{pdf_summary}

Available Researchers:
- storm: Storm drainage systems (RCP, catch basins, inlets)
- sanitary: Sanitary sewers (PVC, manholes, gravity sewers)
- water: Water distribution (DI pipes, hydrants, pressurized systems)
- elevation: Invert and ground elevations, depth calculations
- legend: Symbol interpretation and legend reading

Return JSON list of tasks:
[
  {{"researcher": "storm", "task": "Extract storm drain pipes from plan view"}},
  {{"researcher": "elevation", "task": "Read all invert elevations from profile sheet"}}
]

Only deploy researchers relevant to what's actually in the PDF."""
        
        messages = [
            SystemMessage(content="You are a construction takeoff supervisor coordinating specialized researchers."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            import json
            import re
            
            # Extract JSON from response (might be wrapped in markdown or have text)
            content = response.content
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                tasks = json.loads(json_match.group())
            else:
                # Try parsing whole response
                tasks = json.loads(content)
            
            logger.info(f"Planned {len(tasks)} research tasks")
            for task in tasks:
                logger.info(f"  - {task['researcher']}: {task['task'][:50]}...")
            
            return tasks
        
        except Exception as e:
            logger.warning(f"Task planning failed ({e}), using default deployment")
            # Fallback: deploy all researchers (this is fine!)
            return [
                {"researcher": "legend", "task": "Read and interpret the drawing legend and symbols"},
                {"researcher": "storm", "task": "Extract all storm drainage information"},
                {"researcher": "sanitary", "task": "Extract all sanitary sewer information"},
                {"researcher": "water", "task": "Extract all water main information"},
                {"researcher": "elevation", "task": "Extract all elevation data and calculate depths"}
            ]
    
    def execute_research(
        self,
        tasks: List[Dict[str, str]],
        parallel: bool = True
    ) -> Dict[str, ResearcherState]:
        """
        Execute research tasks, optionally in parallel.
        
        Args:
            tasks: List of tasks from plan_research
            parallel: Whether to run researchers in parallel
        
        Returns:
            Dict of researcher_name -> ResearcherState with findings
        """
        logger.info(f"Executing {len(tasks)} research tasks (parallel={parallel})")
        
        results = {}
        
        if parallel:
            # Run researchers in parallel for speed
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                
                for task_spec in tasks:
                    researcher_name = task_spec["researcher"]
                    task = task_spec["task"]
                    
                    if researcher_name not in self.researchers:
                        logger.warning(f"Unknown researcher: {researcher_name}")
                        continue
                    
                    researcher = self.researchers[researcher_name]
                    
                    # Create researcher state
                    state: ResearcherState = {
                        "researcher_name": researcher_name,
                        "task": task,
                        "retrieved_context": [],
                        "findings": {},
                        "confidence": 0.0
                    }
                    
                    # Submit task
                    future = executor.submit(researcher.analyze, state)
                    futures[researcher_name] = future
                
                # Collect results
                for researcher_name, future in futures.items():
                    try:
                        result = future.result(timeout=120)  # 2 minute timeout per researcher
                        results[researcher_name] = result
                        logger.info(
                            f"[{researcher_name}] Complete. "
                            f"Confidence: {result['confidence']:.2f}"
                        )
                    except Exception as e:
                        logger.error(f"[{researcher_name}] Failed: {e}")
                        results[researcher_name] = {
                            "researcher_name": researcher_name,
                            "task": task_spec["task"],
                            "retrieved_context": [],
                            "findings": {"error": str(e)},
                            "confidence": 0.0
                        }
        else:
            # Run sequentially
            for task_spec in tasks:
                researcher_name = task_spec["researcher"]
                task = task_spec["task"]
                
                if researcher_name not in self.researchers:
                    continue
                
                researcher = self.researchers[researcher_name]
                
                state: ResearcherState = {
                    "researcher_name": researcher_name,
                    "task": task,
                    "retrieved_context": [],
                    "findings": {},
                    "confidence": 0.0
                }
                
                try:
                    result = researcher.analyze(state)
                    results[researcher_name] = result
                except Exception as e:
                    logger.error(f"[{researcher_name}] Failed: {e}")
                    results[researcher_name] = {
                        "researcher_name": researcher_name,
                        "task": task,
                        "retrieved_context": [],
                        "findings": {"error": str(e)},
                        "confidence": 0.0
                        }
        
        logger.info(f"Research complete: {len(results)} researchers finished")
        
        # Check if API augmentation is needed for low-confidence results
        low_confidence_researchers = []
        for name, result in results.items():
            confidence = result.get('confidence', 0.0)
            retrieved_count = result.get('retrieved_standards_count', 0)
            
            if confidence < 0.5 or retrieved_count < 3:
                low_confidence_researchers.append((name, result))
                logger.warning(
                    f"[{name}] Low confidence detected: "
                    f"confidence={confidence:.2f}, contexts={retrieved_count}"
                )
        
        # Deploy API researcher for low-confidence cases
        if low_confidence_researchers:
            logger.info(
                f"Deploying API researcher for {len(low_confidence_researchers)} "
                "low-confidence researchers"
            )
            
            for name, result in low_confidence_researchers:
                task = result.get('task', '')
                logger.info(f"[api] Augmenting {name} researcher with external search")
                
                try:
                    # Query external APIs with the researcher's task
                    api_result = self.api_researcher.analyze(
                        {"task": f"Find construction standards for: {task}"},
                        vision_pipes=result.get('findings', {}).get('pipes', [])
                    )
                    
                    # Merge API context into original result
                    if api_result.get('retrieved_context'):
                        result['retrieved_context'].extend(api_result['retrieved_context'])
                        result['retrieved_standards_count'] = (
                            result.get('retrieved_standards_count', 0) + 
                            len(api_result['retrieved_context'])
                        )
                        result['api_augmented'] = True
                        result['confidence'] = min(
                            1.0,
                            result['confidence'] + 0.2  # Boost confidence with external data
                        )
                        
                        logger.info(
                            f"[api] Augmented {name}: added {len(api_result['retrieved_context'])} "
                            f"external contexts, new confidence: {result['confidence']:.2f}"
                        )
                    else:
                        logger.warning(f"[api] No external context found for {name}")
                        result['api_augmented'] = False
                
                except Exception as e:
                    logger.error(f"[api] Failed to augment {name}: {e}")
                    result['api_augmented'] = False
        
        return results
    
    def consolidate_findings(
        self,
        researcher_results: Dict[str, ResearcherState]
    ) -> Dict[str, Any]:
        """
        Consolidate and validate findings from all researchers.
        
        Args:
            researcher_results: Results from execute_research
        
        Returns:
            Consolidated takeoff data
        """
        logger.info("Consolidating researcher findings...")
        
        # Format results for LLM
        findings_text = ""
        for name, result in researcher_results.items():
            findings_text += f"\n## {name.upper()} Researcher\n"
            findings_text += f"Confidence: {result['confidence']:.2f}\n"
            findings_text += f"Findings: {result['findings']}\n"
            findings_text += f"Context Used: {len(result['retrieved_context'])} standards\n"
        
        prompt = f"""Consolidate findings from specialized researchers into a unified takeoff report.

{findings_text}

Your tasks:
1. **Aggregate Counts**: Total pipes by discipline (storm, sanitary, water)
2. **Aggregate Lengths**: Total linear feet by discipline
3. **Extract Details**: Materials, diameters, elevations found
4. **Identify Conflicts**: Do any researchers contradict each other?
5. **Assess Quality**: Overall confidence and completeness
6. **Flag Issues**: Any validation problems or missing data

Return JSON:
{{
    "summary": {{
        "storm_pipes": int,
        "sanitary_pipes": int,
        "water_pipes": int,
        "total_pipes": int,
        "storm_lf": float,
        "sanitary_lf": float,
        "water_lf": float,
        "total_lf": float
    }},
    "materials_found": ["PVC", "DI", "RCP"],
    "diameters_found": [8, 12, 18],
    "elevations_extracted": bool,
    "conflicts": [],
    "overall_confidence": 0.0-1.0,
    "validation_issues": [],
    "recommendations": ""
}}"""
        
        messages = [
            SystemMessage(content="You are a construction takeoff supervisor consolidating researcher findings."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            # Just use text consolidation - no JSON parsing!
            consolidation_text = response.content
            
            # Calculate simple summary from vision results if available
            consolidated = {
                "summary": {
                    "storm_pipes": 0,
                    "sanitary_pipes": 0,
                    "water_pipes": 0,
                    "total_pipes": 0,
                    "storm_lf": 0.0,
                    "sanitary_lf": 0.0,
                    "water_lf": 0.0,
                    "total_lf": 0.0
                },
                "consolidation_analysis": consolidation_text,
                "materials_found": [],
                "diameters_found": [],
                "elevations_extracted": False,
                "conflicts": [],
                "overall_confidence": sum(r.get("confidence", 0) for r in researcher_results.values()) / len(researcher_results) if researcher_results else 0.0,
                "validation_issues": [],
                "recommendations": "Review researcher findings"
            }
            
            logger.info(
                f"Consolidation complete. Overall confidence: {consolidated['overall_confidence']:.2f}"
            )
            
            return consolidated
        
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            # Fallback: basic structure
            return {
                "summary": {
                    "storm_pipes": 0,
                    "sanitary_pipes": 0,
                    "water_pipes": 0,
                    "total_pipes": 0,
                    "storm_lf": 0.0,
                    "sanitary_lf": 0.0,
                    "water_lf": 0.0,
                    "total_lf": 0.0
                },
                "consolidation_analysis": str(e),
                "materials_found": [],
                "diameters_found": [],
                "elevations_extracted": False,
                "conflicts": [],
                "overall_confidence": 0.0,
                "validation_issues": ["Consolidation failed"],
                "recommendations": "Manual review required"
            }
    
    def supervise(self, state: SupervisorState) -> SupervisorState:
        """
        Main supervision workflow.
        
        Args:
            state: SupervisorState with PDF summary
        
        Returns:
            Updated state with consolidated data
        """
        pdf_summary = state["pdf_summary"]
        
        logger.info("=== SUPERVISOR STARTING ===")
        
        # Step 1: Plan research tasks
        tasks = self.plan_research(pdf_summary)
        
        # Step 2: Execute research (parallel)
        researcher_results = self.execute_research(tasks, parallel=True)
        
        # Step 3: Consolidate findings
        consolidated = self.consolidate_findings(researcher_results)
        
        # Step 4: Identify conflicts
        conflicts = consolidated.get("conflicts", [])
        if conflicts:
            logger.warning(f"Found {len(conflicts)} conflicts between researchers")
            for conflict in conflicts:
                logger.warning(f"  - {conflict}")
        
        logger.info("=== SUPERVISOR COMPLETE ===")
        
        return {
            "pdf_summary": pdf_summary,
            "assigned_tasks": tasks,
            "researcher_results": researcher_results,
            "consolidated_data": consolidated,
            "conflicts": conflicts
        }
    
    def __call__(self, state: SupervisorState) -> SupervisorState:
        """Make supervisor callable."""
        return self.supervise(state)

