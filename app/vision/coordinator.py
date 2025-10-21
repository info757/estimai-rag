"""
Vision Coordinator - orchestrates multiple specialized Vision agents.

Manages parallel execution of Vision agents and merges their results.
"""
import logging
import os
import asyncio
import base64
from typing import Dict, Any, List
from pathlib import Path
from collections import Counter
import fitz  # PyMuPDF

from app.vision.pipes_vision_agent_v2 import PipesVisionAgent
from app.vision.grading_vision_agent import GradingVisionAgent

logger = logging.getLogger(__name__)


class VisionCoordinator:
    """
    Coordinates multiple specialized Vision agents.
    
    This is the main entry point for Vision-based PDF analysis.
    It manages:
    - Converting PDF pages to images
    - Deploying appropriate Vision agents in parallel
    - Merging results from multiple agents
    - Deduplication and consolidation
    """
    
    def __init__(self):
        """Initialize coordinator with available Vision agents."""
        self.agents = {
            "pipes": PipesVisionAgent(),
            "grading": GradingVisionAgent()  # NEW: Grading plan detection
            # Future: Add more specialized agents as needed
            # "foundations": FoundationsVisionAgent(),
            # "electrical": ElectricalVisionAgent(),
        }
        
        logger.info(f"Vision Coordinator initialized with {len(self.agents)} agent(s)")
    
    async def analyze_page(
        self,
        pdf_path: str,
        page_num: int,
        agents_to_deploy: List[str] = None,
        dpi: int = 300  # Higher DPI for better accuracy
    ) -> Dict[str, Any]:
        """
        Analyze a single PDF page with multiple Vision agents.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-based)
            agents_to_deploy: List of agent keys to deploy (default: all pipe agents)
            dpi: Image rendering DPI (higher = better quality, larger size)
        
        Returns:
            Merged results from all deployed agents
        """
        # Default: deploy pipes and grading agents
        if agents_to_deploy is None:
            agents_to_deploy = ["pipes", "grading"]
        
        logger.info(
            f"[VisionCoord] Analyzing page {page_num} with {len(agents_to_deploy)} agents: "
            f"{', '.join(agents_to_deploy)}"
        )
        
        # Convert PDF page to base64 image (once, shared by all agents)
        image_b64 = await self._pdf_page_to_base64(pdf_path, page_num, dpi=dpi)
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        # Deploy agents in parallel
        tasks = []
        for agent_key in agents_to_deploy:
            if agent_key in self.agents:
                agent = self.agents[agent_key]
                tasks.append(agent.analyze(image_b64, api_key))
            else:
                logger.warning(f"[VisionCoord] Unknown agent: {agent_key}, skipping")
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_results = []
        for i, result in enumerate(results):
            agent_key = agents_to_deploy[i] if i < len(agents_to_deploy) else "unknown"
            
            if isinstance(result, Exception):
                logger.error(f"[VisionCoord] Agent {agent_key} failed: {result}")
            else:
                valid_results.append(result)
                pipes_found = len(result.get("pipes", []))
                logger.info(f"[VisionCoord] Agent {agent_key}: {pipes_found} pipes")
        
        # Merge results
        merged = self._merge_results(valid_results)
        
        logger.info(
            f"[VisionCoord] Page {page_num} complete: "
            f"{merged['total_pipes']} total pipes from {len(valid_results)} agents"
        )
        
        return merged
    
    async def analyze_multipage(
        self,
        pdf_path: str,
        max_pages: int = None,  # Changed to None for unlimited (or set to specific number)
        agents_to_deploy: List[str] = None,
        dpi: int = 300
    ) -> Dict[str, Any]:
        """
        Analyze multiple pages of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process (None = all pages, default: 25 for Dawn Ridge)
            agents_to_deploy: Which agents to use
            dpi: Image rendering quality
        
        Returns:
            Combined results from all pages
        """
        logger.info(f"[VisionCoord] Processing PDF: {pdf_path}")
        
        # Get page count
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        num_pages = min(total_pages, max_pages) if max_pages else total_pages
        doc.close()
        
        logger.info(f"[VisionCoord] Processing {num_pages} pages (out of {total_pages} total)")
        
        # Process each page
        page_results = []
        for page_num in range(num_pages):
            result = await self.analyze_page(
                pdf_path=pdf_path,
                page_num=page_num,
                agents_to_deploy=agents_to_deploy,
                dpi=dpi
            )
            page_results.append(result)
        
        # Combine results from all pages
        combined = self._combine_pages(page_results)
        
        logger.info(
            f"[VisionCoord] Complete: {combined['num_pages_processed']} pages, "
            f"{combined['total_pipes']} total pipes"
        )
        
        return combined
    
    async def _pdf_page_to_base64(
        self,
        pdf_path: str,
        page_num: int,
        dpi: int = 300
    ) -> str:
        """
        Convert PDF page to base64-encoded PNG image.
        
        Args:
            pdf_path: Path to PDF
            page_num: Page index (0-based)
            dpi: Rendering DPI (higher = better quality)
        
        Returns:
            Base64-encoded PNG
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at high DPI for Vision accuracy
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.pil_tobytes(format="PNG")
        
        doc.close()
        
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple Vision agents analyzing same page.
        
        Args:
            results: List of result dicts from different agents
        
        Returns:
            Merged result dict
        """
        all_pipes = []
        summaries = []
        
        for result in results:
            pipes = result.get("pipes", [])
            all_pipes.extend(pipes)
            
            summary = result.get("summary", "")
            if summary:
                summaries.append(summary)
        
        return {
            "pipes": all_pipes,
            "total_pipes": len(all_pipes),
            "summaries": summaries,
            "agents_deployed": len(results)
        }
    
    def _combine_pages(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple pages.
        
        Args:
            page_results: List of page result dicts
        
        Returns:
            Combined result dict
        """
        all_pipes = []
        page_summaries = []
        
        for page_idx, page_result in enumerate(page_results):
            pipes = page_result.get("pipes", [])
            
            # Add page number to each pipe
            for pipe in pipes:
                pipe["page_num"] = page_idx
                all_pipes.append(pipe)
            
            # Collect summaries
            summaries = page_result.get("summaries", [])
            if summaries:
                page_summaries.append(" | ".join(summaries))
        
        # Count by discipline
        disciplines = [p.get("discipline") for p in all_pipes if p.get("discipline")]
        discipline_counts = Counter(disciplines)
        
        return {
            "pipes": all_pipes,
            "total_pipes": len(all_pipes),
            "num_pages_processed": len(page_results),
            "page_summaries": page_summaries,
            "discipline_counts": dict(discipline_counts)
        }

