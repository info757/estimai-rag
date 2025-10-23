#!/usr/bin/env python3
"""
Extract legend data from PDF and ingest into RAG.

This script:
1. Runs LegendVisionAgent on first 3 pages of PDF
2. Extracts abbreviations, symbols, specifications
3. Creates embeddings and stores in Qdrant RAG
4. Tags with project name for future retrieval
"""
import sys
import json
import logging
import os
import asyncio
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
from app.vision.coordinator import VisionCoordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_legend_from_pdf(pdf_path: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Extract legend data from first few pages of PDF."""
    logger.info(f"Extracting legend from: {pdf_path} (first {max_pages} pages)")
    
    coordinator = VisionCoordinator()
    legend_data = []
    
    for page_num in range(max_pages):
        try:
            logger.info(f"Analyzing page {page_num}...")
            result = asyncio.run(coordinator.analyze_page(
                pdf_path=pdf_path,
                page_num=page_num,
                agents_to_deploy=["legend"],
                dpi=300
            ))
            
            # Extract legend data from result
            if result and isinstance(result, dict):
                # The result structure may vary, check for legend data
                if "legend" in result:
                    legend_result = result["legend"]
                elif "pipes" in result and len(result["pipes"]) > 0:
                    # Legend agent returns data in pipes array
                    legend_result = result["pipes"][0] if isinstance(result["pipes"], list) else result["pipes"]
                else:
                    legend_result = result
                
                if legend_result and legend_result.get("is_legend_page", False):
                    legend_data.append({
                        "page_num": page_num,
                        "data": legend_result
                    })
                    logger.info(f"Found legend data on page {page_num}")
                else:
                    logger.info(f"Page {page_num} is not a legend page")
            
        except Exception as e:
            logger.error(f"Failed to analyze page {page_num}: {e}")
            continue
    
    return legend_data

def merge_legend_data(legend_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge legend data from multiple pages."""
    merged = {
        "abbreviations": [],
        "symbols": [],
        "specifications": [],
        "project_info": {},
        "measurement_standards": {}
    }
    
    for page_data in legend_pages:
        data = page_data["data"]
        
        # Merge abbreviations (deduplicate by abbr)
        for abbr in data.get("abbreviations", []):
            if not any(a["abbr"] == abbr["abbr"] for a in merged["abbreviations"]):
                merged["abbreviations"].append(abbr)
        
        # Merge symbols
        for symbol in data.get("symbols", []):
            if not any(s["symbol"] == symbol["symbol"] for s in merged["symbols"]):
                merged["symbols"].append(symbol)
        
        # Merge specifications
        for spec in data.get("specifications", []):
            if not any(s["code"] == spec["code"] for s in merged["specifications"]):
                merged["specifications"].append(spec)
        
        # Take first non-empty project info
        if not merged["project_info"] and data.get("project_info"):
            merged["project_info"] = data["project_info"]
        
        # Take first non-empty measurement standards
        if not merged["measurement_standards"] and data.get("measurement_standards"):
            merged["measurement_standards"] = data["measurement_standards"]
    
    return merged

def create_legend_points(legend_data: Dict[str, Any], project_name: str) -> List[PointStruct]:
    """Convert legend data to Qdrant points."""
    points = []
    embeddings = OpenAIEmbeddings()
    point_id = 20000  # Start from 20000 to avoid conflicts
    
    logger.info(f"Creating embeddings for legend data...")
    
    # Create points for abbreviations
    for abbr in legend_data.get("abbreviations", []):
        content = f"Abbreviation: {abbr['abbr']} = {abbr['full_name']}\n"
        content += f"Category: {abbr['category']}\n"
        content += f"Project: {project_name}\n"
        
        try:
            embedding = embeddings.embed_query(content)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "abbreviation",
                    "abbr": abbr["abbr"],
                    "full_name": abbr["full_name"],
                    "category": abbr["category"],
                    "content": content,
                    "source": f"{project_name}_legend",
                    "project": project_name
                }
            )
            points.append(point)
            point_id += 1
            
            logger.info(f"Created point for abbreviation: {abbr['abbr']}")
            
        except Exception as e:
            logger.error(f"Failed to create embedding for {abbr['abbr']}: {e}")
            continue
    
    # Create points for symbols
    for symbol in legend_data.get("symbols", []):
        content = f"Symbol: {symbol['symbol']} = {symbol['meaning']}\n"
        content += f"Visual Description: {symbol.get('visual_description', '')}\n"
        if symbol.get("discipline"):
            content += f"Discipline: {symbol['discipline']}\n"
        content += f"Project: {project_name}\n"
        
        try:
            embedding = embeddings.embed_query(content)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "symbol",
                    "symbol": symbol["symbol"],
                    "meaning": symbol["meaning"],
                    "discipline": symbol.get("discipline", ""),
                    "content": content,
                    "source": f"{project_name}_legend",
                    "project": project_name
                }
            )
            points.append(point)
            point_id += 1
            
            logger.info(f"Created point for symbol: {symbol['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to create embedding for symbol {symbol['symbol']}: {e}")
            continue
    
    # Create points for specifications
    for spec in legend_data.get("specifications", []):
        content = f"Specification Code: {spec['code']}\n"
        content += f"Description: {spec['description']}\n"
        content += f"Category: {spec.get('category', 'specification')}\n"
        content += f"Project: {project_name}\n"
        
        try:
            embedding = embeddings.embed_query(content)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "specification",
                    "code": spec["code"],
                    "description": spec["description"],
                    "category": spec.get("category", "specification"),
                    "content": content,
                    "source": f"{project_name}_legend",
                    "project": project_name
                }
            )
            points.append(point)
            point_id += 1
            
            logger.info(f"Created point for specification: {spec['code']}")
            
        except Exception as e:
            logger.error(f"Failed to create embedding for spec {spec['code']}: {e}")
            continue
    
    return points

def ingest_to_qdrant(points: List[PointStruct]) -> bool:
    """Ingest legend points into Qdrant."""
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if "construction_standards" not in collection_names:
            logger.error("construction_standards collection not found")
            return False
        
        # Upsert points
        logger.info(f"Upserting {len(points)} legend points...")
        
        client.upsert(
            collection_name="construction_standards",
            points=points
        )
        
        logger.info("✅ Successfully ingested legend data")
        return True
        
    except Exception as e:
        logger.error(f"Failed to ingest to Qdrant: {e}")
        return False

def main():
    """Main function to extract and ingest legend data."""
    
    # PDF path
    pdf_path = "uploads/Dawn Ridge Homes_HEPA_Combined_04-1-25.pdf"
    project_name = "Dawn Ridge Homes"
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    # Extract legend from first 3 pages
    logger.info("Extracting legend data from PDF...")
    legend_pages = extract_legend_from_pdf(pdf_path, max_pages=3)
    
    if not legend_pages:
        logger.warning("No legend data found in first 3 pages")
        return
    
    logger.info(f"Found legend data on {len(legend_pages)} page(s)")
    
    # Merge legend data
    logger.info("Merging legend data...")
    legend_data = merge_legend_data(legend_pages)
    
    # Save merged data
    output_file = "golden_dataset/dawn_ridge_legend_data.json"
    with open(output_file, 'w') as f:
        json.dump(legend_data, f, indent=2)
    
    logger.info(f"Legend data saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("LEGEND DATA EXTRACTED")
    print("="*60)
    print(f"Abbreviations: {len(legend_data['abbreviations'])}")
    print(f"Symbols: {len(legend_data['symbols'])}")
    print(f"Specifications: {len(legend_data['specifications'])}")
    print(f"Project: {legend_data.get('project_info', {}).get('name', 'Unknown')}")
    
    # Show sample abbreviations
    if legend_data['abbreviations']:
        print("\nSample Abbreviations:")
        for abbr in legend_data['abbreviations'][:5]:
            print(f"  {abbr['abbr']} = {abbr['full_name']} ({abbr['category']})")
    
    # Create points for RAG
    logger.info("Creating embeddings for RAG...")
    points = create_legend_points(legend_data, project_name)
    
    logger.info(f"Created {len(points)} points for RAG")
    
    # Ingest to Qdrant
    logger.info("Ingesting to Qdrant...")
    success = ingest_to_qdrant(points)
    
    if success:
        print("\n🎉 Legend data successfully ingested to RAG!")
        print(f"Total points added: {len(points)}")
        print("\nBreakdown:")
        print(f"  Abbreviations: {len([p for p in points if p.payload['type'] == 'abbreviation'])}")
        print(f"  Symbols: {len([p for p in points if p.payload['type'] == 'symbol'])}")
        print(f"  Specifications: {len([p for p in points if p.payload['type'] == 'specification'])}")
    else:
        logger.error("Failed to ingest legend data")

if __name__ == "__main__":
    main()

