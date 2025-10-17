"""
Advanced multi-query retrieval with query expansion and fusion.

This module implements advanced retrieval techniques:
1. Query expansion (generating variants of the original query)
2. Multi-query retrieval (searching with all variants)
3. Reciprocal rank fusion (combining results from all queries)

Improves recall by expanding technical abbreviations and generating
semantic variants of construction queries.
"""
import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class AdvancedRetriever:
    """
    Advanced retriever with multi-query and query expansion.
    
    Generates multiple query variants to improve recall, especially for
    technical construction queries with abbreviations.
    """
    
    def __init__(self):
        """Initialize advanced retriever."""
        self.hybrid_retriever = HybridRetriever()
        
        # Use LLM for query expansion
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3  # Slight creativity for variant generation
        )
        
        logger.info("Advanced retriever initialized")
    
    def generate_query_variants(
        self,
        original_query: str,
        num_variants: int = 3
    ) -> List[str]:
        """
        Generate query variants using LLM.
        
        Expands technical abbreviations and generates semantic variants
        to improve retrieval recall.
        
        Args:
            original_query: Original search query
            num_variants: Number of variants to generate
        
        Returns:
            List of query variants (including original)
        """
        logger.info(f"Generating {num_variants} variants for: '{original_query}'")
        
        prompt = f"""Generate {num_variants} alternative search queries for construction document retrieval.

Original Query: "{original_query}"

Generate variants that:
1. Expand technical abbreviations (MH → manhole, RCP → reinforced concrete pipe, etc.)
2. Add context (e.g., "cover depth" → "minimum burial depth requirements")
3. Use different phrasings (e.g., "storm drain" → "storm water drainage system")

Common construction abbreviations:
- MH/SSMH = manhole/sanitary sewer manhole
- CB/DI/FES = catch basin/drain inlet/flared end section  
- WM/HYD/GV = water main/hydrant/gate valve
- RCP = reinforced concrete pipe
- DI = ductile iron
- PVC = polyvinyl chloride
- IE/INV = invert elevation
- SS = sanitary sewer
- SD = storm drain

Return ONLY a JSON array of strings (no explanation):
["variant 1", "variant 2", "variant 3"]"""
        
        messages = [
            SystemMessage(content="You are an expert at construction document terminology."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            import json
            variants = json.loads(response.content)
            
            # Ensure we have a list
            if not isinstance(variants, list):
                logger.warning(f"LLM returned non-list: {variants}")
                variants = [original_query]
            
            # Always include original query
            all_queries = [original_query] + [v for v in variants if v != original_query]
            
            logger.info(f"Generated {len(all_queries)} total queries (including original)")
            for i, q in enumerate(all_queries):
                logger.info(f"  {i+1}. {q}")
            
            return all_queries
        
        except Exception as e:
            logger.error(f"Query variant generation failed: {e}")
            # Fallback: return original query only
            return [original_query]
    
    def retrieve_multi_query(
        self,
        query: str,
        k: int = 5,
        discipline: str = None,
        category: str = None,
        num_variants: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using multiple query variants and fuse results.
        
        Args:
            query: Original search query
            k: Number of final results to return
            discipline: Optional discipline filter
            category: Optional category filter
            num_variants: Number of query variants to generate
        
        Returns:
            Fused results from all query variants
        """
        logger.info(f"Multi-query retrieval for: '{query}'")
        
        # Generate query variants
        query_variants = self.generate_query_variants(query, num_variants)
        
        # Retrieve with each variant
        all_results = []
        for variant in query_variants:
            results = self.hybrid_retriever.retrieve_hybrid(
                query=variant,
                k=k * 2,  # Get more results per query for better fusion
                discipline=discipline,
                category=category
            )
            all_results.append(results)
        
        # Fuse all results
        fused = self._multi_query_fusion(all_results, k=k)
        
        logger.info(f"Multi-query fusion: {len(fused)} final results")
        
        return fused
    
    def _multi_query_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fuse results from multiple queries using reciprocal rank fusion.
        
        Similar to the fusion in HybridRetriever, but works across
        multiple queries instead of multiple retrieval methods.
        
        Args:
            result_lists: List of result lists (one per query variant)
            k: Number of results to return
        
        Returns:
            Fused and re-ranked results
        """
        # Constant for RRF
        RRF_K = 60
        
        # Collect all unique documents with scores
        doc_scores = {}
        
        for query_idx, results in enumerate(result_lists):
            for rank, doc in enumerate(results, start=1):
                doc_id = doc["id"]
                rrf_score = 1.0 / (RRF_K + rank)
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "doc": doc,
                        "score": 0.0,
                        "query_sources": [],
                        "ranks": []
                    }
                
                doc_scores[doc_id]["score"] += rrf_score
                doc_scores[doc_id]["query_sources"].append(query_idx)
                doc_scores[doc_id]["ranks"].append(rank)
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        # Format output
        fused_results = []
        for item in sorted_docs[:k]:
            doc = item["doc"].copy()
            doc["multi_query_score"] = item["score"]
            doc["appeared_in_queries"] = len(item["query_sources"])
            doc["avg_rank"] = sum(item["ranks"]) / len(item["ranks"])
            fused_results.append(doc)
        
        return fused_results
    
    def expand_technical_terms(self, query: str) -> List[str]:
        """
        Expand common technical abbreviations in construction queries.
        
        Simple rule-based expansion for common terms.
        
        Args:
            query: Original query
        
        Returns:
            List of expanded queries
        """
        # Common construction abbreviations
        expansions = {
            "MH": "manhole",
            "SSMH": "sanitary sewer manhole",
            "CB": "catch basin",
            "DI": "drain inlet",
            "WM": "water main",
            "HYD": "hydrant",
            "RCP": "reinforced concrete pipe",
            "PVC": "polyvinyl chloride pipe",
            "HDPE": "high density polyethylene",
            "IE": "invert elevation",
            "INV": "invert elevation",
            "SS": "sanitary sewer",
            "SD": "storm drain"
        }
        
        expanded_queries = [query]
        query_upper = query.upper()
        
        for abbrev, expansion in expansions.items():
            if abbrev in query_upper:
                # Create variant with expansion
                expanded = query.replace(abbrev, expansion).replace(abbrev.lower(), expansion)
                expanded_queries.append(expanded)
        
        return list(set(expanded_queries))  # Remove duplicates
    
    def retrieve_with_expansion(
        self,
        query: str,
        k: int = 5,
        discipline: str = None,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve with automatic technical term expansion.
        
        Combines rule-based expansion with multi-query retrieval.
        
        Args:
            query: Original query
            k: Number of results
            discipline: Optional filter
            category: Optional filter
        
        Returns:
            Fused results from expanded queries
        """
        logger.info(f"Retrieve with expansion: '{query}'")
        
        # Expand technical terms
        expanded_queries = self.expand_technical_terms(query)
        
        if len(expanded_queries) > 1:
            logger.info(f"Expanded to {len(expanded_queries)} queries")
        
        # Retrieve with each
        all_results = []
        for exp_query in expanded_queries:
            results = self.hybrid_retriever.retrieve_hybrid(
                query=exp_query,
                k=k * 2,
                discipline=discipline,
                category=category
            )
            all_results.append(results)
        
        # Fuse
        fused = self._multi_query_fusion(all_results, k=k)
        
        logger.info(f"Expansion fusion: {len(fused)} results")
        
        return fused
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        base_stats = self.hybrid_retriever.get_stats()
        base_stats["retrieval_mode"] = "advanced_multi_query"
        return base_stats

