#!/usr/bin/env python3
"""
Run custom evaluation metrics on golden dataset.

Tests what actually matters for construction takeoff:
- Pipe count accuracy
- Material classification
- Elevation extraction  
- RAG retrieval quality
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from app.evaluation.custom_metrics import evaluate_takeoff_custom, format_custom_results_table
from app.agents.main_agent import run_takeoff

logging.basicConfig(level=logging.WARNING)  # Less verbose
logger = logging.getLogger(__name__)


def load_test_case(test_num):
    """Load a specific test case."""
    pdf_path = f"golden_dataset/pdfs/test_{test_num:02d}_*.pdf"
    gt_path = f"golden_dataset/ground_truth/test_{test_num:02d}_annotations.json"
    
    from glob import glob
    pdf_files = glob(pdf_path)
    
    if not pdf_files:
        return None
    
    pdf_file = pdf_files[0]
    
    with open(glob(gt_path)[0], 'r') as f:
        ground_truth = json.load(f)
    
    return {
        "pdf_path": pdf_file,
        "pdf_name": Path(pdf_file).name,
        "ground_truth": ground_truth
    }


def main():
    """Run custom evaluation."""
    print("\n" + "="*60)
    print("CUSTOM TAKEOFF EVALUATION")
    print("="*60)
    print()
    
    # Test case 1
    print("📄 Test 01: Simple Storm Drain")
    print("-" * 60)
    
    test_case = load_test_case(1)
    if not test_case:
        print("❌ Test case not found")
        return 1
    
    print(f"PDF: {test_case['pdf_name']}")
    print(f"Expected: {test_case['ground_truth']['description']}")
    print()
    
    # Run takeoff
    print("🤖 Running takeoff...")
    result = run_takeoff(test_case["pdf_path"])
    
    # Extract data
    takeoff_data = result.get("takeoff_result", {})
    researcher_results = result.get("researcher_results", {})
    
    # Get all retrieved contexts
    all_contexts = []
    for researcher_name, res in researcher_results.items():
        all_contexts.extend(res.get("retrieved_context", []))
    
    print(f"✅ Takeoff complete")
    print(f"   Detected: {takeoff_data.get('summary', {}).get('total_pipes', 0)} pipes")
    print(f"   Retrieved: {len(all_contexts)} construction standards")
    print()
    
    # Evaluate with custom metrics
    print("📊 Custom Metrics Evaluation")
    print("-" * 60)
    
    scores = evaluate_takeoff_custom(
        predicted=takeoff_data,
        expected=test_case["ground_truth"],
        retrieved_contexts=all_contexts
    )
    
    print()
    print(format_custom_results_table(scores))
    print()
    
    # Analysis
    overall = scores.get("overall_accuracy", 0.0)
    
    if overall >= 0.90:
        print("✅ EXCELLENT! System is highly accurate")
    elif overall >= 0.75:
        print("✅ GOOD! System meets accuracy targets")
    elif overall >= 0.60:
        print("⚠️  ACCEPTABLE - Room for improvement")
    else:
        print("❌ NEEDS WORK - Check detection and RAG retrieval")
    
    print()
    
    # Detailed breakdown
    print("📋 Detailed Breakdown:")
    print(f"  Pipe Count: {scores['pipe_count_accuracy']:.1%}")
    print(f"  Materials: {scores['material_accuracy']:.1%}")
    print(f"  Elevations: {scores['elevation_accuracy']:.1%}")
    print(f"  RAG Retrieval: {scores['rag_retrieval_quality']:.1%}")
    print()
    
    # Save results
    results_file = Path("golden_dataset/custom_eval_results.json")
    with open(results_file, 'w') as f:
        json.dump(scores, f, indent=2)
    
    print(f"✅ Results saved to: {results_file}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

