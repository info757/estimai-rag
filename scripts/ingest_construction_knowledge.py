#!/usr/bin/env python3
"""
Ingest construction knowledge base into RAG.

Loads the generated construction_knowledge_base.json and adds it to the Qdrant
construction_standards collection for use by the RAG system.
"""
import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from langchain_openai import OpenAIEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_construction_knowledge() -> Dict[str, Any]:
    """Load the construction knowledge base from JSON file."""
    kb_file = Path("golden_dataset/construction_knowledge_base.json")
    
    if not kb_file.exists():
        logger.error(f"Knowledge base file not found: {kb_file}")
        return {}
    
    with open(kb_file, 'r') as f:
        return json.load(f)

def create_knowledge_points(knowledge_base: Dict[str, Any]) -> List[PointStruct]:
    """Convert knowledge base entries to Qdrant points."""
    points = []
    embeddings = OpenAIEmbeddings()
    
    entries = knowledge_base.get("entries", [])
    logger.info(f"Processing {len(entries)} knowledge base entries...")
    
    for i, entry in enumerate(entries):
        # Create content for embedding
        content = f"Construction Term: {entry['term']}\n"
        content += f"Definition: {entry['definition']}\n"
        content += f"Category: {entry['category']}\n"
        
        # Add visual cues if present
        if "visual_cues" in entry:
            content += f"Visual Cues: {', '.join(entry['visual_cues'])}\n"
        
        # Add formulas if present
        if "formulas" in entry:
            content += f"Formulas: {', '.join(entry['formulas'])}\n"
        
        # Generate embedding
        try:
            embedding = embeddings.embed_query(content)
            
            # Create point with integer ID (Qdrant requirement)
            point = PointStruct(
                id=10000 + i,  # Start from 10000 to avoid conflicts
                vector=embedding,
                payload={
                    "term": entry["term"],
                    "definition": entry["definition"],
                    "category": entry["category"],
                    "content": content,
                    "source": "construction_knowledge_base",
                    "type": "construction_term"
                }
            )
            points.append(point)
            
            logger.info(f"Created point for: {entry['term']}")
            
        except Exception as e:
            logger.error(f"Failed to create embedding for {entry['term']}: {e}")
            continue
    
    return points

def ingest_to_qdrant(points: List[PointStruct]) -> bool:
    """Ingest points into Qdrant construction_standards collection."""
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if "construction_standards" not in collection_names:
            logger.error("construction_standards collection not found")
            return False
        
        # Upsert points
        logger.info(f"Upserting {len(points)} construction knowledge points...")
        
        client.upsert(
            collection_name="construction_standards",
            points=points
        )
        
        logger.info("✅ Successfully ingested construction knowledge base")
        return True
        
    except Exception as e:
        logger.error(f"Failed to ingest to Qdrant: {e}")
        return False

def main():
    """Main function to ingest construction knowledge base."""
    
    # Load knowledge base
    logger.info("Loading construction knowledge base...")
    knowledge_base = load_construction_knowledge()
    
    if not knowledge_base:
        logger.error("Failed to load knowledge base")
        return
    
    logger.info(f"Knowledge base loaded: {knowledge_base.get('metadata', {})}")
    
    # Create points
    logger.info("Creating Qdrant points...")
    points = create_knowledge_points(knowledge_base)
    
    if not points:
        logger.error("No points created")
        return
    
    logger.info(f"Created {len(points)} points")
    
    # Ingest to Qdrant
    logger.info("Ingesting to Qdrant...")
    success = ingest_to_qdrant(points)
    
    if success:
        logger.info("🎉 Construction knowledge base successfully ingested!")
        logger.info(f"Added {len(points)} construction terms to RAG system")
        
        # Print summary
        categories = {}
        for point in points:
            category = point.payload.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        
        print("\n" + "="*60)
        print("CONSTRUCTION KNOWLEDGE BASE INGESTED")
        print("="*60)
        print(f"Total Terms: {len(points)}")
        print("\nBy Category:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count} terms")
        print("\nTerms now available for RAG retrieval:")
        print("- Material definitions (DIP, HDPE, PVC, RCP, etc.)")
        print("- Structure types (SSMH, CB, DI, MH, CO)")
        print("- Fitting types (FES, SSL, SS)")
        print("- NCDOT specifications (840.02, 840.14, 840.53)")
        print("- Visual cues and formulas")
        print("="*60)
        
    else:
        logger.error("Failed to ingest knowledge base")

if __name__ == "__main__":
    main()
