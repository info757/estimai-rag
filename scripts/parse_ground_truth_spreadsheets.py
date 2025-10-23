#!/usr/bin/env python3
"""
Parse ground truth spreadsheets from Dawn Ridge project.

Extracts all materials, abbreviations, quantities, and structures from the 4 Excel files
to create a comprehensive ground truth dataset for accuracy evaluation.
"""
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_utilities_spreadsheet(file_path: str) -> Dict[str, Any]:
    """Parse the utilities spreadsheet to extract all utility items."""
    logger.info(f"Parsing utilities spreadsheet: {file_path}")
    
    # Read the spreadsheet
    df = pd.read_excel(file_path, header=None)
    
    # Find the header row (contains "Structure", "Type", etc.)
    header_row = None
    for i, row in df.iterrows():
        if pd.notna(row.iloc[0]) and "Structure" in str(row.iloc[0]):
            header_row = i
            break
    
    if header_row is None:
        logger.error("Could not find header row in utilities spreadsheet")
        return {"error": "Header row not found"}
    
    # Extract data starting from header row + 1
    data_df = df.iloc[header_row + 1:].copy()
    data_df.columns = df.iloc[header_row].tolist()
    
    # Clean up the data
    data_df = data_df.dropna(subset=[data_df.columns[0]])  # Remove empty rows
    
    utilities = []
    for _, row in data_df.iterrows():
        if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
            continue
            
        utility = {
            "structure": str(row.iloc[0]).strip(),
            "surface_strata": str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
            "type": str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else "",
            "class": str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else "",
            "count": float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0,
            "average_depth": float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0,
            "total_measure": float(row.iloc[6]) if pd.notna(row.iloc[6]) else 0,
            "measure": float(row.iloc[7]) if pd.notna(row.iloc[7]) else 0,
            "slope_length": float(row.iloc[8]) if pd.notna(row.iloc[8]) else 0,
        }
        
        # Add depth categories
        for i, col in enumerate(row.iloc[9:], 9):
            if pd.notna(col) and col != 0:
                utility[f"depth_category_{i-9}"] = float(col)
        
        utilities.append(utility)
    
    logger.info(f"Extracted {len(utilities)} utility items")
    return {"utilities": utilities}

def parse_materials_spreadsheet(file_path: str) -> Dict[str, Any]:
    """Parse the materials spreadsheet to extract erosion control and site work items."""
    logger.info(f"Parsing materials spreadsheet: {file_path}")
    
    df = pd.read_excel(file_path, header=None)
    
    # Find data rows (skip header rows)
    materials = []
    for i, row in df.iterrows():
        if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
            continue
            
        # Skip header rows
        if "Diversion Ditch" in str(row.iloc[0]) and i == 0:
            continue
            
        material = {
            "item": str(row.iloc[0]).strip(),
            "description": str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
            "phase": str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else "",
            "category": str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else "",
            "quantity": float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0,
            "unit": str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) else "",
        }
        
        materials.append(material)
    
    logger.info(f"Extracted {len(materials)} material items")
    return {"materials": materials}

def parse_volume_spreadsheet(file_path: str) -> Dict[str, Any]:
    """Parse volume report spreadsheet to extract earthwork calculations."""
    logger.info(f"Parsing volume spreadsheet: {file_path}")
    
    df = pd.read_excel(file_path, header=None)
    
    # Find the data section (look for "Name" column)
    data_start = None
    for i, row in df.iterrows():
        if pd.notna(row.iloc[0]) and "Name" in str(row.iloc[0]):
            data_start = i
            break
    
    if data_start is None:
        logger.error("Could not find data section in volume spreadsheet")
        return {"error": "Data section not found"}
    
    # Extract data
    volumes = []
    for i in range(data_start + 1, len(df)):
        row = df.iloc[i]
        if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
            continue
        
        # Skip header rows
        if str(row.iloc[0]).strip() in ['Name', 'Type', 'Total Area', 'Cut Area', 'Fill Area']:
            continue
            
        try:
            volume = {
                "name": str(row.iloc[0]).strip(),
                "type": str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
                "total_area": float(row.iloc[2]) if pd.notna(row.iloc[2]) and str(row.iloc[2]).replace('.', '').replace('-', '').isdigit() else 0,
                "cut_area": float(row.iloc[3]) if pd.notna(row.iloc[3]) and str(row.iloc[3]).replace('.', '').replace('-', '').isdigit() else 0,
                "fill_area": float(row.iloc[4]) if pd.notna(row.iloc[4]) and str(row.iloc[4]).replace('.', '').replace('-', '').isdigit() else 0,
                "cut_volume": float(row.iloc[6]) if pd.notna(row.iloc[6]) and str(row.iloc[6]).replace('.', '').replace('-', '').isdigit() else 0,
                "fill_volume": float(row.iloc[7]) if pd.notna(row.iloc[7]) and str(row.iloc[7]).replace('.', '').replace('-', '').isdigit() else 0,
            }
            
            volumes.append(volume)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping row {i} due to parsing error: {e}")
            continue
    
    logger.info(f"Extracted {len(volumes)} volume items")
    return {"volumes": volumes}

def extract_materials_and_abbreviations(data: Dict[str, Any]) -> List[str]:
    """Extract all unique materials and abbreviations from the parsed data."""
    materials = set()
    abbreviations = set()
    
    # From utilities
    for utility in data.get("utilities", []):
        structure = utility.get("structure", "")
        if structure:
            # Extract pipe materials and sizes
            if '"' in structure:
                # Extract material abbreviations
                parts = structure.split()
                for part in parts:
                    if part in ["DIP", "PVC", "HDPE", "RCP", "FES", "SS", "SSL"]:
                        abbreviations.add(part)
                    elif "Corrugated" in part:
                        abbreviations.add("HDPE")
                    elif "NCDOT" in part:
                        abbreviations.add("NCDOT")
        
        # Extract structure types
        structure_type = utility.get("type", "")
        if structure_type:
            if structure_type in ["Pipe", "Lateral", "Vertical", "Fitting"]:
                materials.add(structure_type)
    
    # From materials
    for material in data.get("materials", []):
        item = material.get("item", "")
        if item:
            # Extract common abbreviations
            if "HDPE" in item:
                abbreviations.add("HDPE")
            if "PVC" in item:
                abbreviations.add("PVC")
            if "Concrete" in item:
                abbreviations.add("Concrete")
    
    return {
        "materials": sorted(list(materials)),
        "abbreviations": sorted(list(abbreviations))
    }

def create_ground_truth_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ground truth JSON in the format expected by evaluation scripts."""
    
    # Convert utilities to expected pipe format
    expected_pipes = []
    for utility in data.get("utilities", []):
        structure = utility.get("structure", "")
        if not structure or "NaN" in structure:
            continue
            
        # Determine discipline from class
        discipline = "unknown"
        if utility.get("class", "").lower() == "storm":
            discipline = "storm"
        elif utility.get("class", "").lower() == "sewer":
            discipline = "sanitary"
        elif utility.get("class", "").lower() == "water":
            discipline = "water"
        
        # Extract material and diameter from structure name
        material = "Unknown"
        diameter = 0
        
        if '"' in structure:
            # Extract diameter
            import re
            diameter_match = re.search(r'(\d+)"', structure)
            if diameter_match:
                diameter = int(diameter_match.group(1))
            
            # Extract material
            if "DIP" in structure:
                material = "DIP"
            elif "PVC" in structure:
                material = "PVC"
            elif "HDPE" in structure:
                material = "HDPE"
            elif "RCP" in structure:
                material = "RCP"
        
        pipe = {
            "discipline": discipline,
            "material": material,
            "diameter_in": diameter,
            "length_ft": utility.get("total_measure", 0),
            "depth_ft": utility.get("average_depth", 0),
            "count": utility.get("count", 1),
            "structure_name": structure,
            "type": utility.get("type", ""),
            "class": utility.get("class", "")
        }
        
        expected_pipes.append(pipe)
    
    # Create summary
    storm_pipes = [p for p in expected_pipes if p["discipline"] == "storm"]
    sanitary_pipes = [p for p in expected_pipes if p["discipline"] == "sanitary"]
    water_pipes = [p for p in expected_pipes if p["discipline"] == "water"]
    
    summary = {
        "total_pipes": len(expected_pipes),
        "storm_pipes": len(storm_pipes),
        "sanitary_pipes": len(sanitary_pipes),
        "water_pipes": len(water_pipes),
        "storm_lf": sum(p["length_ft"] for p in storm_pipes),
        "sanitary_lf": sum(p["length_ft"] for p in sanitary_pipes),
        "water_lf": sum(p["length_ft"] for p in water_pipes),
        "total_lf": sum(p["length_ft"] for p in expected_pipes)
    }
    
    # Extract materials and abbreviations
    vocab = extract_materials_and_abbreviations(data)
    
    ground_truth = {
        "expected_pipes": expected_pipes,
        "expected_materials": data.get("materials", []),
        "expected_volumes": data.get("volumes", []),
        "expected_summary": summary,
        "expected_retrieval_keywords": vocab["abbreviations"],
        "materials_vocabulary": vocab["materials"],
        "abbreviations_vocabulary": vocab["abbreviations"],
        "total_utility_items": len(expected_pipes),
        "total_material_items": len(data.get("materials", [])),
        "total_volume_items": len(data.get("volumes", []))
    }
    
    return ground_truth

def main():
    """Main function to parse all spreadsheets and create ground truth."""
    base_path = Path("golden_dataset/pdfs")
    
    # File paths
    utilities_file = base_path / "DR_Utilities.xlsx"
    materials_file = base_path / "DR_Materials.xlsx"
    volume_designed_file = base_path / "DR_Volume Report as Designed.xlsx"
    volume_raised_file = base_path / "DR_Volume Report Site Raised 0.264.xlsx"
    
    all_data = {}
    
    # Parse each spreadsheet
    if utilities_file.exists():
        all_data.update(parse_utilities_spreadsheet(str(utilities_file)))
    else:
        logger.error(f"Utilities file not found: {utilities_file}")
    
    if materials_file.exists():
        all_data.update(parse_materials_spreadsheet(str(materials_file)))
    else:
        logger.error(f"Materials file not found: {materials_file}")
    
    if volume_designed_file.exists():
        all_data.update(parse_volume_spreadsheet(str(volume_designed_file)))
    else:
        logger.error(f"Volume designed file not found: {volume_designed_file}")
    
    if volume_raised_file.exists():
        raised_data = parse_volume_spreadsheet(str(volume_raised_file))
        all_data["volumes_raised"] = raised_data.get("volumes", [])
    else:
        logger.error(f"Volume raised file not found: {volume_raised_file}")
    
    # Create ground truth JSON
    ground_truth = create_ground_truth_json(all_data)
    
    # Save to file
    output_file = Path("golden_dataset/ground_truth/dawn_ridge_annotations.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    logger.info(f"Ground truth saved to: {output_file}")
    logger.info(f"Summary: {ground_truth['expected_summary']}")
    logger.info(f"Materials vocabulary: {ground_truth['materials_vocabulary']}")
    logger.info(f"Abbreviations vocabulary: {ground_truth['abbreviations_vocabulary']}")
    
    return ground_truth

if __name__ == "__main__":
    main()
