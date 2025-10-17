"""
Main Agent - orchestrates the entire takeoff workflow with LangGraph.

Flow:
1. Analyze PDF → understand what's in it
2. Call Supervisor → deploy researchers, get findings
3. Generate Report → create final takeoff with confidence scores
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
            # Use vision processor to analyze PDF
            from app.vision_processor import process_pdf_with_vision
            
            vision_results = process_pdf_with_vision(pdf_path, max_pages=10)
            
            pipes_found = len(vision_results.get("pipes", []))
            pages_processed = vision_results.get("num_pages_processed", 0)
            
            # Create summary for supervisor
            pdf_summary = f"""PDF Analysis Results:
- Pages processed: {pages_processed}
- Total pipes detected: {pipes_found}
- Page summaries: {' | '.join(vision_results.get('page_summaries', []))}

Pipe breakdown:
"""
            # Count by discipline
            from collections import Counter
            disciplines = [p.get("discipline") for p in vision_results.get("pipes", []) if p.get("discipline")]
            discipline_counts = Counter(disciplines)
            
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
            import traceback
            traceback.print_exc()
            
            # Fallback: basic summary
            return {
                **state,
                "pdf_summary": f"PDF: {pdf_path}. Analysis failed: {e}. Deploying all researchers.",
                "messages": state.get("messages", [])
            }
    
    def supervise_research_node(self, state: AgentState) -> AgentState:
        """
        Node 2: Call supervisor to coordinate researchers.
        """
        pdf_summary = state["pdf_summary"]
        
        logger.info("[Main Agent] Calling supervisor...")
        
        # Create supervisor state
        supervisor_state: SupervisorState = {
            "pdf_summary": pdf_summary,
            "assigned_tasks": [],
            "researcher_results": {},
            "consolidated_data": {},
            "conflicts": []
        }
        
        # Run supervisor
        result = self.supervisor.supervise(supervisor_state)
        
        logger.info(
            f"[Main Agent] Supervisor complete. "
            f"Found {result['consolidated_data'].get('summary', {}).get('total_pipes', 0)} pipes"
        )
        
        # Update state with supervisor results
        return {
            **state,
            "final_report": {
                "supervisor_tasks": result["assigned_tasks"],
                "researcher_results": result["researcher_results"],
                "consolidated_data": result["consolidated_data"],
                "conflicts": result["conflicts"]
            }
        }
    
    def generate_report_node(self, state: AgentState) -> AgentState:
        """
        Node 3: Generate final takeoff report.
        """
        logger.info("[Main Agent] Generating final report...")
        
        consolidated = state["final_report"]["consolidated_data"]
        researcher_results = state["final_report"]["researcher_results"]
        
        # Extract summary
        summary_data = consolidated.get("summary", {})
        
        # Create TakeoffSummary
        summary = TakeoffSummary(
            total_pipes=summary_data.get("total_pipes", 0),
            storm_pipes=summary_data.get("storm_pipes", 0),
            sanitary_pipes=summary_data.get("sanitary_pipes", 0),
            water_pipes=summary_data.get("water_pipes", 0),
            storm_lf=summary_data.get("storm_lf", 0.0),
            sanitary_lf=summary_data.get("sanitary_lf", 0.0),
            water_lf=summary_data.get("water_lf", 0.0),
            total_lf=summary_data.get("total_lf", 0.0),
            avg_confidence=consolidated.get("overall_confidence", 0.0),
            validation_flags_count=len(consolidated.get("validation_issues", []))
        )
        
        # Create placeholder pipes (in real version, extract from researcher findings)
        pipes = []
        
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
            f"{summary.total_lf:.1f} LF, {summary.avg_confidence:.2f} confidence"
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
                    "overall_confidence": 0.0,
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

