"""
API Researcher - Queries external APIs when RAG has insufficient context.

Uses Tavily API for web search on construction standards, materials,
and code requirements not available in the static knowledge base.
"""
import logging
import os
from typing import Dict, Any, List
from tavily import TavilyClient

logger = logging.getLogger(__name__)


class APIResearcher:
    """
    Researcher that queries external APIs for construction knowledge.
    
    Deployed by Supervisor when:
    - RAG retrieves < 3 relevant contexts
    - Unknown materials/codes detected
    """
    
    def __init__(self):
        """Initialize API researcher with Tavily client."""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set in environment")
        
        self.tavily_client = TavilyClient(api_key=api_key)
        self.discipline = "api"
        self.name = "API Knowledge Retrieval"
        
        logger.info("API Researcher initialized with Tavily")
    
    def analyze(self, state: Dict[str, Any], vision_pipes: List[Dict] = None) -> Dict[str, Any]:
        """
        Query external APIs for construction knowledge.
        
        Args:
            state: Research task state with 'task' key
            vision_pipes: Optional pipe data from Vision LLM
        
        Returns:
            Dict with findings and retrieved context
        """
        task = state.get("task", "")
        
        logger.info(f"[api] Searching external sources for: {task[:50]}...")
        
        try:
            # Search with Tavily - focus on construction/engineering domains
            results = self.tavily_client.search(
                query=task,
                search_depth="advanced",
                max_results=5,
                include_domains=["iccsafe.org", "astm.org", "awwa.org", "asce.org"],
                timeout=15
            )
            
            logger.info(f"[api] Found {len(results.get('results', []))} external sources")
            
            # Format results
            external_knowledge = self._format_results(results)
            retrieved_contexts = self._extract_contexts(results)
            
            return {
                "findings": {
                    "analysis": external_knowledge,
                    "source": "external_api",
                    "api_used": "tavily",
                    "results_count": len(retrieved_contexts)
                },
                "retrieved_context": retrieved_contexts,
                "retrieved_standards_count": len(retrieved_contexts)
            }
        
        except Exception as e:
            logger.error(f"[api] API search failed: {e}")
            return {
                "findings": {
                    "analysis": f"External API search failed: {str(e)}",
                    "source": "external_api_error",
                    "api_used": "tavily"
                },
                "retrieved_context": [],
                "retrieved_standards_count": 0
            }
    
    def _format_results(self, results: Dict[str, Any]) -> str:
        """Format Tavily results into analysis text."""
        if not results or "results" not in results:
            return "No external information found."
        
        analysis_parts = []
        
        for i, result in enumerate(results.get("results", [])[:3], 1):
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            url = result.get("url", "")
            
            analysis_parts.append(f"**External Source {i}: {title}**\n{content[:300]}...\n(Source: {url})")
        
        return "\n\n".join(analysis_parts)
    
    def _extract_contexts(self, results: Dict[str, Any]) -> List[str]:
        """Extract context strings from Tavily results."""
        contexts = []
        
        for result in results.get("results", []):
            content = result.get("content", "")
            if content:
                contexts.append(content)
        
        return contexts

