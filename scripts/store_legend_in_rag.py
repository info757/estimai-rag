"""
Store extracted project legends in Qdrant RAG alongside construction standards.

This enables the retriever to query both:
1. General construction standards (existing)
2. Project-specific legends (new)
"""
import sys
import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from langchain_openai import OpenAIEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def store_legend_chunks_in_qdrant(
    chunks: List[Dict[str, Any]],
    collection_name: str = "construction_standards",
    qdrant_url: str = "http://localhost:6333"
):
    """
    Store legend chunks in Qdrant alongside existing construction standards.
    
    Uses same collection but with metadata to distinguish project legends.
    """
    logger.info(f"Connecting to Qdrant at {qdrant_url}...")
    client = QdrantClient(url=qdrant_url)
    
    # Check if collection exists
    try:
        collection_info = client.get_collection(collection_name)
        logger.info(f"✓ Collection '{collection_name}' exists")
        logger.info(f"  Current points: {collection_info.points_count}")
    except Exception as e:
        logger.error(f"Collection not found: {e}")
        logger.error("Please run scripts/setup_kb.py first to create the collection")
        return
    
    # Initialize embeddings
    logger.info("Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Prepare points for upload
    logger.info(f"Embedding {len(chunks)} legend chunks...")
    points = []
    
    for i, chunk in enumerate(chunks):
        content = chunk['content']
        metadata = chunk['metadata']
        
        # Generate embedding
        try:
            embedding = embeddings.embed_query(content)
        except Exception as e:
            logger.error(f"Failed to embed chunk {i}: {e}")
            continue
        
        # Create point
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "content": content,
                **metadata
            }
        )
        points.append(point)
        
        if (i + 1) % 10 == 0:
            logger.info(f"  Embedded {i + 1}/{len(chunks)} chunks...")
    
    logger.info(f"✓ Embedded all {len(points)} chunks")
    
    # Upload to Qdrant
    logger.info(f"Uploading to Qdrant collection '{collection_name}'...")
    try:
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"✓ Successfully uploaded {len(points)} legend chunks")
        
        # Verify upload
        collection_info = client.get_collection(collection_name)
        logger.info(f"✓ Collection now contains {collection_info.points_count} total points")
        
    except Exception as e:
        logger.error(f"Failed to upload to Qdrant: {e}")
        return
    
    # Test retrieval
    logger.info("\n=== TESTING RETRIEVAL ===")
    test_queries = [
        "What does RCP mean?",
        "What is SILT FENCE?",
        "Construction entrance abbreviation"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        query_embedding = embeddings.embed_query(query)
        
        # Search with project legend filter
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=3,
            query_filter={
                "must": [
                    {
                        "key": "source",
                        "match": {"value": "project_legend"}
                    }
                ]
            }
        )
        
        if results:
            logger.info(f"  Top result: {results[0].payload.get('abbreviation', 'N/A')} = {results[0].payload.get('full_name', 'N/A')}")
            logger.info(f"  Score: {results[0].score:.3f}")
        else:
            logger.info(f"  No results found")
    
    logger.info("\n✓ Legend storage complete!")


def main():
    """Load Dawn Ridge legends into Qdrant."""
    
    chunks_file = Path(__file__).parent.parent / "dawn_ridge_legend_chunks.json"
    
    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        logger.error("Run extract_legend_from_pdf.py first")
        return
    
    logger.info(f"=" * 80)
    logger.info(f"STORING PROJECT LEGENDS IN RAG")
    logger.info(f"=" * 80)
    
    # Load chunks
    with open(chunks_file, 'r') as f:
        chunks = json.load(f)
    
    logger.info(f"Loaded {len(chunks)} chunks from {chunks_file.name}")
    logger.info(f"Chunk types:")
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    for chunk_type, count in chunk_types.items():
        logger.info(f"  - {chunk_type}: {count}")
    
    # Store in Qdrant
    store_legend_chunks_in_qdrant(chunks)
    
    logger.info("\n=== NEXT STEPS ===")
    logger.info("1. ✓ Legends extracted from PDF")
    logger.info("2. ✓ Legends stored in Qdrant RAG")
    logger.info("3. TODO: Update retriever to query project legends")
    logger.info("4. TODO: Test with materials that need legend decoding")


if __name__ == "__main__":
    main()

