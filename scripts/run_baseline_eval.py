#!/usr/bin/env python3
"""
Run baseline RAGAS evaluation on golden dataset.

Uses standard hybrid retrieval (BM25 + semantic) without multi-query.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from app.evaluation.ragas_eval import RAGASEvaluator, format_results_table
from app.agents.main_agent import run_takeoff

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_golden_dataset():
    """Load all test PDFs and their ground truth."""
    dataset_dir = Path("golden_dataset")
    pdfs_dir = dataset_dir / "pdfs"
    gt_dir = dataset_dir / "ground_truth"
    
    test_cases = []
    
    # Find all PDFs
    pdf_files = sorted(pdfs_dir.glob("test_*.pdf"))
    
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


def run_takeoff_on_test_case(test_case):
    """Run takeoff on a single test case."""
    pdf_path = test_case["pdf_path"]
    pdf_name = test_case["pdf_name"]
    
    logger.info(f"Running takeoff on {pdf_name}...")
    
    try:
        result = run_takeoff(pdf_path=pdf_path)
        logger.info(f"✅ Takeoff complete for {pdf_name}")
        return result
    except Exception as e:
        logger.error(f"❌ Takeoff failed for {pdf_name}: {e}")
        return None


def main():
    """Run baseline RAGAS evaluation."""
    print("\n" + "="*60)
    print("BASELINE RAGAS EVALUATION")
    print("="*60)
    print()
    
    # Load golden dataset
    print("📚 Loading golden dataset...")
    test_cases = load_golden_dataset()
    print(f"   Loaded {len(test_cases)} test PDFs")
    print()
    
    # Run takeoff on each test case
    print("🤖 Running takeoff on test cases...")
    ragas_test_cases = []
    
    for test_case in test_cases:
        pdf_name = test_case["pdf_name"]
        print(f"\n   Processing: {pdf_name}")
        
        # Run takeoff
        takeoff_result = run_takeoff_on_test_case(test_case)
        
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
    
    print(f"\n   Total: {len(ragas_test_cases)} test cases ready for RAGAS")
    print()
    
    # Run RAGAS evaluation
    print("📊 Running RAGAS evaluation...")
    evaluator = RAGASEvaluator()
    
    try:
        scores = evaluator.evaluate_takeoff(ragas_test_cases)
        
        print("\n" + "="*60)
        print("BASELINE EVALUATION RESULTS")
        print("="*60)
        print()
        print(format_results_table(scores))
        print()
        
        # Save results
        results_file = Path("golden_dataset/baseline_results.json")
        with open(results_file, 'w') as f:
            json.dump(scores, f, indent=2)
        
        print(f"✅ Results saved to: {results_file}")
        print()
        
        # Analysis
        avg_score = sum(scores.values()) / len(scores)
        print(f"📊 Average Score: {avg_score:.4f}")
        
        if avg_score >= 0.75:
            print("✅ EXCELLENT! Above 0.75 threshold")
        elif avg_score >= 0.60:
            print("⚠️  GOOD - Room for improvement with advanced retrieval")
        else:
            print("❌ NEEDS IMPROVEMENT - Check retrieval and prompts")
        
        print()
        
        return 0
    
    except Exception as e:
        print(f"\n❌ RAGAS evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

