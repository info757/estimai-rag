#!/usr/bin/env python3
"""
Run advanced RAGAS evaluation with multi-query retrieval.

Compares performance against baseline to show improvement.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from app.evaluation.ragas_eval import RAGASEvaluator, compare_results_table
from app.agents.main_agent import MainAgent
from app.rag.advanced_retriever import AdvancedRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_golden_dataset(limit=1):
    """Load test PDFs and their ground truth (limited for speed)."""
    dataset_dir = Path("golden_dataset")
    pdfs_dir = dataset_dir / "pdfs"
    gt_dir = dataset_dir / "ground_truth"
    
    test_cases = []
    
    # Find all PDFs
    pdf_files = sorted(pdfs_dir.glob("test_*.pdf"))
    
    # Limit for faster evaluation
    pdf_files = pdf_files[:limit]
    
    for pdf_file in pdf_files:
        # Find corresponding ground truth
        test_num = pdf_file.stem.split('_')[1]  # Extract number
        gt_file = gt_dir / f"test_{test_num}_annotations.json"
        
        if not gt_file.exists():
            logger.warning(f"No ground truth for {pdf_file.name}")
            continue
        
        with open(gt_file, 'r') as f:
            ground_truth = json.load(f)
        
        test_cases.append({
            "pdf_path": str(pdf_file),
            "pdf_name": pdf_file.name,
            "ground_truth": ground_truth
        })
    
    logger.info(f"Loaded {len(test_cases)} test cases")
    return test_cases


def patch_researchers_with_advanced_retrieval():
    """
    Temporarily patch researchers to use advanced retriever.
    
    This allows us to compare baseline vs advanced without
    modifying the core code.
    """
    from app.agents.researchers import base_researcher
    
    # Create advanced retriever instance
    advanced = AdvancedRetriever()
    
    # Store original method
    original_retrieve = base_researcher.BaseResearcher.retrieve_context
    
    # Patch with advanced retrieval
    def advanced_retrieve_context(self, query, k=5, category=None):
        """Patched method using advanced multi-query retrieval."""
        logger.info(f"[{self.researcher_name}] Using ADVANCED retrieval")
        results = advanced.retrieve_multi_query(
            query=query,
            k=k,
            discipline=self.discipline,
            category=category,
            num_variants=3
        )
        return results
    
    base_researcher.BaseResearcher.retrieve_context = advanced_retrieve_context
    
    logger.info("✅ Researchers patched to use advanced retrieval")
    
    return original_retrieve


def restore_baseline_retrieval(original_method):
    """Restore baseline retrieval method."""
    from app.agents.researchers import base_researcher
    base_researcher.BaseResearcher.retrieve_context = original_method
    logger.info("✅ Restored baseline retrieval")


def run_takeoff_with_advanced(test_case):
    """Run takeoff with advanced retrieval."""
    from app.agents.main_agent import run_takeoff
    
    pdf_path = test_case["pdf_path"]
    pdf_name = test_case["pdf_name"]
    
    logger.info(f"Running takeoff (ADVANCED) on {pdf_name}...")
    
    try:
        result = run_takeoff(pdf_path=pdf_path)
        logger.info(f"✅ Takeoff complete for {pdf_name}")
        return result
    except Exception as e:
        logger.error(f"❌ Takeoff failed for {pdf_name}: {e}")
        return None


def main():
    """Run advanced RAGAS evaluation and compare with baseline."""
    print("\n" + "="*60)
    print("ADVANCED RAGAS EVALUATION (Multi-Query Retrieval)")
    print("="*60)
    print()
    
    # Load baseline results
    baseline_file = Path("golden_dataset/baseline_results.json")
    if not baseline_file.exists():
        print("❌ Baseline results not found!")
        print("   Run baseline evaluation first: python scripts/run_baseline_eval.py")
        return 1
    
    with open(baseline_file, 'r') as f:
        baseline_scores = json.load(f)
    
    print("📊 Loaded baseline results:")
    for metric, score in baseline_scores.items():
        print(f"   {metric}: {score:.4f}")
    print()
    
    # Patch researchers to use advanced retrieval
    print("🔧 Patching researchers with advanced retrieval...")
    original_method = patch_researchers_with_advanced_retrieval()
    print()
    
    try:
        # Load golden dataset
        print("📚 Loading golden dataset...")
        test_cases = load_golden_dataset()
        print(f"   Loaded {len(test_cases)} test PDFs")
        print()
        
        # Run takeoff with advanced retrieval
        print("🤖 Running takeoff with ADVANCED retrieval...")
        ragas_test_cases = []
        
        for test_case in test_cases:
            pdf_name = test_case["pdf_name"]
            print(f"\n   Processing: {pdf_name}")
            
            # Run takeoff
            takeoff_result = run_takeoff_with_advanced(test_case)
            
            if not takeoff_result:
                print(f"      ❌ Skipping (takeoff failed)")
                continue
            
            # Create RAGAS test case
            evaluator = RAGASEvaluator()
            ragas_case = evaluator.create_test_case_from_takeoff(
                pdf_name=pdf_name,
                takeoff_result=takeoff_result,
                ground_truth=test_case["ground_truth"]
            )
            
            ragas_test_cases.append(ragas_case)
            print(f"      ✅ Test case prepared")
        
        print(f"\n   Total: {len(ragas_test_cases)} test cases ready")
        print()
        
        # Run RAGAS evaluation
        print("📊 Running RAGAS evaluation with advanced retrieval...")
        evaluator = RAGASEvaluator()
        
        advanced_scores = evaluator.evaluate_takeoff(ragas_test_cases)
        
        print("\n" + "="*60)
        print("ADVANCED EVALUATION RESULTS")
        print("="*60)
        print()
        
        # Show comparison table
        print(compare_results_table(baseline_scores, advanced_scores))
        print()
        
        # Save results
        advanced_file = Path("golden_dataset/advanced_results.json")
        with open(advanced_file, 'w') as f:
            json.dump(advanced_scores, f, indent=2)
        
        print(f"✅ Results saved to: {advanced_file}")
        print()
        
        # Analysis
        baseline_avg = sum(baseline_scores.values()) / len(baseline_scores)
        advanced_avg = sum(advanced_scores.values()) / len(advanced_scores)
        improvement = advanced_avg - baseline_avg
        improvement_pct = (improvement / baseline_avg * 100) if baseline_avg > 0 else 0
        
        print("📊 SUMMARY:")
        print(f"   Baseline Average: {baseline_avg:.4f}")
        print(f"   Advanced Average: {advanced_avg:.4f}")
        print(f"   Improvement: {improvement:+.4f} ({improvement_pct:+.1f}%)")
        print()
        
        if improvement > 0:
            print("✅ ADVANCED RETRIEVAL SHOWS IMPROVEMENT!")
            print("   Multi-query and expansion are working!")
        elif improvement == 0:
            print("⚠️  NO CHANGE - Both methods perform similarly")
        else:
            print("❌ BASELINE PERFORMED BETTER - Investigate advanced retrieval")
        
        print()
        
        return 0
    
    finally:
        # Always restore baseline retrieval
        restore_baseline_retrieval(original_method)
        print("🔧 Restored baseline retrieval")


if __name__ == "__main__":
    sys.exit(main())

