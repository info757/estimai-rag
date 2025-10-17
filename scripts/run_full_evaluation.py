#!/usr/bin/env python3
"""
Run complete RAGAS evaluation - baseline AND advanced.

This convenience script:
1. Runs baseline evaluation (hybrid retrieval)
2. Runs advanced evaluation (multi-query retrieval)
3. Generates comparison table
4. Saves all results
5. Provides analysis and recommendations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import json


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=False,
        text=True
    )
    
    if result.returncode != 0:
        print(f"\n❌ Failed: {description}")
        return False
    
    return True


def load_results():
    """Load baseline and advanced results."""
    baseline_file = Path("golden_dataset/baseline_results.json")
    advanced_file = Path("golden_dataset/advanced_results.json")
    
    baseline = None
    advanced = None
    
    if baseline_file.exists():
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
    
    if advanced_file.exists():
        with open(advanced_file, 'r') as f:
            advanced = json.load(f)
    
    return baseline, advanced


def generate_final_report(baseline, advanced):
    """Generate final comparison report."""
    print("\n" + "="*60)
    print("FINAL RAGAS EVALUATION REPORT")
    print("="*60)
    print()
    
    if not baseline:
        print("❌ Baseline results not found")
        return
    
    if not advanced:
        print("⚠️  Advanced results not found - showing baseline only")
        print("\nBaseline Results:")
        for metric, score in baseline.items():
            print(f"  {metric}: {score:.4f}")
        return
    
    # Generate comparison table
    print("📊 BASELINE vs. ADVANCED COMPARISON")
    print()
    print("| Metric | Baseline | Advanced | Improvement |")
    print("|--------|----------|----------|-------------|")
    
    improvements = {}
    for metric in baseline.keys():
        base_score = baseline.get(metric, 0.0)
        adv_score = advanced.get(metric, 0.0)
        improvement = adv_score - base_score
        improvement_pct = (improvement / base_score * 100) if base_score > 0 else 0
        
        improvements[metric] = improvement
        
        print(f"| {metric} | {base_score:.4f} | {adv_score:.4f} | {improvement:+.4f} ({improvement_pct:+.1f}%) |")
    
    print()
    
    # Calculate averages
    baseline_avg = sum(baseline.values()) / len(baseline)
    advanced_avg = sum(advanced.values()) / len(advanced)
    total_improvement = advanced_avg - baseline_avg
    total_improvement_pct = (total_improvement / baseline_avg * 100) if baseline_avg > 0 else 0
    
    print("📊 SUMMARY:")
    print(f"  Baseline Average: {baseline_avg:.4f}")
    print(f"  Advanced Average: {advanced_avg:.4f}")
    print(f"  Total Improvement: {total_improvement:+.4f} ({total_improvement_pct:+.1f}%)")
    print()
    
    # Analysis
    if total_improvement > 0.05:
        print("✅ SIGNIFICANT IMPROVEMENT!")
        print("   Multi-query retrieval is highly effective")
    elif total_improvement > 0:
        print("✅ POSITIVE IMPROVEMENT")
        print("   Multi-query shows measurable gains")
    elif total_improvement == 0:
        print("⚠️  NO CHANGE")
        print("   Both methods perform similarly")
    else:
        print("❌ BASELINE BETTER")
        print("   Investigate advanced retrieval implementation")
    
    print()
    
    # Metric-specific insights
    print("📈 METRIC INSIGHTS:")
    print()
    
    best_metric = max(improvements.items(), key=lambda x: x[1])
    worst_metric = min(improvements.items(), key=lambda x: x[1])
    
    print(f"  Best Improvement: {best_metric[0]} ({best_metric[1]:+.4f})")
    if best_metric[0] in ["context_recall", "context_precision"]:
        print(f"    ✅ Multi-query improved retrieval quality!")
    
    print()
    print(f"  Smallest Improvement: {worst_metric[0]} ({worst_metric[1]:+.4f})")
    if worst_metric[0] in ["faithfulness", "answer_relevancy"]:
        print(f"    💡 These depend on LLM usage, not retrieval method")
    
    print()
    
    # Save combined report
    report = {
        "baseline": baseline,
        "advanced": advanced,
        "improvements": improvements,
        "summary": {
            "baseline_average": baseline_avg,
            "advanced_average": advanced_avg,
            "total_improvement": total_improvement,
            "total_improvement_pct": total_improvement_pct
        }
    }
    
    report_file = Path("golden_dataset/evaluation_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Full report saved to: {report_file}")
    print()


def main():
    """Run complete evaluation workflow."""
    print("\n" + "="*60)
    print("COMPLETE RAGAS EVALUATION WORKFLOW")
    print("="*60)
    print()
    print("This will:")
    print("  1. Run baseline evaluation (standard hybrid retrieval)")
    print("  2. Run advanced evaluation (multi-query retrieval)")
    print("  3. Generate comparison tables")
    print("  4. Save all results")
    print()
    
    input("Press Enter to continue...")
    
    # Run baseline
    success = run_command(
        "python scripts/run_baseline_eval.py",
        "STEP 1: Baseline Evaluation"
    )
    
    if not success:
        print("\n❌ Baseline evaluation failed. Fix errors and try again.")
        return 1
    
    # Run advanced
    success = run_command(
        "python scripts/run_advanced_eval.py",
        "STEP 2: Advanced Evaluation"
    )
    
    if not success:
        print("\n❌ Advanced evaluation failed. Fix errors and try again.")
        return 1
    
    # Load and compare results
    print("\n" + "="*60)
    print("STEP 3: Generating Final Report")
    print("="*60)
    
    baseline, advanced = load_results()
    generate_final_report(baseline, advanced)
    
    # Final instructions
    print("\n" + "="*60)
    print("🎉 EVALUATION COMPLETE!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Copy results into docs/CERTIFICATION_REPORT.md")
    print("  2. Write 2-3 sentences analyzing the improvements")
    print("  3. Record demo video showing:")
    print("     - Upload test PDF")
    print("     - Show results")
    print("     - Show RAG context used")
    print("     - Show this comparison table")
    print()
    print("Files generated:")
    print("  - golden_dataset/baseline_results.json")
    print("  - golden_dataset/advanced_results.json")
    print("  - golden_dataset/evaluation_report.json")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

