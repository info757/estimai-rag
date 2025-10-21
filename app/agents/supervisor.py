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
        
        # Initialize API researcher for unknown material augmentation
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
            SystemMessage(content="""You are a construction estimating supervisor that leads a team of construction estimators, each with expertise in specific areas of performing takeoff on construction documents. 

Your expertise is in deciding which researcher/estimator should perform takeoff on each part of the construction blueprint documents, vector and raster construction pdfs."""),
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
                        "findings": {}
                    }
                    
                    # Submit task
                    future = executor.submit(researcher.analyze, state)
                    futures[researcher_name] = future
                
                # Collect results
                for researcher_name, future in futures.items():
                    try:
                        result = future.result(timeout=120)  # 2 minute timeout per researcher
                        results[researcher_name] = result
                        logger.info(f"[{researcher_name}] Complete.")
                    except Exception as e:
                        logger.error(f"[{researcher_name}] Failed: {e}")
                        results[researcher_name] = {
                            "researcher_name": researcher_name,
                            "task": task_spec["task"],
                            "retrieved_context": [],
                            "findings": {"error": str(e)}
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
                    "findings": {}
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
                        "findings": {"error": str(e)}
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
        researcher_results: Dict[str, ResearcherState],
        vision_pipes: list = None
    ) -> Dict[str, Any]:
        """
        Consolidate and validate findings from all researchers.
        
        Includes intelligent deduplication of pipes from multiple views.
        
        Args:
            researcher_results: Results from execute_research
            vision_pipes: Raw pipe list from Vision agents (may contain duplicates)
        
        Returns:
            Consolidated takeoff data with deduplicated pipes
        """
        logger.info("Consolidating researcher findings...")
        
        # If we have Vision pipes, add deduplication step
        if vision_pipes:
            logger.info(f"Deduplicating {len(vision_pipes)} Vision detections...")
        
        # Format results for LLM (skip user_alerts key - not a researcher)
        findings_text = ""
        for name, result in researcher_results.items():
            # Skip meta keys like user_alerts, or None keys
            if not name or name in ['user_alerts']:
                continue
                
            findings_text += f"\n## {name.upper()} Researcher\n"
            findings_text += f"Findings: {result.get('findings', {})}\n"
            findings_text += f"Context Used: {len(result.get('retrieved_context', []))} standards\n"
            
            # Show if unknowns were resolved
            if result.get('unknowns_resolved'):
                findings_text += f"Unknowns Resolved: {', '.join(result['unknowns_resolved'])}\n"
        
        # Build Vision pipe summary for deduplication
        vision_summary = ""
        if vision_pipes:
            vision_summary = f"\n## VISION AGENT DETECTIONS ({len(vision_pipes)} pipes, may include duplicates)\n\n"
            for i, p in enumerate(vision_pipes, 1):
                vision_summary += f"{i}. {p.get('discipline', '?')} - {p.get('diameter_in', '?')}\" {p.get('material', '?')} - {p.get('length_ft', '?')} LF"
                if p.get('from_structure'):
                    vision_summary += f" (from {p.get('from_structure')} to {p.get('to_structure')})"
                vision_summary += f" [source: {p.get('source', '?')}]\n"
        
        prompt = f"""You are an expert at reading construction blueprint documents and vector and raster pdfs.

{vision_summary}

{findings_text}

If you see a construction item like a pipe with the same label more than once then don't count it multiple times. It is simply a construction item being referenced again from a different view or perhaps giving us more information about it. Analyze for new, important information but do not count it again when you see it has the same naming convention you already saw and counted.

Calculate total unique pipes by type and their total lengths.

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
    "materials_found": [],
    "overall_confidence": 0.0-1.0,
    "recommendations": ""
}}"""
        
        messages = [
            SystemMessage(content="You are a construction takeoff supervisor consolidating researcher findings."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            consolidation_text = response.content
            
            # Try to parse JSON from LLM response (for deduplication results)
            import re
            import json
            
            json_match = re.search(r'\{.*\}', consolidation_text, re.DOTALL)
            if json_match:
                try:
                    llm_result = json.loads(json_match.group())
                    logger.info(f"✅ Supervisor parsed deduplication result")
                    
                    # Use LLM's deduplicated counts
                    consolidated = {
                        "summary": llm_result.get("summary", {}),
                        "consolidation_analysis": consolidation_text,
                        "deduplication_notes": llm_result.get("deduplication_notes", ""),
                        "materials_found": llm_result.get("materials_found", []),
                        "diameters_found": llm_result.get("diameters_found", []),
                        "elevations_extracted": llm_result.get("elevations_extracted", False),
                        "conflicts": llm_result.get("conflicts", []),
                        "validation_issues": llm_result.get("validation_issues", []),
                        "recommendations": llm_result.get("recommendations", "")
                    }
                    
                    logger.info(
                        f"Consolidation complete. Deduplicated: {consolidated['summary'].get('total_pipes', 0)} unique pipes."
                    )
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Supervisor JSON, using fallback")
                    consolidated = self._fallback_consolidation(researcher_results, consolidation_text)
            else:
                logger.warning("No JSON found in Supervisor response, using fallback")
                consolidated = self._fallback_consolidation(researcher_results, consolidation_text)
            
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
                "validation_issues": ["Consolidation failed"],
                "recommendations": "Manual review required"
            }
    
    def _deduplicate_vision_only(self, vision_pipes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deduplicate Vision pipes WITHOUT researcher input.
        
        Vision is single source of truth. This method only removes duplicates
        from multi-page/multi-view scenarios using LLM-based intelligent deduplication.
        
        Args:
            vision_pipes: List of pipes detected by Vision
        
        Returns:
            Consolidated result with deduplicated pipes
        """
        if not vision_pipes:
            return {
                "summary": {
                    "total_pipes": 0,
                    "storm_pipes": 0,
                    "sanitary_pipes": 0,
                    "water_pipes": 0,
                    "storm_lf": 0.0,
                    "sanitary_lf": 0.0,
                    "water_lf": 0.0,
                    "total_lf": 0.0
                },
                "materials_found": [],
                "validation_issues": [],
                "recommendations": ""
            }
        
        # Use LLM to deduplicate (same prompt as consolidate_findings)
        vision_summary = f"Vision detected {len(vision_pipes)} pipes from construction document."
        
        prompt = f"""You are an expert at reading construction blueprint documents and vector and raster pdfs.

{vision_summary}

Vision Detections:
{self._format_pipes_for_llm(vision_pipes)}

If you see a construction item like a pipe with the same label more than once then don't count it multiple times. It is simply a construction item being referenced again from a different view or perhaps giving us more information about it. Analyze for new, important information but do not count it again when you see it has the same naming convention you already saw and counted.

Calculate the total unique pipes by type and their total lengths.

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
    "materials_found": [],
    "recommendations": ""
}}"""

        try:
            messages = [
                SystemMessage(content="You are an expert construction estimator."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            import json
            import re
            
            content = response.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                consolidated = json.loads(json_match.group())
                logger.info("✅ Supervisor parsed deduplication result")
                return consolidated
            else:
                raise ValueError("No JSON found in response")
        
        except Exception as e:
            logger.warning(f"LLM deduplication failed ({e}), using fallback count")
            # Fallback: naive count (no deduplication)
            storm_count = sum(1 for p in vision_pipes if p.get("discipline") == "storm")
            sanitary_count = sum(1 for p in vision_pipes if p.get("discipline") == "sanitary")
            water_count = sum(1 for p in vision_pipes if p.get("discipline") == "water")
            
            return {
                "summary": {
                    "storm_pipes": storm_count,
                    "sanitary_pipes": sanitary_count,
                    "water_pipes": water_count,
                    "total_pipes": len(vision_pipes),
                    "storm_lf": sum(p.get("length_ft", 0) for p in vision_pipes if p.get("discipline") == "storm"),
                    "sanitary_lf": sum(p.get("length_ft", 0) for p in vision_pipes if p.get("discipline") == "sanitary"),
                    "water_lf": sum(p.get("length_ft", 0) for p in vision_pipes if p.get("discipline") == "water"),
                    "total_lf": sum(p.get("length_ft", 0) for p in vision_pipes)
                },
                "materials_found": list(set(p.get("material", "") for p in vision_pipes)),
                "validation_issues": ["LLM deduplication failed - using naive count"],
                "recommendations": ""
            }
    
    def _format_pipes_for_llm(self, pipes: List[Dict[str, Any]]) -> str:
        """Format pipes for LLM prompt."""
        formatted = []
        for i, pipe in enumerate(pipes, 1):
            formatted.append(
                f"{i}. {pipe.get('discipline', 'unknown')} - "
                f"{pipe.get('diameter_in', '?')}\" {pipe.get('material', '?')} - "
                f"{pipe.get('length_ft', 0)} LF"
            )
        return "\n".join(formatted)
    
    def _fallback_consolidation(
        self,
        researcher_results: Dict[str, ResearcherState],
        consolidation_text: str
    ) -> Dict[str, Any]:
        """Fallback when LLM doesn't return valid JSON."""
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
            "consolidation_analysis": consolidation_text,
            "deduplication_notes": "Deduplication failed - counts may include duplicates",
            "materials_found": [],
            "diameters_found": [],
            "elevations_extracted": False,
            "conflicts": [],
            "validation_issues": ["Consolidation JSON parsing failed"],
            "recommendations": "Manual review required"
        }
    
    def _looks_like_abbreviation(self, material: str) -> bool:
        """
        Check if material looks like an abbreviation that needs legend decoding.
        
        Edge cases handled:
        - Single char abbreviations (C, I, V) - included
        - Mixed case (Pvc, PVC, pvc) - ALL included (drawing standards vary)
        - Multi-word materials (Ductile Iron) - excluded
        - Very long strings (Polyethylene) - excluded
        - Numeric-only strings (12, 24) - excluded
        
        Philosophy: Better to over-ask the Legend Researcher than miss an abbreviation.
        If it's not in the legend, Legend Researcher returns nothing (no harm done).
        """
        if not material:
            return False
        
        material_core = material.strip()
        
        # Exclude multi-word materials (already expanded)
        if ' ' in material_core:
            return False  # "Ductile Iron" is not an abbreviation
        
        # Exclude very long strings (not abbreviations)
        if len(material_core) > 6:
            return False  # "Polyethylene" is not an abbreviation
        
        # Exclude purely numeric strings
        if material_core.isdigit():
            return False  # "12" is not a material abbreviation
        
        # Include anything 1-6 chars with letters (regardless of case)
        return any(c.isalpha() for c in material_core)
        # Includes: "FPVC", "Pvc", "C", "DI", "pvc", "RCP"
    
    def validate_and_enrich(self, state: SupervisorState) -> SupervisorState:
        """
        Vision-First validation workflow - NO extraction, only validation.
        
        Vision is the single source of truth for counts.
        Researchers are ONLY used to validate unknown materials via RAG.
        
        Args:
            state: SupervisorState with PDF summary and Vision results
        
        Returns:
            Updated state with validated, deduplicated Vision pipes
        """
        pdf_summary = state["pdf_summary"]
        vision_result = state.get("vision_result", {})
        vision_pipes = vision_result.get("pipes", []) if vision_result else []
        
        logger.info("=== SUPERVISOR STARTING (VALIDATION MODE) ===")
        logger.info(f"Vision provided {len(vision_pipes)} pipes (source of truth)")
        
        # Step 1: Extract unique materials from Vision pipes
        logger.info("Checking materials against RAG knowledge base...")
        unique_materials = set()
        for pipe in vision_pipes:
            material = (pipe.get("material") or "").strip().upper()
            if material and material not in ["", "UNKNOWN", "N/A"]:
                unique_materials.add(material)
        
        logger.info(f"Found {len(unique_materials)} unique materials: {', '.join(sorted(unique_materials))}")
        
        # Step 1.5: NEW - Decode abbreviations using legend (Vision or text extraction)
        logger.info("Attempting to decode abbreviations from PDF legend...")
        abbreviations = {}  # Maps abbreviation -> full name
        
        # Try Vision-extracted legend first
        vision_legend = vision_result.get("legend", {})
        if vision_legend:
            logger.info(f"Vision extracted legend with {len(vision_legend)} entries")
            for material in unique_materials:
                if self._looks_like_abbreviation(material):
                    decoded = vision_legend.get(material)
                    if not decoded:
                        for abbrev, full_name in vision_legend.items():
                            if abbrev.upper() == material.upper():
                                decoded = full_name
                                break
                    if decoded:
                        abbreviations[material] = decoded
                        logger.info(f"📖 Vision legend: {material} → {decoded}")
        
        # Fallback: Extract legend directly from PDF text (if Vision didn't extract it)
        if not abbreviations and state.get("pdf_path"):
            logger.info("Attempting text-based legend extraction from PDF file...")
            try:
                import fitz  # PyMuPDF
                import re
                
                pdf_path = state.get("pdf_path")
                doc = fitz.open(pdf_path)
                pdf_text = ""
                # Extract text from first 2 pages (legend usually on page 1)
                for page_num in range(min(2, len(doc))):
                    pdf_text += doc[page_num].get_text()
                doc.close()
                
                # Look for patterns like "FPVC = Fabric-Reinforced PVC Pipe"
                legend_pattern = r'([A-Z]{2,6})\s*=\s*([^(\n]+?)(?:\s*\(|$|\n)'
                matches = re.findall(legend_pattern, pdf_text)
                if matches:
                    logger.info(f"Found {len(matches)} legend entries via text extraction")
                    for abbrev, full_name in matches:
                        abbrev_clean = abbrev.strip().upper()
                        full_name_clean = full_name.strip()
                        if abbrev_clean in unique_materials:
                            abbreviations[abbrev_clean] = full_name_clean
                            logger.info(f"📖 Text legend: {abbrev_clean} → {full_name_clean}")
            except Exception as e:
                logger.warning(f"Text-based legend extraction failed: {e}")
        
        if not abbreviations:
            logger.info("No abbreviations decoded (either no legend or no abbreviations needed decoding)")
        
        # Step 2: Query RAG for each material to validate (use decoded names if available)
        from app.rag.retriever import HybridRetriever
        retriever = HybridRetriever()
        
        known_materials = set()
        unknown_materials = set()
        researcher_results = {}
        
        for material in unique_materials:
            # Use decoded material name if available, otherwise use original
            search_name = abbreviations.get(material, material)
            search_query = f"{search_name} pipe material specifications"
            
            if material in abbreviations:
                logger.info(f"Searching RAG for '{material}' using decoded name '{search_name}'")
            
            # Query RAG for material specs
            rag_results = retriever.retrieve_hybrid(
                query=search_query,
                k=5,
                discipline=None
            )
            
            # Check if material is ACTUALLY mentioned in retrieved content
            # Not just "did we get generic pipe results?"
            material_found_in_content = False
            if rag_results:
                for result in rag_results:
                    content = result.get('content', '').upper()
                    # Check if either the abbreviation OR decoded name appears in content
                    search_terms = [material.upper()]
                    if material in abbreviations:
                        search_terms.append(abbreviations[material].upper())
                    
                    if any(term in content for term in search_terms):
                        material_found_in_content = True
                        break
            
            if material_found_in_content:
                known_materials.add(material)
                if material in abbreviations:
                    logger.info(f"✓ {material} ({abbreviations[material]}): Found in knowledge base via legend decoding!")
                else:
                    logger.info(f"✓ {material}: Found in knowledge base (explicitly mentioned in standards)")
            else:
                unknown_materials.add(material)
                if material in abbreviations:
                    logger.warning(f"⚠️  {material} ({abbreviations[material]}): NOT in knowledge base even after legend decoding")
                else:
                    logger.warning(f"⚠️  {material}: NOT in knowledge base (material not mentioned in any standard)")
                
                # Try to resolve via Tavily API
                tavily_search = abbreviations.get(material, material)
                logger.info(f"[api] Searching external sources for material: '{tavily_search}'")
                api_result = self.api_researcher.analyze(
                    state={"task": f"Construction pipe {tavily_search} material specifications ASTM standards"}
                )
                researcher_results[f"api_{material}"] = {
                    "researcher_name": "api",
                    "task": f"Research {material} material",
                    "findings": api_result.get("findings", {}),
                    "retrieved_context": api_result.get("retrieved_context", [])
                }
        
        # Summary
        if unknown_materials:
            logger.error(f"⚠️  {len(unknown_materials)} unknown material(s) could not be validated: {', '.join(sorted(unknown_materials))}")
        else:
            logger.info("✓ All detected materials found in knowledge base")
        
        # Step 3: Deduplicate Vision pipes (same logic as before)
        logger.info("Consolidating researcher findings...")
        logger.info(f"Deduplicating {len(vision_pipes)} Vision detections...")
        
        consolidated = self._deduplicate_vision_only(vision_pipes)
        
        # Add unknown alerts (include decoded names for better UX)
        if unknown_materials:
            # Format unknown materials with decoded names if available
            formatted_unknowns = []
            for mat in sorted(unknown_materials):
                if mat in abbreviations:
                    formatted_unknowns.append(f"{mat} ({abbreviations[mat]})")
                else:
                    formatted_unknowns.append(mat)
            
            consolidated["user_alerts"] = {
                "severity": "CRITICAL" if len(unknown_materials) > 2 else "WARNING",
                "message": f"{len(unknown_materials)} unknown materials detected: {', '.join(formatted_unknowns)}",
                "unknown_materials": list(unknown_materials),
                "decoded_materials": {mat: abbreviations.get(mat, mat) for mat in unknown_materials}
            }
        
        logger.info(f"Consolidation complete. Deduplicated: {consolidated['summary']['total_pipes']} unique pipes.")
        logger.info("=== SUPERVISOR COMPLETE ===")
        
        return {
            "pdf_summary": pdf_summary,
            "assigned_tasks": [],  # No extraction tasks
            "researcher_results": researcher_results,
            "consolidated_data": consolidated,
            "conflicts": []  # No conflicts since Vision is single source
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
        
        # Step 3: Consolidate findings (with Vision pipes for deduplication)
        vision_pipes = vision_result.get("pipes", []) if vision_result else []
        consolidated = self.consolidate_findings(
            researcher_results,
            vision_pipes=vision_pipes
        )
        
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
            material = (pipe.get("material") or "").strip().upper()
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
                example_pipes = [p for p in pipes if (p.get("material") or "").upper() == material]
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
        
        Returns success status, contexts, and failure reason.
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
                    "contexts": contexts
                }
            
            # Success!
            logger.info(f"[api] ✓ Found specifications for {unknown_value}")
            return {
                "success": True,
                "contexts": contexts
            }
            
        except Exception as e:
            logger.error(f"[api] External search failed: {e}")
            return {
                "success": False,
                "reason": f"API error: {str(e)}",
                "contexts": []
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

