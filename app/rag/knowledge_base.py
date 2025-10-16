"""
Knowledge base setup and management for construction standards.

This module loads construction standards from JSON files and prepares them
for ingestion into the Qdrant vector store.
"""
import json
import logging
from pathlib import Path
from typing import List

from app.models import ConstructionStandard

logger = logging.getLogger(__name__)


class ConstructionKnowledgeBase:
    """Manages construction standards knowledge base."""
    
    def __init__(self, standards_dir: str | Path = None):
        """
        Initialize knowledge base.
        
        Args:
            standards_dir: Directory containing JSON standard files.
                          Defaults to app/rag/standards/
        """
        if standards_dir is None:
            # Default to standards directory relative to this file
            self.standards_dir = Path(__file__).parent / "standards"
        else:
            self.standards_dir = Path(standards_dir)
        
        self.standards: List[ConstructionStandard] = []
        logger.info(f"Initialized KB with standards dir: {self.standards_dir}")
    
    def load_all_standards(self) -> List[ConstructionStandard]:
        """
        Load all construction standards from JSON files.
        
        Returns:
            List of ConstructionStandard objects
        """
        logger.info("Loading all construction standards...")
        
        # Load each JSON file
        json_files = [
            "cover_depths.json",
            "materials.json",
            "symbols.json",
            "validation_rules.json"
        ]
        
        all_standards = []
        
        for json_file in json_files:
            file_path = self.standards_dir / json_file
            if not file_path.exists():
                logger.warning(f"Standards file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Convert to ConstructionStandard objects
                for item in data:
                    standard = ConstructionStandard(**item)
                    all_standards.append(standard)
                
                logger.info(f"Loaded {len(data)} standards from {json_file}")
            
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
                continue
        
        self.standards = all_standards
        logger.info(f"Total standards loaded: {len(self.standards)}")
        
        return self.standards
    
    def get_standards_by_discipline(
        self,
        discipline: str
    ) -> List[ConstructionStandard]:
        """
        Get standards filtered by discipline.
        
        Args:
            discipline: storm, sanitary, water, or general
        
        Returns:
            Filtered list of standards
        """
        return [
            s for s in self.standards
            if s.discipline == discipline or s.discipline == "general"
        ]
    
    def get_standards_by_category(
        self,
        category: str
    ) -> List[ConstructionStandard]:
        """
        Get standards filtered by category.
        
        Args:
            category: cover_depth, material, slope, symbol, validation
        
        Returns:
            Filtered list of standards
        """
        return [s for s in self.standards if s.category == category]
    
    def get_standards_text(self) -> List[str]:
        """
        Get all standards as plain text for embedding.
        
        Returns:
            List of standard content strings
        """
        return [s.content for s in self.standards]
    
    def get_standards_with_metadata(self) -> List[dict]:
        """
        Get standards with full metadata for Qdrant.
        
        Returns:
            List of dicts with content and metadata
        """
        results = []
        for i, standard in enumerate(self.standards):
            results.append({
                "id": i,
                "content": standard.content,
                "metadata": {
                    "discipline": standard.discipline,
                    "category": standard.category,
                    "source": standard.source,
                    "reference": standard.reference or ""
                }
            })
        return results
    
    def search_standards(
        self,
        query: str,
        discipline: str = None,
        category: str = None
    ) -> List[ConstructionStandard]:
        """
        Simple keyword search in standards (for testing).
        
        Args:
            query: Search query
            discipline: Optional discipline filter
            category: Optional category filter
        
        Returns:
            Matching standards
        """
        query_lower = query.lower()
        results = []
        
        for standard in self.standards:
            # Apply filters
            if discipline and standard.discipline != discipline and standard.discipline != "general":
                continue
            if category and standard.category != category:
                continue
            
            # Simple keyword match
            if query_lower in standard.content.lower():
                results.append(standard)
        
        logger.info(f"Keyword search for '{query}': {len(results)} results")
        return results
    
    def get_stats(self) -> dict:
        """Get statistics about the knowledge base."""
        stats = {
            "total_standards": len(self.standards),
            "by_discipline": {},
            "by_category": {}
        }
        
        # Count by discipline
        for standard in self.standards:
            disc = standard.discipline or "unknown"
            stats["by_discipline"][disc] = stats["by_discipline"].get(disc, 0) + 1
        
        # Count by category
        for standard in self.standards:
            cat = standard.category or "unknown"
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        
        return stats


# Convenience function
def load_knowledge_base() -> ConstructionKnowledgeBase:
    """
    Load and return the construction knowledge base.
    
    Returns:
        Initialized ConstructionKnowledgeBase with all standards loaded
    """
    kb = ConstructionKnowledgeBase()
    kb.load_all_standards()
    
    logger.info("Knowledge base loaded successfully")
    logger.info(f"Stats: {kb.get_stats()}")
    
    return kb

