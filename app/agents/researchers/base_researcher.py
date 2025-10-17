"""
Base researcher agent with RAG retrieval capabilities.

All specialized researchers (storm, sanitary, water, elevation, legend) inherit from this.
"""
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.models import ResearcherState
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class BaseResearcher:
    """
    Base class for all specialized researchers.
    
    Each researcher:
    1. Receives a task from the supervisor
    2. Retrieves relevant construction standards via RAG
    3. Analyzes the task using LLM with retrieved context
    4. Returns findings with confidence score
    """
    
    def __init__(
        self,
        researcher_name: str,
        discipline: str = None,
        specialty: str = ""
    ):
        """
        Initialize researcher.
        
        Args:
            researcher_name: Name of this researcher (e.g., "storm", "elevation")
            discipline: Optional discipline filter for RAG (storm/sanitary/water)
            specialty: Description of researcher's specialty
        """
        self.researcher_name = researcher_name
        self.discipline = discipline
        self.specialty = specialty
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )
        
        # Initialize retriever
        self.retriever = HybridRetriever()
        
        logger.info(f"Initialized {researcher_name} researcher: {specialty}")
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this researcher.
        
        Override in subclasses to customize.
        """
        return f"""You are a specialized construction takeoff researcher focusing on {self.specialty}.

Your role:
- Analyze construction PDFs for specific information related to your specialty
- Use the provided construction standards to validate your findings
- Provide accurate, confident assessments based on evidence
- Flag any uncertainties or conflicts

Be precise, cite standards when relevant, and always include confidence scores."""
    
    def retrieve_context(
        self,
        query: str,
        k: int = 5,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant construction standards.
        
        Args:
            query: Search query
            k: Number of results
            category: Optional category filter
        
        Returns:
            List of retrieved documents with metadata
        """
        logger.info(
            f"[{self.researcher_name}] Retrieving context for: '{query}'"
        )
        
        results = self.retriever.retrieve_hybrid(
            query=query,
            k=k,
            discipline=self.discipline,
            category=category
        )
        
        logger.info(
            f"[{self.researcher_name}] Retrieved {len(results)} standards"
        )
        
        return results
    
    def format_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for LLM prompt."""
        if not retrieved_docs:
            return "No relevant construction standards found."
        
        formatted = "Relevant Construction Standards:\n\n"
        for i, doc in enumerate(retrieved_docs, 1):
            formatted += f"{i}. {doc['content']}\n"
            formatted += f"   Source: {doc['metadata']['source']}"
            if doc['metadata'].get('reference'):
                formatted += f" - {doc['metadata']['reference']}"
            formatted += "\n\n"
        
        return formatted
    
    def analyze(self, state: ResearcherState) -> ResearcherState:
        """
        Main analysis method - override in subclasses for specialized behavior.
        
        Args:
            state: Current researcher state with task
        
        Returns:
            Updated state with findings
        """
        task = state["task"]
        
        logger.info(f"[{self.researcher_name}] Starting analysis: {task}")
        
        # 1. Retrieve relevant context
        retrieved_docs = self.retrieve_context(task)
        context_text = self.format_context(retrieved_docs)
        
        # 2. Analyze with LLM
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Task: {task}

{context_text}

Provide your findings in JSON format:
{{
    "summary": "Brief summary of findings",
    "details": {{}},  // Specific data found
    "confidence": 0.0-1.0,
    "issues": [],  // Any problems or conflicts
    "context_used": []  // Which standards were most relevant
}}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            # Use raw text response - no JSON parsing needed!
            findings_text = response.content
            
            # Simple confidence estimation based on response quality
            confidence = 0.7 if len(findings_text) > 100 else 0.5
            
            logger.info(
                f"[{self.researcher_name}] Analysis complete. "
                f"Response length: {len(findings_text)} chars"
            )
            
            # Return updated state with text findings
            return {
                "researcher_name": self.researcher_name,
                "task": task,
                "retrieved_context": [doc["content"] for doc in retrieved_docs],
                "findings": {
                    "analysis": findings_text,
                    "retrieved_standards_count": len(retrieved_docs)
                },
                "confidence": confidence
            }
        
        except Exception as e:
            logger.error(f"[{self.researcher_name}] Analysis failed: {e}")
            return {
                "researcher_name": self.researcher_name,
                "task": task,
                "retrieved_context": [],
                "findings": {"error": str(e), "analysis": ""},
                "confidence": 0.0
            }
    
    def __call__(self, state: ResearcherState) -> ResearcherState:
        """Make researcher callable."""
        return self.analyze(state)

