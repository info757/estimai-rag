#!/usr/bin/env python3
"""
Test retrieval quality directly (without full takeoff).

Tests how well different retrieval methods find expected keywords
in construction standards.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import List, Dict
from app.rag.retriever import HybridRetriever


def test_retrieval(queries: List[str], retriever, expected_keywords: List[str], k: int = 10) -> Dict:
    """
    Test if retriever finds all expected keywords.
    
    Args:
        queries: List of test queries
        retriever: Retriever instance
        expected_keywords: Keywords that should be found
        k: Number of results to retrieve per query
    
    Returns:
        Dict with recall score, keywords found, and details
    """
    # Retrieve for all queries
    all_contexts = []
    for query in queries:
        contexts = retriever.retrieve_hybrid(query, k=k)
        all_contexts.extend([c['content'] for c in contexts])
    
    # Combine all retrieved text
    all_text = " ".join(all_contexts).lower()
    
    # Check which keywords were found
    found_keywords = []
    missing_keywords = []
    
    for keyword in expected_keywords:
        if keyword.lower() in all_text:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Calculate recall
    recall = len(found_keywords) / len(expected_keywords) if expected_keywords else 0.0
    
    return {
        "recall": recall,
        "found_count": len(found_keywords),
        "total_count": len(expected_keywords),
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords,
        "contexts_retrieved": len(set(all_contexts))
    }


def test_semantic_only(queries: List[str], retriever, expected_keywords: List[str], k: int = 10) -> Dict:
    """Test with semantic search only (no BM25)."""
    all_contexts = []
    for query in queries:
        contexts = retriever.retrieve_semantic(query, k=k)
        all_contexts.extend([c['content'] for c in contexts])
    
    all_text = " ".join(all_contexts).lower()
    
    found_keywords = []
    missing_keywords = []
    
    for keyword in expected_keywords:
        if keyword.lower() in all_text:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    recall = len(found_keywords) / len(expected_keywords) if expected_keywords else 0.0
    
    return {
        "recall": recall,
        "found_count": len(found_keywords),
        "total_count": len(expected_keywords),
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords,
        "contexts_retrieved": len(set(all_contexts))
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RETRIEVAL QUALITY TEST")
    print("="*60)
    print()
    
    # Load test case
    with open("golden_dataset/ground_truth/test_04_annotations.json", "r") as f:
        test_case = json.load(f)
    
    expected_keywords = test_case["expected_retrieval_keywords"]
    
    print(f"Test: {test_case['description']}")
    print(f"Expected keywords: {len(expected_keywords)}")
    print()
    
    # Test queries focusing on abbreviations
    test_queries = [
        "MH manhole construction specifications",
        "SSMH sanitary sewer manhole standards",
        "CB catch basin storm drainage",
        "DI ductile iron pipe or drain inlet",
        "RCP reinforced concrete pipe specifications",
        "HDPE high-density polyethylene pipe",
        "IE invert elevation definitions",
        "FES flared end section outfall",
        "STA station stationing alignment",
        "CL centerline road pipe"
    ]
    
    # Initialize retriever
    retriever = HybridRetriever()
    
    # Test 1: Semantic only (baseline)
    print("1️⃣  BASELINE: Semantic Search Only")
    print("-" * 60)
    baseline_results = test_semantic_only(test_queries, retriever, expected_keywords, k=5)
    
    print(f"Recall: {baseline_results['recall']:.1%}")
    print(f"Found: {baseline_results['found_count']}/{baseline_results['total_count']} keywords")
    print(f"Unique contexts: {baseline_results['contexts_retrieved']}")
    
    if baseline_results['missing_keywords']:
        print(f"\nMissing keywords:")
        for kw in baseline_results['missing_keywords'][:5]:
            print(f"  - {kw}")
        if len(baseline_results['missing_keywords']) > 5:
            print(f"  ... and {len(baseline_results['missing_keywords']) - 5} more")
    
    print()
    
    # Test 2: Hybrid (BM25 + Semantic)
    print("2️⃣  ADVANCED: Hybrid (BM25 + Semantic)")
    print("-" * 60)
    advanced_results = test_retrieval(test_queries, retriever, expected_keywords, k=5)
    
    print(f"Recall: {advanced_results['recall']:.1%}")
    print(f"Found: {advanced_results['found_count']}/{advanced_results['total_count']} keywords")
    print(f"Unique contexts: {advanced_results['contexts_retrieved']}")
    
    if advanced_results['missing_keywords']:
        print(f"\nMissing keywords:")
        for kw in advanced_results['missing_keywords']:
            print(f"  - {kw}")
    else:
        print("\n✅ ALL keywords found!")
    
    print()
    
    # Calculate improvement
    improvement = advanced_results['recall'] - baseline_results['recall']
    improvement_pct = improvement * 100
    
    print("="*60)
    print("RESULTS COMPARISON")
    print("="*60)
    print(f"Baseline (semantic only):    {baseline_results['recall']:.1%}")
    print(f"Advanced (hybrid):           {advanced_results['recall']:.1%}")
    print(f"Improvement:                 +{improvement:.1%} ({improvement_pct:+.1f} percentage points)")
    print()
    
    # Save results
    results = {
        "test_case": test_case["pdf_name"],
        "description": test_case["description"],
        "baseline": {
            "method": "semantic_only",
            "recall": baseline_results['recall'],
            "keywords_found": f"{baseline_results['found_count']}/{baseline_results['total_count']}",
            "missing": baseline_results['missing_keywords']
        },
        "advanced": {
            "method": "hybrid_bm25_semantic",
            "recall": advanced_results['recall'],
            "keywords_found": f"{advanced_results['found_count']}/{advanced_results['total_count']}",
            "missing": advanced_results['missing_keywords']
        },
        "improvement": {
            "absolute": improvement,
            "percentage_points": improvement_pct
        }
    }
    
    output_file = Path("golden_dataset/retrieval_improvement_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Results saved to: {output_file}")
    print()
    
    if improvement >= 0.15:
        print("🎉 SIGNIFICANT IMPROVEMENT! Advanced retrieval is clearly better.")
    elif improvement >= 0.05:
        print("✅ MEASURABLE IMPROVEMENT! Advanced retrieval shows gains.")
    else:
        print("📊 Both methods perform similarly on this test.")

