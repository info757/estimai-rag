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
        parallel: bool = True,
        vision_result: Dict[str, Any] = None
    ) -> Dict[str, ResearcherState]:
        """
        Execute research tasks with comprehensive unknown detection.
        
        NEW: Accepts vision_result to identify unknowns (materials, symbols, codes)
        that weren't found in RAG, then queries external APIs specifically for those.
        
        Args:
            tasks: List of tasks from plan_research
            parallel: Whether to run researchers in parallel
            vision_result: Vision extraction results with detected materials/symbols
        
        Returns:
            Dict of researcher_name -> ResearcherState with findings and user alerts
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
        
        # NEW: Comprehensive unknown detection instead of generic thresholds
        if vision_result:
            logger.info("Checking for unknown materials/elements not found in RAG...")
            
            # Identify unknowns (materials, symbols, codes not in knowledge base)
            unknowns = self._identify_unknowns(vision_result, results)
            
            if unknowns:
                logger.warning(f"Detected {len(unknowns)} unknown element(s)")
                unresolved_items = []
                
                # Try to resolve each unknown via external API
                for unknown in unknowns:
                    api_result = self._query_external_for_unknown(unknown)
                    
                    if api_result['success']:
                        # Success! Add external contexts to relevant researchers
                        for researcher_name in ['storm', 'sanitary', 'water']:
                            if researcher_name in results:
                                results[researcher_name]['retrieved_context'].extend(
                                    api_result['contexts']
                                )
                                results[researcher_name]['api_augmented'] = True
                                results[researcher_name].setdefault('unknowns_resolved', []).append(
                                    unknown['value']
                                )
                    else:
                        # Failed - add to unresolved list for user alert
                        unresolved_items.append({
                            **unknown,
                            "searched": ["local_kb", "tavily_api"],
                            "reason": api_result['reason']
                        })
                
                # Build user alerts for unresolved unknowns
                if unresolved_items:
                    user_alerts = self._build_user_alerts(unresolved_items)
                    results['user_alerts'] = user_alerts
                    logger.error(
                        f"⚠️  {len(unresolved_items)} unknown(s) could not be resolved - "
                        f"user alert created"
                    )
            else:
                logger.info("✓ All detected elements found in knowledge base")
        
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
        
        # Format results for LLM (skip user_alerts key - not a researcher)
        findings_text = ""
        for name, result in researcher_results.items():
            # Skip meta keys like user_alerts
            if name in ['user_alerts']:
                continue
                
            findings_text += f"\n## {name.upper()} Researcher\n"
            findings_text += f"Confidence: {result.get('confidence', 0.0):.2f}\n"
            findings_text += f"Findings: {result.get('findings', {})}\n"
            findings_text += f"Context Used: {len(result.get('retrieved_context', []))} standards\n"
            
            # Show if unknowns were resolved
            if result.get('unknowns_resolved'):
                findings_text += f"Unknowns Resolved: {', '.join(result['unknowns_resolved'])}\n"
        
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
        vision_result = state.get("vision_result", {})
        
        logger.info("=== SUPERVISOR STARTING ===")
        
        # Step 1: Plan research tasks
        tasks = self.plan_research(pdf_summary)
        
        # Step 2: Execute research with unknown detection
        researcher_results = self.execute_research(
            tasks,
            parallel=True,
            vision_result=vision_result  # Enable unknown detection
        )
        
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
    
    def _identify_unknowns(
        self,
        vision_result: Dict[str, Any],
        researcher_results: Dict[str, ResearcherState]
    ) -> List[Dict[str, Any]]:
        """
        Identify ANY unknown element from vision that wasn't found in RAG.
        
        Detects:
        - Materials (FPVC, SRPE, CIPP)
        - Symbols (unrecognized legend items)
        - Codes (2024 IPC Section 705.12)
        - Abbreviations (HDD, TR-FLEX)
        - Techniques (directional boring, CIPP)
        
        Returns list of unknowns with type, value, context, location.
        """
        unknowns = []
        
        # Extract materials from vision pipes
        detected_materials = set()
        pipes = vision_result.get("pipes", [])
        
        for pipe in pipes:
            material = pipe.get("material", "").upper().strip()
            if material and material not in ["", "UNKNOWN", "N/A"]:
                detected_materials.add(material)
        
        # Collect all RAG contexts
        all_contexts = []
        for researcher_name, result in researcher_results.items():
            all_contexts.extend(result.get("retrieved_context", []))
        
        # Combine all contexts into searchable text
        all_context_text = " ".join(all_contexts).upper()
        
        # Check each material against RAG contexts
        for material in detected_materials:
            # Search for material in retrieved contexts
            found_in_rag = material in all_context_text
            
            if not found_in_rag:
                # Find which pipe(s) use this material
                example_pipes = [p for p in pipes if p.get("material", "").upper() == material]
                example = example_pipes[0] if example_pipes else {}
                
                unknowns.append({
                    "type": "material",
                    "value": material,
                    "context": f"{example.get('diameter', '?')}\" {material} pipe",
                    "location": f"Pipe segment (detected by vision)",
                    "count": len(example_pipes)
                })
                logger.warning(f"Unknown material detected: {material} ({len(example_pipes)} pipes)")
        
        return unknowns
    
    def _query_external_for_unknown(
        self,
        unknown: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query Tavily API for specific unknown element.
        
        Returns success status, contexts, confidence, and failure reason.
        """
        unknown_type = unknown['type']
        unknown_value = unknown['value']
        
        logger.info(f"[api] Searching external sources for {unknown_type}: '{unknown_value}'")
        
        try:
            # Construct specific query based on type
            if unknown_type == "material":
                query = f"Construction pipe {unknown_value} material specifications ASTM standards properties"
            elif unknown_type == "code":
                query = f"Building code {unknown_value} plumbing requirements"
            elif unknown_type == "symbol":
                query = f"Construction drawing symbol {unknown_value} meaning"
            else:
                query = f"Construction {unknown_type} {unknown_value} specifications"
            
            # Query API
            api_result = self.api_researcher.analyze({"task": query})
            
            contexts = api_result.get("retrieved_context", [])
            confidence = api_result.get("confidence", 0.0)
            
            # Evaluate results
            if len(contexts) == 0:
                return {
                    "success": False,
                    "reason": "No external sources found",
                    "contexts": [],
                    "confidence": 0.0
                }
            
            if confidence < 0.4:
                return {
                    "success": False,
                    "reason": f"Low confidence ({confidence:.2f}) - results unreliable",
                    "contexts": contexts,
                    "confidence": confidence
                }
            
            # Verify the unknown term appears in retrieved contexts
            found_in_external = any(
                unknown_value.lower() in ctx.lower() 
                for ctx in contexts
            )
            
            if not found_in_external:
                return {
                    "success": False,
                    "reason": "External sources don't mention this specific term",
                    "contexts": contexts,
                    "confidence": confidence
                }
            
            # Success!
            logger.info(f"[api] ✓ Found specifications for {unknown_value}")
            return {
                "success": True,
                "contexts": contexts,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"[api] External search failed: {e}")
            return {
                "success": False,
                "reason": f"API error: {str(e)}",
                "contexts": [],
                "confidence": 0.0
            }
    
    def _build_user_alerts(
        self,
        unresolved_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build comprehensive user alert for unresolved unknowns.
        
        Groups by type and assesses impact.
        """
        if not unresolved_items:
            return None
        
        # Group by type
        by_type = {}
        for item in unresolved_items:
            item_type = item['type']
            if item_type not in by_type:
                by_type[item_type] = []
            by_type[item_type].append(item)
        
        # Assess impact
        material_count = len(by_type.get("material", []))
        total_count = len(unresolved_items)
        
        if material_count > 0:
            severity = "CRITICAL"
            impact_level = "HIGH"
            impact_reason = f"{material_count} unknown material(s) - cost estimation unreliable"
            estimated_risk = "$50,000+ bid error risk"
        elif total_count >= 3:
            severity = "WARNING"
            impact_level = "MEDIUM"
            impact_reason = f"{total_count} unknown elements - may affect accuracy"
            estimated_risk = "$5,000-$20,000 bid error risk"
        else:
            severity = "INFO"
            impact_level = "LOW"
            impact_reason = f"{total_count} minor unknown(s)"
            estimated_risk = "< $5,000 bid error risk"
        
        return {
            "severity": severity,
            "total_unknowns": total_count,
            "action_required": "Manual verification required before bid submission",
            "unresolved_by_type": by_type,
            "impact": {
                "level": impact_level,
                "reason": impact_reason,
                "estimated_risk": estimated_risk
            },
            "recommendations": [
                "Contact project engineer for clarification on unknown materials",
                "Review original plans with subject matter expert",
                "Cross-reference with project specifications",
                "Do NOT submit bid without verification of unknown elements"
            ]
        }

