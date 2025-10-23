#!/usr/bin/env python3
"""
Compare current system output to ground truth from spreadsheets.

This script runs the current EstimAI-RAG system on the Dawn Ridge PDF
and compares the results to the ground truth extracted from the estimator's spreadsheets.

Generates detailed accuracy metrics to identify gaps and improvement areas.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from app.agents.main_agent import run_takeoff
from app.evaluation.custom_metrics import evaluate_takeoff_custom
from app.evaluation.ragas_eval import RAGASEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_ground_truth() -> Dict[str, Any]:
    """Load the ground truth data from parsed spreadsheets."""
    gt_file = Path("golden_dataset/ground_truth/dawn_ridge_annotations.json")
    
    if not gt_file.exists():
        logger.error(f"Ground truth file not found: {gt_file}")
        return {}
    
    with open(gt_file, 'r') as f:
        return json.load(f)

def run_current_system(pdf_path: str) -> Dict[str, Any]:
    """Run the current EstimAI-RAG system on the Dawn Ridge PDF."""
    logger.info(f"Running current system on: {pdf_path}")
    
    result = run_takeoff(pdf_path=pdf_path, user_query="")
    
    return result

def compare_pipes(predicted_pipes: List[Dict], expected_pipes: List[Dict]) -> Dict[str, Any]:
    """Compare predicted pipes to expected pipes from ground truth."""
    
    # Group by discipline
    pred_by_discipline = {}
    exp_by_discipline = {}
    
    for pipe in predicted_pipes:
        disc = pipe.get("discipline", "unknown")
        if disc not in pred_by_discipline:
            pred_by_discipline[disc] = []
        pred_by_discipline[disc].append(pipe)
    
    for pipe in expected_pipes:
        disc = pipe.get("discipline", "unknown")
        if disc not in exp_by_discipline:
            exp_by_discipline[disc] = []
        exp_by_discipline[disc].append(pipe)
    
    # Calculate metrics by discipline
    comparison = {
        "total_predicted": len(predicted_pipes),
        "total_expected": len(expected_pipes),
        "detection_rate": len(predicted_pipes) / len(expected_pipes) if expected_pipes else 0,
        "by_discipline": {}
    }
    
    for disc in ["storm", "sanitary", "water"]:
        pred = pred_by_discipline.get(disc, [])
        exp = exp_by_discipline.get(disc, [])
        
        # Calculate LF (handle None values)
        pred_lf = sum(p.get("length_ft") or 0 for p in pred)
        exp_lf = sum(p.get("length_ft") or 0 for p in exp)
        
        comparison["by_discipline"][disc] = {
            "predicted_count": len(pred),
            "expected_count": len(exp),
            "detection_rate": len(pred) / len(exp) if exp else 0,
            "predicted_lf": pred_lf,
            "expected_lf": exp_lf,
            "lf_accuracy": pred_lf / exp_lf if exp_lf > 0 else 0
        }
    
    return comparison

def identify_missing_categories(predicted: Dict, expected: Dict) -> Dict[str, Any]:
    """Identify what categories of items are missing from the predictions."""
    
    missing = {
        "laterals": [],
        "structures": [],
        "fittings": [],
        "materials": [],
        "volumes": []
    }
    
    # Check for laterals
    expected_laterals = [p for p in expected.get("expected_pipes", []) if p.get("type") == "Lateral"]
    predicted_laterals = [p for p in predicted.get("pipes", []) if "lateral" in str(p).lower() or "service" in str(p).lower()]
    
    if expected_laterals and not predicted_laterals:
        missing["laterals"] = [f"{p['structure_name']}: {p['count']} count, {p['length_ft']} LF" for p in expected_laterals]
    
    # Check for structures
    expected_structures = [p for p in expected.get("expected_pipes", []) if p.get("type") == "Vertical"]
    predicted_structures = [p for p in predicted.get("pipes", []) if "manhole" in str(p).lower() or "catch basin" in str(p).lower()]
    
    if expected_structures and not predicted_structures:
        missing["structures"] = [f"{p['structure_name']}: {p['count']} count" for p in expected_structures]
    
    # Check for fittings
    expected_fittings = [p for p in expected.get("expected_pipes", []) if p.get("type") == "Fitting"]
    predicted_fittings = [p for p in predicted.get("pipes", []) if "fitting" in str(p).lower() or "valve" in str(p).lower()]
    
    if expected_fittings and not predicted_fittings:
        missing["fittings"] = [f"{p['structure_name']}: {p['count']} count" for p in expected_fittings]
    
    # Check for materials
    if expected.get("expected_materials"):
        missing["materials"] = [f"{m['item']}: {m['quantity']} {m['unit']}" for m in expected.get("expected_materials", [])]
    
    # Check for volumes
    if expected.get("expected_volumes"):
        missing["volumes"] = [f"{v['name']}: Cut {v['cut_volume']}, Fill {v['fill_volume']}" for v in expected.get("expected_volumes", [])]
    
    return missing

def generate_gap_analysis_report(comparison: Dict, missing: Dict, metrics: Dict) -> str:
    """Generate a markdown report of the gap analysis."""
    
    report = "# Dawn Ridge Baseline vs. Ground Truth\n\n"
    report += "## Executive Summary\n\n"
    report += f"**Detection Rate**: {comparison['detection_rate']:.1%} ({comparison['total_predicted']}/{comparison['total_expected']} items)\n\n"
    
    report += "### By Discipline\n\n"
    report += "| Discipline | Predicted | Expected | Detection Rate | LF Predicted | LF Expected | LF Accuracy |\n"
    report += "|-----------|-----------|----------|----------------|--------------|-------------|-------------|\n"
    
    for disc, stats in comparison["by_discipline"].items():
        report += f"| {disc.title()} | {stats['predicted_count']} | {stats['expected_count']} | {stats['detection_rate']:.1%} | {stats['predicted_lf']:.0f} | {stats['expected_lf']:.0f} | {stats['lf_accuracy']:.1%} |\n"
    
    report += "\n## Missing Categories\n\n"
    
    for category, items in missing.items():
        if items:
            report += f"### {category.title()} (MISSING - {len(items)} items)\n\n"
            for item in items[:5]:  # Show first 5
                report += f"- {item}\n"
            if len(items) > 5:
                report += f"- ... and {len(items) - 5} more\n"
            report += "\n"
    
    report += "## Accuracy Metrics\n\n"
    report += "| Metric | Score |\n"
    report += "|--------|-------|\n"
    
    for metric, score in metrics.items():
        report += f"| {metric} | {score:.3f} |\n"
    
    report += "\n## Key Gaps to Address\n\n"
    
    gaps = []
    
    # Identify top gaps
    for disc, stats in comparison["by_discipline"].items():
        if stats["detection_rate"] < 0.5:
            gaps.append(f"**{disc.title()}**: Only detecting {stats['detection_rate']:.1%} of items")
    
    if missing["laterals"]:
        gaps.append(f"**Laterals**: Missing {len(missing['laterals'])} service connections")
    
    if missing["structures"]:
        gaps.append(f"**Structures**: Missing {len(missing['structures'])} manholes/catch basins/inlets")
    
    if missing["fittings"]:
        gaps.append(f"**Fittings**: Missing {len(missing['fittings'])} valves/fittings")
    
    if missing["materials"]:
        gaps.append(f"**Materials**: Missing entire erosion control/site work category ({len(missing['materials'])} items)")
    
    for gap in gaps:
        report += f"- {gap}\n"
    
    report += "\n## Recommended Actions\n\n"
    report += "1. **Update Vision Prompts**: Add explicit instructions for laterals, structures, fittings\n"
    report += "2. **Enhance RAG**: Add {len(missing['laterals'])+len(missing['structures'])+len(missing['fittings'])} construction terms\n"
    report += "3. **New Agents**: Consider erosion control and site work vision agents\n"
    report += "4. **Test Iteration**: Re-run with enhanced prompts and measure improvement\n"
    
    return report

def main():
    """Main function to compare baseline to ground truth."""
    
    # File paths
    pdf_path = "uploads/Dawn Ridge Homes_HEPA_Combined_04-1-25.pdf"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    # Load ground truth
    logger.info("Loading ground truth...")
    ground_truth = load_ground_truth()
    
    if not ground_truth:
        logger.error("Failed to load ground truth")
        return
    
    logger.info(f"Ground truth loaded: {ground_truth['expected_summary']}")
    
    # Run current system
    logger.info("Running current system...")
    current_result = run_current_system(pdf_path)
    
    # Extract takeoff result
    takeoff_result = current_result.get("takeoff_result", {})
    
    logger.info(f"Current system result: {takeoff_result.get('summary', {})}")
    
    # Compare pipes
    logger.info("Comparing pipes...")
    predicted_pipes = takeoff_result.get("pipes", [])
    expected_pipes = ground_truth.get("expected_pipes", [])
    
    comparison = compare_pipes(predicted_pipes, expected_pipes)
    
    # Identify missing categories
    logger.info("Identifying missing categories...")
    missing = identify_missing_categories(takeoff_result, ground_truth)
    
    # Evaluate using custom metrics
    logger.info("Calculating accuracy metrics...")
    retrieved_contexts = []
    for researcher_result in current_result.get("researcher_results", {}).values():
        retrieved_contexts.extend(researcher_result.get("retrieved_context", []))
    
    metrics = evaluate_takeoff_custom(
        predicted=takeoff_result,
        expected=ground_truth,
        retrieved_contexts=retrieved_contexts
    )
    
    # Generate report
    logger.info("Generating gap analysis report...")
    report = generate_gap_analysis_report(comparison, missing, metrics)
    
    # Save report
    output_file = "golden_dataset/dawn_ridge_baseline_vs_ground_truth.md"
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {output_file}")
    
    # Also save detailed comparison as JSON
    detailed_output = {
        "comparison": comparison,
        "missing_categories": missing,
        "accuracy_metrics": metrics,
        "current_result_summary": takeoff_result.get("summary", {}),
        "ground_truth_summary": ground_truth.get("expected_summary", {})
    }
    
    json_output_file = "golden_dataset/dawn_ridge_baseline_vs_ground_truth.json"
    with open(json_output_file, 'w') as f:
        json.dump(detailed_output, f, indent=2)
    
    logger.info(f"Detailed comparison saved to: {json_output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("BASELINE VS. GROUND TRUTH COMPARISON")
    print("="*80)
    print(f"\nDetection Rate: {comparison['detection_rate']:.1%} ({comparison['total_predicted']}/{comparison['total_expected']} items)")
    print(f"\nAccuracy Metrics:")
    for metric, score in metrics.items():
        print(f"  {metric}: {score:.3f}")
    print(f"\nMissing Categories:")
    for category, items in missing.items():
        if items:
            print(f"  {category.title()}: {len(items)} items missing")
    
    return detailed_output

if __name__ == "__main__":
    main()

