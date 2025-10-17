#!/usr/bin/env python3
"""
Run custom evaluation with API-augmented RAG.

This uses the full Supervisor with API researcher auto-deployment,
demonstrating hybrid RAG: local knowledge + external API fallback.

Key difference from baseline:
- Supervisor monitors confidence scores
- Auto-deploys API Researcher when confidence < 0.5 or contexts < 3
- Queries Tavily API for external construction standards
- Especially effective on test_05 (unknown materials)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from glob import glob
from app.evaluation.custom_metrics import evaluate_takeoff_custom, format_custom_results_table
from app.agents.main_agent import run_takeoff

logging.basicConfig(level=logging.INFO)  # Show API researcher activity
logger = logging.getLogger(__name__)


def load_test_case(test_num):
    """Load a specific test case."""
    pdf_path = f"golden_dataset/pdfs/test_{test_num:02d}_*.pdf"
    gt_path = f"golden_dataset/ground_truth/test_{test_num:02d}_annotations.json"
    
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


def run_takeoff_with_api(pdf_path: str):
    """
    Run takeoff using full system with API researcher.
    
    Uses the same main agent as baseline but with API researcher
    integrated into Supervisor for low-confidence fallback.
    """
    print("   🤖 Running takeoff with API augmentation...")
    
    # Run full takeoff (includes Supervisor with API researcher)
    result = run_takeoff(pdf_path)
    
    # Extract results
    takeoff_data = result.get("takeoff_result", {})
    researcher_results = result.get("researcher_results", {})
    
    # Check if API was used
    api_used = any(
        res.get("api_augmented", False) 
        for res in researcher_results.values()
    )
    
    if api_used:
        print("   🌐 API Researcher deployed - external standards retrieved!")
    else:
        print("   📚 Local knowledge base sufficient")
    
    # Collect all retrieved contexts
    all_contexts = []
    for researcher_name, res in researcher_results.items():
        contexts = res.get("retrieved_context", [])
        all_contexts.extend(contexts)
        
        if res.get("api_augmented"):
            logger.info(
                f"   [{researcher_name}] augmented with "
                f"{len(res.get('retrieved_context', []))} total contexts"
            )
    
    return {
        "takeoff_result": takeoff_data,
        "researcher_results": researcher_results,
        "retrieved_contexts": all_contexts,
        "api_used": api_used
    }


def main():
    """Run API-augmented custom evaluation."""
    print("\n" + "="*60)
    print("API-AUGMENTED CUSTOM EVALUATION")
    print("Testing hybrid RAG: Local KB + External API Fallback")
    print("="*60)
    print()
    
    all_scores = {}
    
    # Run on all test cases
    for test_num in [1, 2, 3, 4, 5]:
        print(f"📄 Test {test_num:02d}")
        print("-" * 60)
        
        test_case = load_test_case(test_num)
        if not test_case:
            print(f"   ⚠️  Test case {test_num:02d} not found, skipping")
            print()
            continue
        
        print(f"   PDF: {test_case['pdf_name']}")
        print(f"   Challenge: {test_case['ground_truth']['description']}")
        print()
        
        # Run takeoff with API augmentation
        result = run_takeoff_with_api(test_case["pdf_path"])
        
        takeoff_data = result["takeoff_result"]
        all_contexts = result["retrieved_contexts"]
        api_used = result["api_used"]
        
        print(f"   ✅ Complete")
        print(f"      Pipes: {takeoff_data.get('summary', {}).get('total_pipes', 0)}")
        print(f"      Contexts: {len(all_contexts)}")
        print(f"      API Used: {'Yes' if api_used else 'No'}")
        print()
        
        # Evaluate with custom metrics
        print("   📊 Custom Metrics:")
        scores = evaluate_takeoff_custom(
            predicted=takeoff_data,
            expected=test_case["ground_truth"],
            retrieved_contexts=all_contexts
        )
        
        # Store scores
        test_key = f"test_{test_num:02d}"
        all_scores[test_key] = {
            "scores": scores,
            "api_used": api_used,
            "pdf_name": test_case["pdf_name"]
        }
        
        # Print summary
        print(f"      Pipe Count: {scores['pipe_count_accuracy']:.1%}")
        print(f"      Materials: {scores['material_accuracy']:.1%}")
        print(f"      Elevations: {scores['elevation_accuracy']:.1%}")
        print(f"      RAG Retrieval: {scores['rag_retrieval_quality']:.1%}")
        print(f"      Overall: {scores['overall_accuracy']:.1%}")
        
        if scores['overall_accuracy'] >= 0.90:
            print("      ✅ EXCELLENT")
        elif scores['overall_accuracy'] >= 0.75:
            print("      ✅ GOOD")
        else:
            print("      ⚠️  NEEDS IMPROVEMENT")
        
        print()
    
    # Calculate averages
    avg_scores = {
        "pipe_count_accuracy": 0.0,
        "material_accuracy": 0.0,
        "elevation_accuracy": 0.0,
        "rag_retrieval_quality": 0.0,
        "overall_accuracy": 0.0
    }
    
    for test_data in all_scores.values():
        scores = test_data["scores"]
        for metric in avg_scores.keys():
            avg_scores[metric] += scores[metric]
    
    num_tests = len(all_scores)
    if num_tests > 0:
        for metric in avg_scores.keys():
            avg_scores[metric] /= num_tests
    
    # Print overall results
    print("="*60)
    print("OVERALL RESULTS")
    print("="*60)
    print()
    print(format_custom_results_table(avg_scores))
    print()
    
    print("Key Highlights:")
    print(f"  • Average RAG Retrieval Quality: {avg_scores['rag_retrieval_quality']:.1%}")
    print(f"  • Average Overall Accuracy: {avg_scores['overall_accuracy']:.1%}")
    
    # Count API usage
    api_usage_count = sum(1 for test_data in all_scores.values() if test_data["api_used"])
    print(f"  • API Researcher Deployed: {api_usage_count}/{num_tests} tests")
    print()
    
    # Save results
    results_file = Path("golden_dataset/api_augmented_custom.json")
    output = {
        "method": "api_augmented",
        "description": "Hybrid RAG with Tavily API fallback for unknown materials",
        "test_results": all_scores,
        "averages": avg_scores,
        "api_usage": {
            "tests_using_api": api_usage_count,
            "total_tests": num_tests,
            "percentage": api_usage_count / num_tests if num_tests > 0 else 0.0
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Results saved to: {results_file}")
    print()
    
    if avg_scores['overall_accuracy'] >= 0.90:
        print("🎉 OUTSTANDING! API augmentation working excellently!")
    elif avg_scores['overall_accuracy'] >= 0.80:
        print("✅ STRONG! API augmentation shows clear improvement!")
    else:
        print("⚠️  Review API integration - may need tuning")
    
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

