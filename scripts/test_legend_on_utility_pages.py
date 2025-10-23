#!/usr/bin/env python3
"""
Test legend extraction on utility plan pages where abbreviations appear as labels.
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

def test_legend_on_utility_page(pdf_path: str, page_num: int):
    """Test legend extraction on a utility plan page."""
    logger.info(f"Testing legend extraction on utility page {page_num}")
    
    try:
        coordinator = VisionCoordinator()
        result = asyncio.run(coordinator.analyze_page(
            pdf_path=pdf_path,
            page_num=page_num,
            agents_to_deploy=["legend"],
            dpi=300
        ))
        
        print(f"\n{'='*60}")
        print(f"UTILITY PAGE {page_num} LEGEND ANALYSIS")
        print(f"{'='*60}")
        
        if result and isinstance(result, dict):
            legend_data = None
            
            if "legend" in result:
                legend_data = result["legend"]
            elif "pipes" in result and len(result["pipes"]) > 0:
                legend_data = result["pipes"][0] if isinstance(result["pipes"], list) else result["pipes"]
            else:
                legend_data = result
            
            if legend_data:
                print(f"Raw result: {json.dumps(legend_data, indent=2)}")
                
                if legend_data.get("is_legend_page", False):
                    print("✅ LEGEND DATA FOUND ON UTILITY PAGE")
                    
                    abbreviations = legend_data.get("abbreviations", [])
                    symbols = legend_data.get("symbols", [])
                    specifications = legend_data.get("specifications", [])
                    
                    print(f"\nAbbreviations found: {len(abbreviations)}")
                    for abbr in abbreviations:
                        print(f"  {abbr.get('abbr', 'N/A')} = {abbr.get('full_name', 'N/A')} ({abbr.get('category', 'N/A')})")
                    
                    print(f"\nSymbols found: {len(symbols)}")
                    for symbol in symbols:
                        print(f"  {symbol.get('symbol', 'N/A')} = {symbol.get('meaning', 'N/A')}")
                    
                    print(f"\nSpecifications found: {len(specifications)}")
                    for spec in specifications:
                        print(f"  {spec.get('code', 'N/A')} = {spec.get('description', 'N/A')}")
                else:
                    print("❌ NO LEGEND DATA DETECTED")
                    print(f"Summary: {legend_data.get('summary', 'No summary')}")
            else:
                print("❌ NO DATA RETURNED")
        else:
            print("❌ INVALID RESULT FORMAT")
            
    except Exception as e:
        logger.error(f"Failed to analyze page {page_num}: {e}")
        print(f"❌ ERROR: {e}")

def main():
    """Test legend extraction on utility plan pages."""
    
    pdf_path = "uploads/Dawn Ridge Homes_HEPA_Combined_04-1-25.pdf"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    # Test utility pages where we found pipes (these should have abbreviations)
    utility_pages = [6, 8, 9, 13, 14]  # Pages where we detected utilities
    
    print("Testing legend extraction on utility plan pages...")
    print("These pages contain utilities and should have abbreviations like:")
    print("- RCP, PVC, DIP (materials)")
    print("- SS, STM, WM (disciplines)")  
    print("- MH, CB, CO (structures)")
    print("- NCDOT specifications")
    
    for page_num in utility_pages:
        test_legend_on_utility_page(pdf_path, page_num)
    
    print(f"\n{'='*60}")
    print("UTILITY PAGE LEGEND TEST COMPLETE")
    print(f"{'='*60}")
    print("\nIf no legend data was found on utility pages, the abbreviations might be:")
    print("1. Too small or embedded in the plan")
    print("2. In a different format than expected")
    print("3. Already captured by our construction knowledge base")
    print("\nNote: We already have 40 construction terms in RAG from our knowledge base!")

if __name__ == "__main__":
    main()
