#!/usr/bin/env python3
"""
Compare baseline vs advanced retrieval using custom metrics.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from app.evaluation.custom_metrics import evaluate_takeoff_custom
from app.agents.main_agent import MainAgent
from app.rag.advanced_retriever import AdvancedRetriever
from app.agents.researchers import base_researcher

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def run_with_baseline(pdf_path, ground_truth):
    """Run takeoff with baseline hybrid retrieval."""
    print("   Running with BASELINE retrieval (BM25 + Semantic)...")
    
    from app.agents.main_agent import run_takeoff
    result = run_takeoff(pdf_path)
    
    # Extract data
    takeoff_data = result.get("takeoff_result", {})
    researcher_results = result.get("researcher_results", {})
    
    # Get contexts
    contexts = []
    for res in researcher_results.values():
        contexts.extend(res.get("retrieved_context", []))
    
    # Evaluate
    scores = evaluate_takeoff_custom(takeoff_data, ground_truth, contexts)
    
    print(f"   ✅ Baseline complete: {scores['overall_accuracy']:.3f} overall")
    return scores


def run_with_advanced(pdf_path, ground_truth):
    """Run takeoff with advanced multi-query retrieval."""
    print("   Running with ADVANCED retrieval (Multi-Query + Expansion)...")
    
    # Patch researchers
    advanced = AdvancedRetriever()
    original = base_researcher.BaseResearcher.retrieve_context
    
    def advanced_retrieve(self, query, k=5, category=None):
        return advanced.retrieve_multi_query(
            query, k=k, discipline=self.discipline, category=category, num_variants=3
        )
    
    base_researcher.BaseResearcher.retrieve_context = advanced_retrieve
    
    try:
        from app.agents.main_agent import run_takeoff
        result = run_takeoff(pdf_path)
        
        # Extract data
        takeoff_data = result.get("takeoff_result", {})
        researcher_results = result.get("researcher_results", {})
        
        # Get contexts
        contexts = []
        for res in researcher_results.values():
            contexts.extend(res.get("retrieved_context", []))
        
        # Evaluate
        scores = evaluate_takeoff_custom(takeoff_data, ground_truth, contexts)
        
        print(f"   ✅ Advanced complete: {scores['overall_accuracy']:.3f} overall")
        return scores
    
    finally:
        # Restore
        base_researcher.BaseResearcher.retrieve_context = original


def main():
    """Compare baseline vs advanced."""
    print("\n" + "="*60)
    print("BASELINE vs ADVANCED COMPARISON")
    print("="*60)
    print()
    
    # Load test case
    test_num = 1
    pdf_path = f"golden_dataset/pdfs/test_01_simple_storm.pdf"
    gt_path = f"golden_dataset/ground_truth/test_01_annotations.json"
    
    with open(gt_path, 'r') as f:
        ground_truth = json.load(f)
    
    print(f"Test: {ground_truth['description']}")
    print()
    
    # Run baseline
    print("1️⃣  BASELINE EVALUATION")
    baseline_scores = run_with_baseline(pdf_path, ground_truth)
    print()
    
    # Run advanced
    print("2️⃣  ADVANCED EVALUATION")
    advanced_scores = run_with_advanced(pdf_path, ground_truth)
    print()
    
    # Comparison table
    print("="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    print()
    print("| Metric | Baseline | Advanced | Improvement |")
    print("|--------|----------|----------|-------------|")
    
    for metric in ["pipe_count_accuracy", "material_accuracy", "elevation_accuracy", "rag_retrieval_quality", "overall_accuracy"]:
        base = baseline_scores.get(metric, 0.0)
        adv = advanced_scores.get(metric, 0.0)
        diff = adv - base
        diff_pct = (diff / base * 100) if base > 0 else 0
        
        metric_name = metric.replace("_", " ").title()
        print(f"| {metric_name} | {base:.3f} | {adv:.3f} | {diff:+.3f} ({diff_pct:+.1f}%) |")
    
    print()
    
    # Save both
    Path("golden_dataset/baseline_custom.json").write_text(json.dumps(baseline_scores, indent=2))
    Path("golden_dataset/advanced_custom.json").write_text(json.dumps(advanced_scores, indent=2))
    
    print("✅ Results saved")
    print()
    
    # Analysis
    overall_improvement = advanced_scores["overall_accuracy"] - baseline_scores["overall_accuracy"]
    
    if overall_improvement > 0.05:
        print("🎉 SIGNIFICANT IMPROVEMENT with advanced retrieval!")
    elif overall_improvement > 0:
        print("✅ Positive improvement with advanced retrieval")
    else:
        print("📊 Both methods perform excellently (already at ceiling)")
    
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

