#!/usr/bin/env python3
"""
Test legend extraction on specific pages to debug and refine the approach.
"""
import sys
import json
import logging
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from app.vision.coordinator import VisionCoordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_legend_on_page(pdf_path: str, page_num: int):
    """Test legend extraction on a specific page."""
    logger.info(f"Testing legend extraction on page {page_num}")
    
    try:
        coordinator = VisionCoordinator()
        result = asyncio.run(coordinator.analyze_page(
            pdf_path=pdf_path,
            page_num=page_num,
            agents_to_deploy=["legend"],
            dpi=300
        ))
        
        print(f"\n{'='*60}")
        print(f"PAGE {page_num} LEGEND ANALYSIS")
        print(f"{'='*60}")
        
        if result and isinstance(result, dict):
            # Check for legend data in various possible locations
            legend_data = None
            
            if "legend" in result:
                legend_data = result["legend"]
            elif "pipes" in result and len(result["pipes"]) > 0:
                # Legend agent might return data in pipes array
                legend_data = result["pipes"][0] if isinstance(result["pipes"], list) else result["pipes"]
            else:
                legend_data = result
            
            if legend_data:
                print(f"Raw result: {json.dumps(legend_data, indent=2)}")
                
                if legend_data.get("is_legend_page", False):
                    print("✅ LEGEND PAGE DETECTED")
                    
                    abbreviations = legend_data.get("abbreviations", [])
                    symbols = legend_data.get("symbols", [])
                    specifications = legend_data.get("specifications", [])
                    
                    print(f"\nAbbreviations found: {len(abbreviations)}")
                    for abbr in abbreviations[:5]:  # Show first 5
                        print(f"  {abbr.get('abbr', 'N/A')} = {abbr.get('full_name', 'N/A')}")
                    
                    print(f"\nSymbols found: {len(symbols)}")
                    for symbol in symbols[:3]:  # Show first 3
                        print(f"  {symbol.get('symbol', 'N/A')} = {symbol.get('meaning', 'N/A')}")
                    
                    print(f"\nSpecifications found: {len(specifications)}")
                    for spec in specifications[:3]:  # Show first 3
                        print(f"  {spec.get('code', 'N/A')} = {spec.get('description', 'N/A')}")
                else:
                    print("❌ NOT A LEGEND PAGE")
                    print(f"Summary: {legend_data.get('summary', 'No summary')}")
            else:
                print("❌ NO DATA RETURNED")
        else:
            print("❌ INVALID RESULT FORMAT")
            
    except Exception as e:
        logger.error(f"Failed to analyze page {page_num}: {e}")
        print(f"❌ ERROR: {e}")

def main():
    """Test legend extraction on multiple pages."""
    
    pdf_path = "uploads/Dawn Ridge Homes_HEPA_Combined_04-1-25.pdf"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    # Test first 5 pages to see what's there
    for page_num in range(5):
        test_legend_on_page(pdf_path, page_num)
    
    print(f"\n{'='*60}")
    print("LEGEND EXTRACTION TEST COMPLETE")
    print(f"{'='*60}")
    print("\nIf no legend pages were detected, the legend might be:")
    print("1. Embedded within utility plan pages")
    print("2. On a different page number")
    print("3. In a different format than expected")
    print("\nNext steps:")
    print("- Check if legend appears on utility plan pages")
    print("- Refine legend agent prompts")
    print("- Look for abbreviation tables within plan sheets")

if __name__ == "__main__":
    main()
