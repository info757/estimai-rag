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
        
        This uses GPT-4o Vision to understand what's in the PDF.
        """
        pdf_path = state["pdf_path"]
        user_query = state.get("user_query", "")
        
        logger.info(f"[Main Agent] Analyzing PDF: {pdf_path}")
        
        # In a real implementation, we'd use Vision API
        # For now, simulate with a text prompt
        prompt = f"""Analyze this construction PDF and provide a summary.

PDF Path: {pdf_path}
User Query: {user_query}

Describe what you see:
1. What type of drawing is this? (site plan, profile, detail sheet, combination?)
2. Which utility disciplines are present? (storm, sanitary, water?)
3. Are there elevation labels (inverts, ground levels)?
4. Is there a legend or symbol key?
5. What page(s) contain each type of information?

Provide a concise summary for the supervisor to use when deploying researchers."""
        
        messages = [
            SystemMessage(content="You are a construction drawing analysis expert."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            pdf_summary = response.content
            
            logger.info(f"[Main Agent] PDF analysis complete")
            logger.info(f"Summary: {pdf_summary[:200]}...")
            
            # Update state
            return {
                **state,
                "pdf_summary": pdf_summary,
                "messages": state.get("messages", []) + [response]
            }
        
        except Exception as e:
            logger.error(f"[Main Agent] PDF analysis failed: {e}")
            return {
                **state,
                "pdf_summary": "Analysis failed. Deploying all researchers as fallback.",
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

