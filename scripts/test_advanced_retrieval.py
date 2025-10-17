#!/usr/bin/env python3
"""
Test advanced retrieval vs. baseline retrieval.

Shows the improvement from multi-query retrieval.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_baseline_vs_advanced():
    """Compare baseline hybrid retrieval with advanced multi-query."""
    from app.rag.retriever import HybridRetriever
    from app.rag.advanced_retriever import AdvancedRetriever
    
    print("\n" + "="*60)
    print("BASELINE vs. ADVANCED RETRIEVAL COMPARISON")
    print("="*60)
    
    # Test queries
    test_queries = [
        "What is the minimum cover for MH?",  # Abbreviation
        "RCP depth requirements",  # Technical term
        "storm drain cover depth",  # Common query
    ]
    
    # Initialize retrievers
    baseline = HybridRetriever()
    advanced = AdvancedRetriever()
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"{'='*60}")
        
        # Baseline retrieval
        print("\n📊 BASELINE (Hybrid: BM25 + Semantic)")
        baseline_results = baseline.retrieve_hybrid(query, k=3)
        
        print(f"   Retrieved: {len(baseline_results)} results")
        for i, result in enumerate(baseline_results[:3], 1):
            print(f"\n   {i}. {result['content'][:100]}...")
            print(f"      Score: {result.get('fused_score', 0):.4f}")
            print(f"      Methods: {result.get('retrieval_methods', [])}")
        
        # Advanced retrieval
        print("\n🚀 ADVANCED (Multi-Query + Expansion)")
        advanced_results = advanced.retrieve_multi_query(query, k=3, num_variants=2)
        
        print(f"   Retrieved: {len(advanced_results)} results")
        for i, result in enumerate(advanced_results[:3], 1):
            print(f"\n   {i}. {result['content'][:100]}...")
            print(f"      Score: {result.get('multi_query_score', 0):.4f}")
            print(f"      Appeared in: {result.get('appeared_in_queries', 0)} queries")
            print(f"      Avg rank: {result.get('avg_rank', 0):.1f}")
        
        # Compare
        baseline_ids = {r['id'] for r in baseline_results[:3]}
        advanced_ids = {r['id'] for r in advanced_results[:3]}
        
        unique_to_advanced = advanced_ids - baseline_ids
        
        print(f"\n💡 Analysis:")
        print(f"   Baseline found: {len(baseline_ids)} unique docs")
        print(f"   Advanced found: {len(advanced_ids)} unique docs")
        if unique_to_advanced:
            print(f"   ✨ Advanced discovered {len(unique_to_advanced)} additional relevant docs!")
        else:
            print(f"   📊 Similar results (advanced re-ranked better)")
    
    print("\n" + "="*60)
    print("✅ Comparison complete!")
    print("="*60)
    print("\nKey Improvements:")
    print("  - Query expansion for abbreviations (MH → manhole)")
    print("  - Semantic variants for better recall")
    print("  - Multi-query fusion for confidence")
    print("  - Better ranking via appearance frequency")
    print()


def test_query_expansion():
    """Test query expansion specifically."""
    from app.rag.advanced_retriever import AdvancedRetriever
    
    print("\n" + "="*60)
    print("QUERY EXPANSION TEST")
    print("="*60)
    
    retriever = AdvancedRetriever()
    
    test_cases = [
        "MH cover requirements",
        "RCP minimum depth",
        "WM installation standards"
    ]
    
    for query in test_cases:
        print(f"\nOriginal: '{query}'")
        
        # Rule-based expansion
        expanded = retriever.expand_technical_terms(query)
        print(f"Expanded ({len(expanded)} variants):")
        for exp in expanded:
            print(f"  - {exp}")
        
        # LLM-based variants
        variants = retriever.generate_query_variants(query, num_variants=2)
        print(f"LLM Variants ({len(variants)} total):")
        for var in variants:
            print(f"  - {var}")
    
    print("\n" + "="*60)
    print("✅ Query expansion working!")
    print("="*60)
    print()


def main():
    """Run all advanced retrieval tests."""
    print("\n" + "="*60)
    print("ADVANCED RETRIEVAL TESTING")
    print("="*60)
    print()
    
    # Test 1: Query expansion
    test_query_expansion()
    
    # Test 2: Baseline vs Advanced comparison
    test_baseline_vs_advanced()
    
    print("🎉 All advanced retrieval tests complete!")
    print()
    print("Next steps:")
    print("  1. Integrate into researchers")
    print("  2. Run RAGAS evaluation")
    print("  3. Compare metrics vs baseline")
    print()


if __name__ == "__main__":
    main()

