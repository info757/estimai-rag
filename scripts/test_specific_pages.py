#!/usr/bin/env python3
"""
Test specific pages to debug missing items and improve detection.

This script tests individual pages to understand:
1. What items are visible on each page
2. What the Vision agents are detecting vs missing
3. How to improve prompts for specific item types
"""
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from app.vision.coordinator import VisionCoordinator
from app.vision.pipes_vision_agent_v2 import PipesVisionAgent
from app.vision.grading_vision_agent import GradingVisionAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_ground_truth() -> Dict[str, Any]:
    """Load ground truth to understand what should be on each page."""
    gt_file = Path("golden_dataset/ground_truth/dawn_ridge_annotations.json")
    
    if not gt_file.exists():
        logger.error(f"Ground truth file not found: {gt_file}")
        return {}
    
    with open(gt_file, 'r') as f:
        return json.load(f)

def test_single_page(pdf_path: str, page_num: int, agents: List[str] = None) -> Dict[str, Any]:
    """Test a single page with specified agents."""
    if agents is None:
        agents = ["pipes", "grading"]
    
    logger.info(f"Testing page {page_num} with agents: {agents}")
    
    try:
        coordinator = VisionCoordinator()
        result = asyncio.run(coordinator.analyze_page(
            pdf_path=pdf_path,
            page_num=page_num,
            agents_to_deploy=agents,
            dpi=300
        ))
        
        return {
            "page_num": page_num,
            "agents": agents,
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze page {page_num}: {e}")
        return {
            "page_num": page_num,
            "agents": agents,
            "success": False,
            "error": str(e)
        }

def analyze_page_content(page_result: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze what was found vs what should be there."""
    if not page_result.get("success"):
        return {"error": "Page analysis failed"}
    
    result = page_result["result"]
    page_num = page_result["page_num"]
    
    # Extract detected items
    detected_items = {
        "pipes": result.get("pipes", []),
        "grading": result.get("grading", {}),
        "total_detected": len(result.get("pipes", []))
    }
    
    # Count by type
    item_types = {}
    for pipe in result.get("pipes", []):
        item_type = pipe.get("item_type", "unknown")
        item_types[item_type] = item_types.get(item_type, 0) + 1
    
    # Look for specific patterns
    analysis = {
        "page_num": page_num,
        "total_detected": detected_items["total_detected"],
        "item_types": item_types,
        "has_laterals": any("lateral" in str(pipe).lower() for pipe in result.get("pipes", [])),
        "has_structures": any("structure" in str(pipe).lower() for pipe in result.get("pipes", [])),
        "has_fittings": any("fitting" in str(pipe).lower() for pipe in result.get("pipes", [])),
        "has_erosion_control": len(result.get("grading", {}).get("erosion_control", [])) > 0,
        "has_site_work": len(result.get("grading", {}).get("site_work", [])) > 0,
        "materials_found": list(set(pipe.get("material", "unknown") for pipe in result.get("pipes", []))),
        "raw_pipes": result.get("pipes", []),
        "raw_grading": result.get("grading", {})
    }
    
    return analysis

def test_key_pages(pdf_path: str) -> Dict[str, Any]:
    """Test key pages that should have specific types of items."""
    
    # Pages that typically have utilities (based on our previous runs)
    key_pages = [6, 8, 9, 13, 14, 16]
    
    results = {}
    
    for page_num in key_pages:
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING PAGE {page_num}")
        logger.info(f"{'='*60}")
        
        # Test with both agents
        page_result = test_single_page(pdf_path, page_num, ["pipes", "grading"])
        
        if page_result["success"]:
            analysis = analyze_page_content(page_result, {})
            results[page_num] = analysis
            
            # Print summary
            print(f"\nPage {page_num} Results:")
            print(f"  Total Items: {analysis['total_detected']}")
            print(f"  Item Types: {analysis['item_types']}")
            print(f"  Materials: {analysis['materials_found']}")
            print(f"  Has Laterals: {analysis['has_laterals']}")
            print(f"  Has Structures: {analysis['has_structures']}")
            print(f"  Has Fittings: {analysis['has_fittings']}")
            print(f"  Has Erosion Control: {analysis['has_erosion_control']}")
            print(f"  Has Site Work: {analysis['has_site_work']}")
            
            # Show raw results for debugging
            if analysis['raw_pipes']:
                print(f"\n  Raw Pipes Found:")
                for i, pipe in enumerate(analysis['raw_pipes'][:3]):  # Show first 3
                    print(f"    {i+1}. {pipe}")
                if len(analysis['raw_pipes']) > 3:
                    print(f"    ... and {len(analysis['raw_pipes']) - 3} more")
            
            if analysis['raw_grading']:
                print(f"\n  Raw Grading Found:")
                print(f"    {analysis['raw_grading']}")
        else:
            logger.error(f"Failed to analyze page {page_num}: {page_result.get('error')}")
            results[page_num] = {"error": page_result.get("error")}
    
    return results

def generate_debug_report(results: Dict[str, Any]) -> str:
    """Generate a debug report with recommendations."""
    
    report = "# Page-by-Page Debug Analysis\n\n"
    report += "## Summary\n\n"
    
    total_pages = len(results)
    successful_pages = len([r for r in results.values() if "error" not in r])
    
    report += f"- **Pages Tested**: {total_pages}\n"
    report += f"- **Successful**: {successful_pages}\n"
    report += f"- **Failed**: {total_pages - successful_pages}\n\n"
    
    # Analyze patterns
    all_laterals = sum(1 for r in results.values() if r.get("has_laterals", False))
    all_structures = sum(1 for r in results.values() if r.get("has_structures", False))
    all_fittings = sum(1 for r in results.values() if r.get("has_fittings", False))
    all_erosion = sum(1 for r in results.values() if r.get("has_erosion_control", False))
    
    report += "## Detection Patterns\n\n"
    report += f"- **Pages with Laterals**: {all_laterals}/{successful_pages}\n"
    report += f"- **Pages with Structures**: {all_structures}/{successful_pages}\n"
    report += f"- **Pages with Fittings**: {all_fittings}/{successful_pages}\n"
    report += f"- **Pages with Erosion Control**: {all_erosion}/{successful_pages}\n\n"
    
    # Per-page details
    report += "## Per-Page Results\n\n"
    
    for page_num, result in results.items():
        if "error" in result:
            report += f"### Page {page_num} - ERROR\n"
            report += f"```\n{result['error']}\n```\n\n"
            continue
        
        report += f"### Page {page_num}\n\n"
        report += f"- **Items Detected**: {result['total_detected']}\n"
        report += f"- **Item Types**: {result['item_types']}\n"
        report += f"- **Materials**: {', '.join(result['materials_found'])}\n"
        report += f"- **Laterals**: {'✅' if result['has_laterals'] else '❌'}\n"
        report += f"- **Structures**: {'✅' if result['has_structures'] else '❌'}\n"
        report += f"- **Fittings**: {'✅' if result['has_fittings'] else '❌'}\n"
        report += f"- **Erosion Control**: {'✅' if result['has_erosion_control'] else '❌'}\n"
        report += f"- **Site Work**: {'✅' if result['has_site_work'] else '❌'}\n\n"
        
        # Show sample items
        if result['raw_pipes']:
            report += "**Sample Items Found:**\n"
            for i, pipe in enumerate(result['raw_pipes'][:2]):
                report += f"- {pipe}\n"
            if len(result['raw_pipes']) > 2:
                report += f"- ... and {len(result['raw_pipes']) - 2} more\n"
            report += "\n"
    
    # Recommendations
    report += "## Recommendations\n\n"
    
    if all_laterals == 0:
        report += "### ❌ LATERALS NOT DETECTED\n"
        report += "- **Issue**: No laterals detected on any page\n"
        report += "- **Solution**: Enhance prompts with more specific lateral instructions\n"
        report += "- **Try**: Add examples of lateral patterns, dashed lines, service connections\n\n"
    
    if all_structures == 0:
        report += "### ❌ STRUCTURES NOT DETECTED\n"
        report += "- **Issue**: No structures (manholes, catch basins) detected\n"
        report += "- **Solution**: Add explicit structure detection instructions\n"
        report += "- **Try**: Look for circles (manholes), rectangles (catch basins), labels (MH-1, CB-2)\n\n"
    
    if all_fittings == 0:
        report += "### ❌ FITTINGS NOT DETECTED\n"
        report += "- **Issue**: No fittings (valves, FES, collars) detected\n"
        report += "- **Solution**: Add fitting-specific detection instructions\n"
        report += "- **Try**: Look for valve symbols, FES callouts, connection points\n\n"
    
    if all_erosion == 0:
        report += "### ❌ EROSION CONTROL NOT DETECTED\n"
        report += "- **Issue**: Grading agent not detecting erosion control items\n"
        report += "- **Solution**: Enhance grading agent prompts\n"
        report += "- **Try**: Look for silt fence, inlet protection, slope matting symbols\n\n"
    
    return report

def main():
    """Main function to test specific pages and generate debug report."""
    
    pdf_path = "uploads/Dawn Ridge Homes_HEPA_Combined_04-1-25.pdf"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    # Load ground truth for context
    ground_truth = load_ground_truth()
    logger.info(f"Ground truth loaded: {ground_truth.get('expected_summary', {})}")
    
    # Test key pages
    logger.info("Testing key pages for debugging...")
    results = test_key_pages(pdf_path)
    
    # Generate debug report
    logger.info("Generating debug report...")
    report = generate_debug_report(results)
    
    # Save report
    output_file = "golden_dataset/page_debug_analysis.md"
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Debug report saved to: {output_file}")
    
    # Also save raw results as JSON
    json_output = "golden_dataset/page_debug_results.json"
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Raw results saved to: {json_output}")
    
    # Print summary
    print("\n" + "="*80)
    print("PAGE DEBUG ANALYSIS COMPLETE")
    print("="*80)
    
    successful_pages = len([r for r in results.values() if "error" not in r])
    total_items = sum(r.get("total_detected", 0) for r in results.values() if "error" not in r)
    
    print(f"\nPages Tested: {len(results)}")
    print(f"Successful: {successful_pages}")
    print(f"Total Items Detected: {total_items}")
    
    # Show detection patterns
    all_laterals = sum(1 for r in results.values() if r.get("has_laterals", False))
    all_structures = sum(1 for r in results.values() if r.get("has_structures", False))
    all_fittings = sum(1 for r in results.values() if r.get("has_fittings", False))
    all_erosion = sum(1 for r in results.values() if r.get("has_erosion_control", False))
    
    print(f"\nDetection Patterns:")
    print(f"  Laterals: {all_laterals}/{successful_pages} pages")
    print(f"  Structures: {all_structures}/{successful_pages} pages")
    print(f"  Fittings: {all_fittings}/{successful_pages} pages")
    print(f"  Erosion Control: {all_erosion}/{successful_pages} pages")
    
    print(f"\nFiles Generated:")
    print(f"  - {output_file}")
    print(f"  - {json_output}")
    
    return results

if __name__ == "__main__":
    main()
