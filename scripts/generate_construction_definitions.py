#!/usr/bin/env python3
"""
Generate construction term definitions for RAG enhancement.

Uses GPT-4 to generate definitions for abbreviations and materials found in spreadsheets,
then adds them to the RAG knowledge base.
"""
import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_ground_truth() -> Dict[str, Any]:
    """Load the ground truth data from the parsed spreadsheets."""
    gt_file = Path("golden_dataset/ground_truth/dawn_ridge_annotations.json")
    
    if not gt_file.exists():
        logger.error(f"Ground truth file not found: {gt_file}")
        return {}
    
    with open(gt_file, 'r') as f:
        return json.load(f)

def generate_definition(term: str, context: str = "construction/sitework") -> str:
    """Generate a definition for a construction term using GPT-4."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""You are a construction industry expert. Provide a brief, accurate definition for the term "{term}" in the context of {context}.

Format your response as:
TERM: [term]
DEFINITION: [brief definition]
CATEGORY: [pipe_material|structure|fitting|abbreviation|etc]
USAGE: [how it's used in construction plans]

Keep it concise but informative. Focus on what an estimator would need to know."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate definition for {term}: {e}")
        return f"TERM: {term}\nDEFINITION: [Definition not available]\nCATEGORY: unknown\nUSAGE: [Usage not available]"

def create_rag_knowledge_entries(ground_truth: Dict[str, Any]) -> List[Dict[str, str]]:
    """Create RAG knowledge entries for all terms found in the ground truth."""
    
    entries = []
    
    # Get all unique materials and abbreviations
    abbreviations = ground_truth.get("abbreviations_vocabulary", [])
    materials = ground_truth.get("materials_vocabulary", [])
    
    # Add common construction terms that might be missing
    additional_terms = [
        "MH", "CB", "DI", "CO", "SSMH", "NCDOT", "840.02", "840.14", "840.53",
        "Inlet Protection", "Silt Fence", "Diversion Ditch", "Slope Matting",
        "Retaining Wall", "Chain Link Fence", "Privacy Fence"
    ]
    
    all_terms = set(abbreviations + materials + additional_terms)
    
    logger.info(f"Generating definitions for {len(all_terms)} terms")
    
    for term in sorted(all_terms):
        if not term or term == "Unknown":
            continue
            
        logger.info(f"Generating definition for: {term}")
        definition = generate_definition(term)
        
        # Parse the definition
        lines = definition.split('\n')
        parsed_def = {
            "term": term,
            "definition": definition,
            "category": "construction_term"
        }
        
        # Try to extract structured info
        for line in lines:
            if line.startswith("CATEGORY:"):
                parsed_def["category"] = line.replace("CATEGORY:", "").strip()
            elif line.startswith("DEFINITION:"):
                parsed_def["definition"] = line.replace("DEFINITION:", "").strip()
        
        entries.append(parsed_def)
    
    return entries

def create_visual_cues_entries() -> List[Dict[str, str]]:
    """Create entries for visual cues that help Vision agents identify items."""
    
    visual_cues = [
        {
            "term": "Service Lateral",
            "definition": "Service connection from main to building",
            "category": "visual_cue",
            "visual_description": "Shown as dashed lines perpendicular to main pipes, typically 4\" diameter, 20-50 LF length"
        },
        {
            "term": "Manhole",
            "definition": "Access structure for sewer maintenance",
            "category": "visual_cue", 
            "visual_description": "Shown as circles with labels like MH-1, MH-2, SSMH, typically 4-6 ft diameter"
        },
        {
            "term": "Catch Basin",
            "definition": "Storm drain inlet structure",
            "category": "visual_cue",
            "visual_description": "Shown as rectangles with labels like CB-1, CB-2, often with NCDOT specifications"
        },
        {
            "term": "Drop Inlet",
            "definition": "Storm drain inlet with vertical drop",
            "category": "visual_cue",
            "visual_description": "Shown as rectangles with DI-1, DI-2 labels, NCDOT 840.14 specification"
        },
        {
            "term": "FES",
            "definition": "Flared End Section - concrete outlet structure",
            "category": "visual_cue",
            "visual_description": "Shown as flared concrete structure at pipe outlets, often labeled FES"
        },
        {
            "term": "Silt Fence",
            "definition": "Temporary erosion control barrier",
            "category": "visual_cue",
            "visual_description": "Shown as wavy lines around construction perimeter, typically 100-200 LF"
        },
        {
            "term": "Inlet Protection",
            "definition": "Temporary protection around storm inlets",
            "category": "visual_cue",
            "visual_description": "Shown as circles or symbols around storm inlets during construction"
        }
    ]
    
    return visual_cues

def create_estimation_formulas() -> List[Dict[str, str]]:
    """Create entries for estimation formulas and standards."""
    
    formulas = [
        {
            "term": "Trench Width Formula",
            "definition": "Standard trench width calculation for pipe installation",
            "category": "formula",
            "formula": "Trench Width = Pipe Diameter + 2 feet (working space)",
            "usage": "Used for excavation volume calculations"
        },
        {
            "term": "Excavation Volume",
            "definition": "Volume of earth to be excavated for pipe installation",
            "category": "formula",
            "formula": "Volume (CY) = (Width × Depth × Length) / 27",
            "usage": "Convert cubic feet to cubic yards for excavation estimates"
        },
        {
            "term": "Bedding Material",
            "definition": "Sand or gravel bedding for pipe support",
            "category": "formula",
            "formula": "Bedding Volume = (Width × 0.5 ft × Length) / 27",
            "usage": "Standard 6-inch bedding depth for most pipes"
        },
        {
            "term": "Backfill Volume",
            "definition": "Material needed to backfill trench after pipe installation",
            "category": "formula",
            "formula": "Backfill = Excavation - Pipe Volume - Bedding",
            "usage": "Calculate material needed for trench backfill"
        },
        {
            "term": "Service Lateral Length",
            "definition": "Average length of service connection from main to building",
            "category": "standard",
            "formula": "Typical length: 30-50 LF per connection",
            "usage": "Estimate service lateral quantities for residential connections"
        }
    ]
    
    return formulas

def save_to_rag_knowledge_base(entries: List[Dict[str, str]], output_file: str):
    """Save the knowledge entries to a JSON file for RAG ingestion."""
    
    # Create the knowledge base structure
    knowledge_base = {
        "metadata": {
            "source": "Dawn Ridge Ground Truth Analysis",
            "generated_date": "2025-10-23",
            "total_entries": len(entries),
            "categories": list(set(entry.get("category", "unknown") for entry in entries))
        },
        "entries": entries
    }
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(knowledge_base, f, indent=2)
    
    logger.info(f"Knowledge base saved to: {output_file}")
    logger.info(f"Total entries: {len(entries)}")

def main():
    """Main function to generate construction definitions and create RAG knowledge base."""
    
    # Load ground truth data
    ground_truth = load_ground_truth()
    if not ground_truth:
        logger.error("Failed to load ground truth data")
        return
    
    logger.info("Generating construction term definitions...")
    
    # Generate definitions for all terms
    all_entries = []
    
    # Add term definitions
    term_entries = create_rag_knowledge_entries(ground_truth)
    all_entries.extend(term_entries)
    
    # Add visual cues
    visual_entries = create_visual_cues_entries()
    all_entries.extend(visual_entries)
    
    # Add estimation formulas
    formula_entries = create_estimation_formulas()
    all_entries.extend(formula_entries)
    
    # Save to knowledge base
    output_file = "golden_dataset/construction_knowledge_base.json"
    save_to_rag_knowledge_base(all_entries, output_file)
    
    # Also create a summary
    summary = {
        "total_terms": len(term_entries),
        "visual_cues": len(visual_entries),
        "formulas": len(formula_entries),
        "total_entries": len(all_entries),
        "categories": list(set(entry.get("category", "unknown") for entry in all_entries))
    }
    
    logger.info(f"Knowledge base summary: {summary}")
    
    return all_entries

if __name__ == "__main__":
    main()
