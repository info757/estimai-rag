#!/usr/bin/env python3
"""
Test Vision agents directly to debug detection issues.
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, '/Users/williamholt/estimai-rag')

from app.vision.coordinator import VisionCoordinator


async def main():
    """Test Vision agents on test_06."""
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return
    
    coordinator = VisionCoordinator()
    
    print("=" * 60)
    print("Testing Multi-Vision Agent System")
    print("=" * 60)
    
    pdf_path = "golden_dataset/pdfs/test_06_realistic_site.pdf"
    
    print(f"\nAnalyzing: {pdf_path}")
    print("Deploying agents: plan_pipes, profile_pipes")
    print("DPI: 300")
    print("\n")
    
    # Analyze
    results = await coordinator.analyze_multipage(
        pdf_path=pdf_path,
        max_pages=1,
        agents_to_deploy=["plan_pipes", "profile_pipes"],
        dpi=300
    )
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    print(f"\nTotal pipes detected: {results['total_pipes']}")
    print(f"Pages processed: {results['num_pages_processed']}")
    print(f"Discipline breakdown: {results.get('discipline_counts', {})}")
    
    print("\nPage Summaries:")
    for i, summary in enumerate(results.get('page_summaries', [])):
        print(f"  Page {i}: {summary}")
    
    print("\nDetected Pipes:")
    for i, pipe in enumerate(results.get('pipes', [])[:15], 1):
        print(f"  {i}. {pipe.get('discipline', '?')} - "
              f"{pipe.get('diameter_in', '?')}\" {pipe.get('material', '?')} - "
              f"{pipe.get('length_ft', '?')} LF")
    
    print("\n" + "=" * 60)
    print(f"TARGET: 7 pipes | DETECTED: {results['total_pipes']}")
    print("=" * 60)
    
    # Save detailed results
    import json
    with open('test_vision_agents_debug.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Detailed results saved to: test_vision_agents_debug.json")


if __name__ == "__main__":
    asyncio.run(main())

