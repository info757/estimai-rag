"""
Main Agent - orchestrates the entire takeoff workflow with LangGraph.

Flow:
1. Analyze PDF → understand what's in it
2. Call Supervisor → deploy researchers, get findings
3. Generate Report → create final takeoff
"""
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END

from app.models import AgentState, SupervisorState, TakeoffResult, TakeoffSummary, PipeDetection
from app.agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


class MainAgent:
    """
    Main coordinator agent using LangGraph.
    
    Creates a state graph that orchestrates the entire takeoff process.
    """
    
    def __init__(self):
        """Initialize main agent."""
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Use more powerful model for coordination
            temperature=0
        )
        
        self.supervisor = SupervisorAgent()
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        logger.info("Main Agent initialized with LangGraph workflow")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_pdf", self.analyze_pdf_node)
        workflow.add_node("supervise_research", self.supervise_research_node)
        workflow.add_node("generate_report", self.generate_report_node)
        
        # Define edges
        workflow.set_entry_point("analyze_pdf")
        workflow.add_edge("analyze_pdf", "supervise_research")
        workflow.add_edge("supervise_research", "generate_report")
        workflow.add_edge("generate_report", END)
        
        logger.info("LangGraph workflow built")
        
        return workflow.compile()
    
    def analyze_pdf_node(self, state: AgentState) -> AgentState:
        """
        Node 1: Analyze the PDF to understand its content.
        
        This uses GPT-4o Vision to understand what's in the PDF and
        extract initial pipe information.
        """
        pdf_path = state["pdf_path"]
        user_query = state.get("user_query", "")
        
        logger.info(f"[Main Agent] Analyzing PDF: {pdf_path}")
        
        try:
            # Use Vision Coordinator with specialized agents
            from app.vision.coordinator import VisionCoordinator
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # Create coordinator
            coordinator = VisionCoordinator()
            
            # Run async code in a separate thread to avoid event loop conflicts
            def run_vision_async():
                """Helper to run async Vision coordinator in new event loop."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coordinator.analyze_multipage(
                        pdf_path=pdf_path,
                        max_pages=None,  # Process all pages (was 10)
                        agents_to_deploy=["pipes", "grading"],  # Deploy both pipes and grading agents
                        dpi=300  # High resolution
                    ))
                finally:
                    new_loop.close()
            
            # Execute in thread pool
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_vision_async)
                vision_results = future.result()
            
            logger.info(f"[Main Agent] Vision analysis complete. Raw extraction: {len(vision_results.get('pipes', []))} pipes")
            
            pipes_found = vision_results.get("total_pipes", 0)
            pages_processed = vision_results.get("num_pages_processed", 0)
            discipline_counts = vision_results.get("discipline_counts", {})
            
            # Create summary for supervisor
            pdf_summary = f"""PDF Analysis Results:
- Pages processed: {pages_processed}
- Total pipes detected (raw): {pipes_found}
- Vision analysis: GPT-4o pipe extraction
- Page summaries: {' | '.join(vision_results.get('page_summaries', []))}

Pipe breakdown:
"""
            for disc, count in discipline_counts.items():
                pdf_summary += f"- {disc}: {count} pipes\n"
            
            if user_query:
                pdf_summary += f"\nUser request: {user_query}"
            
            logger.info(f"[Main Agent] PDF analysis complete: {pipes_found} pipes found")
            logger.info(f"Summary: {pdf_summary[:300]}...")
            
            # Store vision results in state for later use
            return {
                **state,
                "pdf_summary": pdf_summary,
                "final_report": {
                    "vision_results": vision_results
                },
                "messages": state.get("messages", [])
            }
        
        except Exception as e:
            logger.error(f"[Main Agent] PDF analysis failed: {e}")
            logger.error(f"[Main Agent] Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"[Main Agent] Full traceback:")
            traceback.print_exc()
            
            # Fallback: basic summary
            return {
                **state,
                "pdf_summary": f"PDF: {pdf_path}. Analysis failed: {e}. Deploying all researchers.",
                "messages": state.get("messages", [])
            }
    
    def supervise_research_node(self, state: AgentState) -> AgentState:
        """
        Node 2: Call supervisor to validate Vision results (NO extraction).
        
        Vision is single source of truth for pipe counts.
        Supervisor only validates unknowns via RAG and deduplicates.
        """
        pdf_summary = state["pdf_summary"]
        
        logger.info("[Main Agent] Calling supervisor (validation mode)...")
        
        # Create supervisor state (with vision_result for unknown detection)
        vision_result = state.get("final_report", {}).get("vision_results", {})
        
        supervisor_state: SupervisorState = {
            "pdf_summary": pdf_summary,
            "assigned_tasks": [],
            "researcher_results": {},
            "consolidated_data": {},
            "conflicts": [],
            "vision_result": vision_result,  # Pass for validation and deduplication
            "pdf_path": state.get("pdf_path")  # NEW: For legend extraction
        }
        
        # Run supervisor in VALIDATION-ONLY mode (no extraction)
        result = self.supervisor.validate_and_enrich(supervisor_state)
        
        logger.info(
            f"[Main Agent] Supervisor complete. "
            f"Found {result['consolidated_data'].get('summary', {}).get('total_pipes', 0)} pipes"
        )
        
        # Update state with supervisor results (preserve vision_results!)
        return {
            **state,
            "final_report": {
                **state.get("final_report", {}),  # Preserve existing data like vision_results
                "supervisor_tasks": result["assigned_tasks"],
                "researcher_results": result["researcher_results"],
                "consolidated_data": result["consolidated_data"],
                "conflicts": result["conflicts"]
            }
        }
    
    def generate_report_node(self, state: AgentState) -> AgentState:
        """
        Node 3: Generate final takeoff report.
        
        Uses vision results + researcher RAG validation.
        """
        logger.info("[Main Agent] Generating final report...")
        
        # Get vision results (actual pipe data)
        vision_results = state["final_report"].get("vision_results", {})
        vision_pipes = vision_results.get("pipes", [])
        
        # Get researcher results (RAG validation)
        researcher_results = state["final_report"].get("researcher_results", {})
        consolidated = state["final_report"].get("consolidated_data", {})
        
        # Trust Supervisor's deduplicated summary
        supervisor_summary = consolidated["summary"]
        
        # Initial summary (will be updated with volumes after calculation)
        summary = TakeoffSummary(
            total_pipes=supervisor_summary["total_pipes"],
            storm_pipes=supervisor_summary["storm_pipes"],
            sanitary_pipes=supervisor_summary["sanitary_pipes"],
            water_pipes=supervisor_summary["water_pipes"],
            storm_lf=supervisor_summary["storm_lf"],
            sanitary_lf=supervisor_summary["sanitary_lf"],
            water_lf=supervisor_summary["water_lf"],
            total_lf=supervisor_summary["total_lf"],
            total_excavation_cy=0.0,  # Will be updated
            total_bedding_cy=0.0,  # Will be updated
            total_backfill_cy=0.0,  # Will be updated
            estimated_truck_loads=0,  # Will be updated
            validation_flags_count=0
        )
        
        # Convert vision pipes to PipeDetection format + calculate volumes
        from app.models import PipeDetection
        from app.calculations.earthwork import TrenchCalculator, calculate_project_totals
        
        pipes = []
        for i, vp in enumerate(vision_pipes):
            # Calculate volumes for this pipe
            volumes = TrenchCalculator.calculate_from_pipe_data(vp)
            
            pipe = PipeDetection(
                pipe_id=f"pipe_{i}",
                discipline=vp["discipline"],
                material=vp["material"],
                diameter_in=vp["diameter_in"],
                length_ft=vp["length_ft"],
                invert_in_ft=vp.get("invert_in_ft"),
                invert_out_ft=vp.get("invert_out_ft"),
                ground_level_ft=vp.get("ground_level_ft"),
                depth_ft=vp.get("depth_ft"),
                # Add calculated volumes
                excavation_cy=volumes.get("excavation_cy"),
                bedding_cy=volumes.get("bedding_cy"),
                backfill_cy=volumes.get("backfill_cy"),
                compacted_backfill_cy=volumes.get("compacted_backfill_cy"),
                trench_width_ft=volumes.get("trench_width_ft"),
                retrieved_context=[],
                validation_flags=[]
            )
            pipes.append(pipe)
        
        # Calculate project totals
        pipes_dict = [p.model_dump() for p in pipes]
        project_totals = calculate_project_totals(pipes_dict)
        
        # Update summary with volume totals
        summary.total_excavation_cy = project_totals["total_excavation_cy"]
        summary.total_bedding_cy = project_totals["total_bedding_cy"]
        summary.total_backfill_cy = project_totals["total_backfill_cy"]
        summary.estimated_truck_loads = project_totals["estimated_truck_loads"]
        
        # Build TakeoffResult
        result = TakeoffResult(
            summary=summary,
            pipes=pipes,
            pdf_summary=state["pdf_summary"],
            rag_stats={
                "researchers_deployed": len(researcher_results),
                "total_standards_retrieved": sum(
                    len(r.get("retrieved_context", []))
                    for r in researcher_results.values()
                ),
                "conflicts_found": len(state["final_report"].get("conflicts", []))
            }
        )
        
        logger.info(
            f"[Main Agent] Report generated: {summary.total_pipes} pipes, "
            f"{summary.total_lf:.1f} LF, "
            f"Excavation: {summary.total_excavation_cy:.1f} CY, "
            f"Bedding: {summary.total_bedding_cy:.1f} CY, "
            f"Backfill: {summary.total_backfill_cy:.1f} CY"
        )
        
        # Update state
        return {
            **state,
            "final_report": {
                **state["final_report"],
                "takeoff_result": result.model_dump()
            }
        }
    
    def run_takeoff(
        self,
        pdf_path: str,
        user_query: str = ""
    ) -> Dict[str, Any]:
        """
        Run the complete takeoff workflow.
        
        Args:
            pdf_path: Path to PDF file
            user_query: Optional user clarification
        
        Returns:
            Final takeoff result
        """
        logger.info("=" * 60)
        logger.info("MAIN AGENT: Starting takeoff workflow")
        logger.info("=" * 60)
        
        # Create initial state
        initial_state: AgentState = {
            "pdf_path": pdf_path,
            "user_query": user_query,
            "pdf_summary": "",
            "final_report": {},
            "messages": []
        }
        
        try:
            # Run the LangGraph workflow
            final_state = self.workflow.invoke(initial_state)
            
            logger.info("=" * 60)
            logger.info("MAIN AGENT: Takeoff workflow complete")
            logger.info("=" * 60)
            
            return final_state["final_report"]
        
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "error": str(e),
                "consolidated_data": {
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
                    "validation_issues": ["Workflow failed"],
                    "recommendations": "Manual takeoff required"
                }
            }


# Convenience function for easy import
def run_takeoff(pdf_path: str, user_query: str = "") -> Dict[str, Any]:
    """
    Run takeoff on a PDF file.
    
    Args:
        pdf_path: Path to PDF
        user_query: Optional clarification
    
    Returns:
        Takeoff results
    """
    agent = MainAgent()
    return agent.run_takeoff(pdf_path, user_query)

