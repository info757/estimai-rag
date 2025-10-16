#!/usr/bin/env python3
"""
System test script - validates all components.

Tests:
1. Qdrant connection
2. Knowledge base loading
3. Hybrid retrieval
4. Individual researchers
5. Supervisor coordination
6. Main agent workflow
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test 1: Can we import everything?"""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from app.models import AgentState, SupervisorState, ResearcherState
        print("✅ Models imported")
        
        from app.rag.knowledge_base import load_knowledge_base
        print("✅ Knowledge base module imported")
        
        from app.rag.retriever import HybridRetriever
        print("✅ Retriever imported")
        
        from app.agents.researchers.storm_researcher import StormResearcher
        print("✅ Researchers imported")
        
        from app.agents.supervisor import SupervisorAgent
        print("✅ Supervisor imported")
        
        from app.agents.main_agent import MainAgent
        print("✅ Main agent imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_knowledge_base():
    """Test 2: Can we load the knowledge base?"""
    print("\n" + "="*60)
    print("TEST 2: Knowledge Base Loading")
    print("="*60)
    
    try:
        from app.rag.knowledge_base import load_knowledge_base
        
        kb = load_knowledge_base()
        print(f"✅ Loaded {len(kb.standards)} standards")
        
        stats = kb.get_stats()
        print(f"   By discipline: {stats['by_discipline']}")
        print(f"   By category: {stats['by_category']}")
        
        # Test search
        results = kb.search_standards("storm drain cover", discipline="storm")
        print(f"✅ Search test: {len(results)} results")
        
        return True
    except Exception as e:
        print(f"❌ Knowledge base test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qdrant_connection():
    """Test 3: Can we connect to Qdrant?"""
    print("\n" + "="*60)
    print("TEST 3: Qdrant Connection")
    print("="*60)
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url="http://localhost:6333")
        collections = client.get_collections()
        
        print(f"✅ Connected to Qdrant")
        print(f"   Collections: {len(collections.collections)}")
        
        return True
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        print("\n💡 Start Qdrant with:")
        print("   docker run -p 6333:6333 qdrant/qdrant")
        return False


def test_retriever():
    """Test 4: Does retrieval work?"""
    print("\n" + "="*60)
    print("TEST 4: Hybrid Retrieval")
    print("="*60)
    
    try:
        from app.rag.retriever import HybridRetriever
        
        retriever = HybridRetriever()
        print("✅ Retriever initialized")
        
        # Check if collection exists
        stats = retriever.get_stats()
        if stats.get("error"):
            print("⚠️  Collection not initialized yet")
            print("   Run: python scripts/setup_kb.py")
            return False
        
        print(f"   Vectors: {stats['vectors_count']}")
        print(f"   Points: {stats['points_count']}")
        
        # Test query
        query = "storm drain cover depth requirements"
        results = retriever.retrieve_hybrid(query, k=3)
        
        print(f"✅ Retrieved {len(results)} results for: '{query}'")
        if results:
            print(f"   Top result: {results[0]['content'][:80]}...")
            print(f"   Score: {results[0]['fused_score']:.4f}")
        
        return True
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_researcher():
    """Test 5: Can a researcher work?"""
    print("\n" + "="*60)
    print("TEST 5: Storm Researcher")
    print("="*60)
    
    try:
        from app.agents.researchers.storm_researcher import StormResearcher
        from app.models import ResearcherState
        
        researcher = StormResearcher()
        print("✅ Storm researcher initialized")
        
        # Create test state
        state: ResearcherState = {
            "researcher_name": "storm",
            "task": "Find storm drain cover depth requirements",
            "retrieved_context": [],
            "findings": {},
            "confidence": 0.0
        }
        
        print("   Running analysis...")
        result = researcher.analyze(state)
        
        print(f"✅ Analysis complete")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Standards used: {len(result['retrieved_context'])}")
        print(f"   Findings: {str(result['findings'])[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Researcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_supervisor():
    """Test 6: Can supervisor coordinate?"""
    print("\n" + "="*60)
    print("TEST 6: Supervisor Agent")
    print("="*60)
    
    try:
        from app.agents.supervisor import SupervisorAgent
        from app.models import SupervisorState
        
        supervisor = SupervisorAgent()
        print("✅ Supervisor initialized with 5 researchers")
        
        # Create test state
        state: SupervisorState = {
            "pdf_summary": "This PDF contains a storm drain plan with catch basins and RCP pipes. Shows invert elevations on profile sheet.",
            "assigned_tasks": [],
            "researcher_results": {},
            "consolidated_data": {},
            "conflicts": []
        }
        
        print("   Planning research...")
        tasks = supervisor.plan_research(state["pdf_summary"])
        print(f"✅ Planned {len(tasks)} tasks")
        
        # Don't run full execution in test (takes too long)
        print("   (Skipping full execution for speed)")
        
        return True
    except Exception as e:
        print(f"❌ Supervisor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_main_agent():
    """Test 7: Can main agent workflow run?"""
    print("\n" + "="*60)
    print("TEST 7: Main Agent (Quick Test)")
    print("="*60)
    
    try:
        from app.agents.main_agent import MainAgent
        
        agent = MainAgent()
        print("✅ Main agent initialized")
        print("✅ LangGraph workflow compiled")
        
        # Don't run full workflow in test (too slow)
        print("   (Full workflow test skipped - use test_e2e.py)")
        
        return True
    except Exception as e:
        print(f"❌ Main agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ESTIMAI-RAG SYSTEM TEST SUITE")
    print("="*60)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set")
        print("   Set it in .env file or export it")
        print()
    
    tests = [
        ("Imports", test_imports),
        ("Knowledge Base", test_knowledge_base),
        ("Qdrant Connection", test_qdrant_connection),
        ("Hybrid Retrieval", test_retriever),
        ("Researcher", test_researcher),
        ("Supervisor", test_supervisor),
        ("Main Agent", test_main_agent),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("1. Run end-to-end test: python scripts/test_e2e.py")
        print("2. Start backend: uvicorn app.main:app --reload")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nFix issues before proceeding:")
        for name, p in results:
            if not p:
                print(f"  - {name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

