"""
Test script for analyzing real-world PDF (Dawn Ridge Homes).

This script runs the existing system on the 25-page PDF and documents:
1. What gets captured correctly
2. What gets missed or misidentified
3. Specific issues with different sheet types
"""
import sys
import logging
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Verify API key is available
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found in environment")
    print("Please set your OpenAI API key:")
    print("  export OPENAI_API_KEY='your-key-here'")
    sys.exit(1)

from app.agents.main_agent import MainAgent
from app.models import AgentState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_dawn_ridge_pdf():
    """Run existing system on Dawn Ridge Homes PDF."""
    
    pdf_path = Path(__file__).parent.parent / "golden_dataset" / "pdfs" / "Dawn Ridge Homes.pdf"
    
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    logger.info(f"=" * 80)
    logger.info(f"PHASE 1: BASELINE ANALYSIS - Dawn Ridge Homes PDF")
    logger.info(f"=" * 80)
    logger.info(f"PDF Path: {pdf_path}")
    logger.info(f"PDF Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    
    # Initialize Main Agent
    logger.info("\nInitializing Main Agent...")
    main_agent = MainAgent()
    
    # Create initial state
    initial_state: AgentState = {
        "pdf_path": str(pdf_path),
        "user_query": "Perform complete takeoff on this construction document",
        "pdf_summary": "",
        "final_report": {},
        "messages": []
    }
    
    # Run the full pipeline
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING FULL PIPELINE")
    logger.info("=" * 80)
    
    try:
        final_state = main_agent.workflow.invoke(initial_state)
        
        logger.info("\n" + "=" * 80)
        logger.info("BASELINE ANALYSIS RESULTS")
        logger.info("=" * 80)
        
        # Extract results from final_report
        final_report = final_state.get("final_report", {})
        vision_result = final_report.get("vision_results", {})
        researcher_results = final_report.get("researcher_results", {})
        consolidated_data = final_report.get("consolidated_data", {})
        errors = []  # Will collect from state if available
        
        # Document what was captured
        logger.info("\n### WHAT WAS CAPTURED ###")
        
        pipes = vision_result.get("pipes", [])
        logger.info(f"\nTotal Pipes Detected by Vision: {len(pipes)}")
        
        if pipes:
            logger.info("\nPipe Breakdown:")
            disciplines = {}
            for pipe in pipes:
                disc = pipe.get("discipline", "unknown")
                disciplines[disc] = disciplines.get(disc, 0) + 1
                logger.info(f"  - {disc}: {pipe.get('material', '?')} {pipe.get('diameter_in', '?')}\" x {pipe.get('length_ft', '?')} LF (depth: {pipe.get('depth_ft', 'N/A')})")
            
            logger.info(f"\nDiscipline Summary:")
            for disc, count in disciplines.items():
                logger.info(f"  - {disc}: {count} pipes")
        
        # Check for legend extraction
        legend = vision_result.get("legend", {})
        if legend:
            logger.info(f"\nLegend Extracted: {len(legend)} entries")
            for abbrev, full_name in list(legend.items())[:5]:
                logger.info(f"  - {abbrev}: {full_name}")
            if len(legend) > 5:
                logger.info(f"  ... and {len(legend) - 5} more entries")
        else:
            logger.info("\nLegend Extracted: NONE")
        
        # Check for elevation data
        has_elevations = any(pipe.get("depth_ft") for pipe in pipes)
        logger.info(f"\nElevation Data Captured: {'YES' if has_elevations else 'NO'}")
        
        # Check consolidated data
        summary = consolidated_data.get("summary", {})
        
        logger.info(f"\n### CONSOLIDATED SUMMARY ###")
        logger.info(f"Total Unique Pipes: {summary.get('total_pipes', 0)}")
        logger.info(f"Storm Pipes: {summary.get('storm_pipes', 0)} ({summary.get('storm_lf', 0)} LF)")
        logger.info(f"Sanitary Pipes: {summary.get('sanitary_pipes', 0)} ({summary.get('sanitary_lf', 0)} LF)")
        logger.info(f"Water Pipes: {summary.get('water_pipes', 0)} ({summary.get('water_lf', 0)} LF)")
        
        materials = consolidated_data.get("materials_found", [])
        if materials:
            logger.info(f"\nMaterials Identified: {', '.join(materials)}")
        
        # Check for unknowns
        user_alerts = consolidated_data.get("user_alerts", {})
        if user_alerts:
            logger.info(f"\n### UNKNOWN MATERIALS DETECTED ###")
            logger.info(f"Severity: {user_alerts.get('severity', 'N/A')}")
            logger.info(f"Message: {user_alerts.get('message', 'N/A')}")
            unknown_mats = user_alerts.get("unknown_materials", [])
            if unknown_mats:
                logger.info(f"Unknown Materials: {', '.join(unknown_mats)}")
        
        # Document errors
        if errors:
            logger.info(f"\n### ERRORS ENCOUNTERED ###")
            for i, error in enumerate(errors, 1):
                logger.info(f"{i}. {error}")
        
        # Save detailed results to file
        output_file = Path(__file__).parent.parent / "dawn_ridge_baseline_results.json"
        results_data = {
            "pdf_name": "Dawn Ridge Homes.pdf",
            "test_type": "baseline_analysis",
            "vision_pipes_count": len(pipes),
            "vision_pipes": pipes,
            "legend_entries": len(legend),
            "legend": legend,
            "has_elevations": has_elevations,
            "consolidated_summary": summary,
            "materials_found": materials,
            "user_alerts": user_alerts,
            "errors": errors,
            "full_state": {
                "vision_results": vision_result,
                "researcher_results": researcher_results,
                "consolidated_data": consolidated_data,
                "final_report": final_report
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"\n### RESULTS SAVED ###")
        logger.info(f"Detailed results saved to: {output_file}")
        
        # Analysis of what's missing
        logger.info("\n" + "=" * 80)
        logger.info("GAPS IDENTIFIED (What needs to be built)")
        logger.info("=" * 80)
        
        gaps = []
        
        if not legend or len(legend) < 5:
            gaps.append("❌ Legend extraction incomplete or missing")
        
        if not has_elevations:
            gaps.append("❌ Elevation data not captured (depth_ft all null)")
        
        if summary.get('total_pipes', 0) == 0:
            gaps.append("❌ No pipes detected - Vision may need enhancement")
        
        # Check for grading/earthwork
        gaps.append("❌ No grading/earthwork analysis (not implemented yet)")
        gaps.append("❌ No contour line reading (grading agent needed)")
        gaps.append("❌ No cut/fill volume calculations (grading agent needed)")
        
        if gaps:
            logger.info("\nIdentified Gaps:")
            for gap in gaps:
                logger.info(f"  {gap}")
        else:
            logger.info("\n✅ All features working as expected!")
        
        logger.info("\n" + "=" * 80)
        logger.info("BASELINE ANALYSIS COMPLETE")
        logger.info("=" * 80)
        logger.info(f"\nNext Steps:")
        logger.info(f"1. Review results in: {output_file}")
        logger.info(f"2. Identify which sheets caused issues")
        logger.info(f"3. Move to Phase 2: RAG Enhancement")
        
        return final_state
        
    except Exception as e:
        logger.error(f"\nFATAL ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    analyze_dawn_ridge_pdf()

