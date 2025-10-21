"""
Extract legend and abbreviations from Dawn Ridge Homes PDF.

This script uses a focused Vision prompt ONLY for legend extraction,
then chunks and stores the results in RAG with project-specific metadata.
"""
import sys
import os
import logging
import json
import base64
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LegendExtractor:
    """Extract legends and abbreviations from construction PDFs using Vision."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
    def pdf_page_to_base64_image(self, pdf_path: str, page_num: int) -> str:
        """Convert PDF page to base64 image."""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render at high DPI for better text recognition
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def extract_legend_from_page(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """
        Extract ONLY legend/abbreviations from a specific page.
        
        Uses a focused prompt that ONLY looks for legends, not pipes.
        """
        logger.info(f"Extracting legend from page {page_num}...")
        
        # Convert page to image
        img_base64 = self.pdf_page_to_base64_image(pdf_path, page_num)
        
        # Focused legend extraction prompt
        prompt = """You are analyzing a construction plan sheet. Your ONLY task is to extract the LEGEND or ABBREVIATIONS TABLE.

Look for:
1. Sections labeled "LEGEND", "ABBREVIATIONS", "SYMBOLS", "NOTES"
2. Tables showing abbreviation = full name (e.g., "RCP = Reinforced Concrete Pipe")
3. Symbol definitions (e.g., circle with X = manhole)
4. Material callouts in legend boxes

DO NOT extract pipe data, quantities, or measurements.
ONLY extract the legend/abbreviations.

Return JSON:
{
  "has_legend": true/false,
  "legend_entries": [
    {
      "abbreviation": "RCP",
      "full_name": "Reinforced Concrete Pipe",
      "category": "material" | "symbol" | "note" | "general"
    }
  ],
  "legend_title": "UTILITY LEGEND" or whatever the legend section is called,
  "notes": ["General notes from the legend section"]
}

If there is NO legend on this page, return:
{
  "has_legend": false,
  "legend_entries": [],
  "legend_title": null,
  "notes": []
}
"""
        
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                    }
                ]
            )
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                if result.get("has_legend"):
                    logger.info(f"✓ Found legend with {len(result.get('legend_entries', []))} entries")
                else:
                    logger.info(f"✗ No legend on this page")
                
                return result
            else:
                logger.warning(f"No JSON found in response for page {page_num}")
                return {"has_legend": False, "legend_entries": [], "legend_title": null, "notes": []}
        
        except Exception as e:
            logger.error(f"Failed to extract legend from page {page_num}: {e}")
            return {"has_legend": False, "legend_entries": [], "legend_title": null, "notes": []}
    
    def extract_all_legends(self, pdf_path: str, pages: List[int] = None) -> Dict[str, Any]:
        """
        Extract legends from multiple pages and consolidate.
        
        Args:
            pdf_path: Path to PDF
            pages: Specific pages to check (or None for all pages)
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        if pages is None:
            # Check all pages
            pages = list(range(total_pages))
        
        logger.info(f"Checking {len(pages)} pages for legends...")
        
        all_entries = []
        all_notes = []
        pages_with_legends = []
        
        for page_num in pages:
            result = self.extract_legend_from_page(pdf_path, page_num)
            
            if result.get("has_legend"):
                pages_with_legends.append(page_num)
                entries = result.get("legend_entries", [])
                
                # Add page metadata to each entry
                for entry in entries:
                    entry["source_page"] = page_num
                    entry["source_sheet"] = result.get("legend_title", f"Page {page_num}")
                    all_entries.append(entry)
                
                # Collect notes
                notes = result.get("notes", [])
                for note in notes:
                    all_notes.append({
                        "note": note,
                        "source_page": page_num
                    })
        
        logger.info(f"\n=== LEGEND EXTRACTION COMPLETE ===")
        logger.info(f"Pages with legends: {pages_with_legends}")
        logger.info(f"Total legend entries: {len(all_entries)}")
        logger.info(f"Total notes: {len(all_notes)}")
        
        return {
            "pdf_name": Path(pdf_path).name,
            "total_legend_entries": len(all_entries),
            "pages_with_legends": pages_with_legends,
            "legend_entries": all_entries,
            "notes": all_notes
        }


def chunk_legend_for_rag(legend_data: Dict[str, Any], project_name: str) -> List[Dict[str, Any]]:
    """
    Chunk legend data for RAG storage.
    
    Each abbreviation becomes a chunk with metadata for retrieval.
    """
    chunks = []
    
    # Chunk 1: Full legend overview
    overview_content = f"Project: {project_name}\n\n"
    overview_content += f"Legend contains {legend_data['total_legend_entries']} abbreviations and symbols.\n\n"
    overview_content += "Abbreviations:\n"
    
    for entry in legend_data['legend_entries']:
        overview_content += f"- {entry['abbreviation']}: {entry['full_name']}\n"
    
    chunks.append({
        "content": overview_content,
        "metadata": {
            "source": "project_legend",
            "project": project_name,
            "chunk_type": "legend_overview",
            "pages": legend_data['pages_with_legends']
        }
    })
    
    # Chunk 2-N: Individual abbreviations (for precise retrieval)
    for entry in legend_data['legend_entries']:
        abbrev_content = f"Abbreviation: {entry['abbreviation']}\n"
        abbrev_content += f"Full Name: {entry['full_name']}\n"
        abbrev_content += f"Category: {entry.get('category', 'general')}\n"
        abbrev_content += f"Source: {entry.get('source_sheet', 'Unknown')}\n"
        abbrev_content += f"\nThis abbreviation appears in the {project_name} construction documents."
        
        chunks.append({
            "content": abbrev_content,
            "metadata": {
                "source": "project_legend",
                "project": project_name,
                "chunk_type": "abbreviation",
                "abbreviation": entry['abbreviation'],
                "full_name": entry['full_name'],
                "category": entry.get('category', 'general'),
                "source_page": entry.get('source_page')
            }
        })
    
    # Chunk for notes
    if legend_data.get('notes'):
        notes_content = f"Project: {project_name}\n\nGeneral Notes:\n\n"
        for note_entry in legend_data['notes']:
            notes_content += f"- {note_entry['note']} (Page {note_entry['source_page']})\n"
        
        chunks.append({
            "content": notes_content,
            "metadata": {
                "source": "project_legend",
                "project": project_name,
                "chunk_type": "notes"
            }
        })
    
    return chunks


def main():
    """Extract legend from Dawn Ridge Homes and prepare for RAG storage."""
    
    pdf_path = Path(__file__).parent.parent / "golden_dataset" / "pdfs" / "Dawn Ridge Homes.pdf"
    
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    logger.info(f"=" * 80)
    logger.info(f"PHASE 2: LEGEND EXTRACTION")
    logger.info(f"=" * 80)
    logger.info(f"PDF: {pdf_path.name}")
    
    # Extract legends
    extractor = LegendExtractor()
    
    # Based on baseline analysis, legends are on pages 3, 4, 5, 7, 8, 9
    # Let's check first 15 pages to be thorough
    target_pages = list(range(15))
    
    legend_data = extractor.extract_all_legends(str(pdf_path), pages=target_pages)
    
    # Save raw legend data
    output_file = Path(__file__).parent.parent / "dawn_ridge_legend_data.json"
    with open(output_file, 'w') as f:
        json.dump(legend_data, f, indent=2)
    
    logger.info(f"\nRaw legend data saved to: {output_file}")
    
    # Chunk for RAG
    chunks = chunk_legend_for_rag(legend_data, "Dawn Ridge Homes")
    
    logger.info(f"\n=== RAG CHUNKING COMPLETE ===")
    logger.info(f"Created {len(chunks)} chunks for RAG storage:")
    logger.info(f"  - 1 overview chunk")
    logger.info(f"  - {len(legend_data['legend_entries'])} abbreviation chunks")
    logger.info(f"  - {1 if legend_data.get('notes') else 0} notes chunk")
    
    # Save chunks
    chunks_file = Path(__file__).parent.parent / "dawn_ridge_legend_chunks.json"
    with open(chunks_file, 'w') as f:
        json.dump(chunks, f, indent=2)
    
    logger.info(f"\nRAG chunks saved to: {chunks_file}")
    logger.info(f"\nNext step: Run store_legend_in_rag.py to load these into Qdrant")
    
    # Print sample
    if legend_data['legend_entries']:
        logger.info(f"\n=== SAMPLE LEGEND ENTRIES ===")
        for entry in legend_data['legend_entries'][:10]:
            logger.info(f"  {entry['abbreviation']:10s} = {entry['full_name']}")
        if len(legend_data['legend_entries']) > 10:
            logger.info(f"  ... and {len(legend_data['legend_entries']) - 10} more")


if __name__ == "__main__":
    main()

