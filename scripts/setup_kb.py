#!/usr/bin/env python3
"""
Initialize the construction knowledge base in Qdrant.

This script:
1. Loads construction standards from JSON files
2. Creates embeddings
3. Populates Qdrant collection
4. Builds BM25 index

Run this before starting the application.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.knowledge_base import load_knowledge_base
from app.rag.retriever import HybridRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize knowledge base."""
    print("=" * 60)
    print("EstimAI-RAG Knowledge Base Initialization")
    print("=" * 60)
    print()
    
    # Step 1: Load construction standards
    print("📚 Step 1: Loading construction standards...")
    try:
        kb = load_knowledge_base()
        print(f"   ✅ Loaded {len(kb.standards)} standards")
        
        # Show stats
        stats = kb.get_stats()
        print(f"\n   📊 Statistics:")
        print(f"      Total standards: {stats['total_standards']}")
        print(f"      By discipline:")
        for disc, count in stats['by_discipline'].items():
            print(f"        - {disc}: {count}")
        print(f"      By category:")
        for cat, count in stats['by_category'].items():
            print(f"        - {cat}: {count}")
        print()
    
    except Exception as e:
        print(f"   ❌ Error loading standards: {e}")
        return 1
    
    # Step 2: Initialize Qdrant
    print("🔌 Step 2: Connecting to Qdrant...")
    try:
        retriever = HybridRetriever()
        print(f"   ✅ Connected to {retriever.qdrant_url}")
        print()
    except Exception as e:
        print(f"   ❌ Error connecting to Qdrant: {e}")
        print(f"\n   💡 Make sure Qdrant is running:")
        print(f"      docker run -p 6333:6333 qdrant/qdrant")
        return 1
    
    # Step 3: Create collection and index standards
    print("📦 Step 3: Creating Qdrant collection and indexing...")
    try:
        standards_data = kb.get_standards_with_metadata()
        retriever.create_collection(standards_data)
        print(f"   ✅ Collection created and indexed")
        print()
    except Exception as e:
        print(f"   ❌ Error creating collection: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 4: Verify setup
    print("🔍 Step 4: Verifying setup...")
    try:
        stats = retriever.get_stats()
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Vectors: {stats['vectors_count']}")
        print(f"   Points: {stats['points_count']}")
        print(f"   BM25 docs: {stats['bm25_documents']}")
        print()
    except Exception as e:
        print(f"   ⚠️  Could not verify: {e}")
        print()
    
    # Step 5: Test retrieval
    print("🧪 Step 5: Testing hybrid retrieval...")
    try:
        test_query = "storm drain cover depth requirements"
        results = retriever.retrieve_hybrid(test_query, k=3)
        
        print(f"   Query: '{test_query}'")
        print(f"   Results: {len(results)}")
        if results:
            print(f"\n   Top result:")
            top = results[0]
            print(f"     Content: {top['content'][:100]}...")
            print(f"     Score: {top['fused_score']:.4f}")
            print(f"     Methods: {top['retrieval_methods']}")
        print()
    except Exception as e:
        print(f"   ⚠️  Test query failed: {e}")
        print()
    
    # Success!
    print("=" * 60)
    print("✅ Knowledge Base Initialization Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Start the backend: uvicorn app.main:app --reload")
    print("  2. Test retrieval: python -c \"from app.rag.retriever import HybridRetriever; r = HybridRetriever(); print(r.get_stats())\"")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

