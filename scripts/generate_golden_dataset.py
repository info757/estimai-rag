#!/usr/bin/env python3
"""
Generate golden dataset for RAGAS evaluation.

Creates simple, clear test PDFs with known ground truth for evaluation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors


def create_simple_storm_plan():
    """
    Create a simple storm drain plan (PDF 1).
    
    Ground truth:
    - 1 storm drain pipe
    - 18" RCP
    - 250 LF
    - IE in: 420.0, IE out: 418.0
    - Ground: 425.0
    """
    output_path = Path("golden_dataset/pdfs/test_01_simple_storm.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, "STORM DRAIN PLAN - Test 01")
    
    # Legend
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 2*inch, "LEGEND:")
    c.setFont("Helvetica", 10)
    c.drawString(1.2*inch, height - 2.3*inch, "SD = Storm Drain")
    c.drawString(1.2*inch, height - 2.6*inch, "RCP = Reinforced Concrete Pipe")
    c.drawString(1.2*inch, height - 2.9*inch, "CB = Catch Basin")
    c.drawString(1.2*inch, height - 3.2*inch, "IE = Invert Elevation")
    
    # Scale
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 3.8*inch, "SCALE: 1\" = 50'")
    
    # Plan View
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 4.5*inch, "PLAN VIEW")
    
    # Draw storm drain pipe (cyan line)
    c.setStrokeColor(colors.cyan)
    c.setLineWidth(3)
    c.line(2*inch, height - 5.5*inch, 7*inch, height - 5.5*inch)
    
    # Labels
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(2*inch, height - 5.8*inch, "CB-1")
    c.drawString(6.8*inch, height - 5.8*inch, "CB-2")
    c.drawString(4*inch, height - 5.2*inch, "18\" RCP SD")
    c.drawString(4*inch, height - 5.5*inch, "250 LF")
    
    # Profile View
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 7*inch, "PROFILE")
    
    # Profile grid
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    for elev in [415, 420, 425, 430]:
        y = height - 9*inch + (elev - 415) * 0.1 * inch
        c.line(2*inch, y, 7*inch, y)
        c.setFont("Helvetica", 8)
        c.drawString(1.5*inch, y - 0.1*inch, f"{elev}'")
    
    # Ground line
    c.setStrokeColor(colors.brown)
    c.setLineWidth(1.5)
    c.line(2*inch, height - 8.5*inch, 7*inch, height - 8.8*inch)
    c.setFont("Helvetica", 8)
    c.drawString(4*inch, height - 8.3*inch, "GROUND")
    
    # Pipe invert line
    c.setStrokeColor(colors.cyan)
    c.setLineWidth(2)
    c.line(2*inch, height - 9*inch, 7*inch, height - 9.2*inch)
    
    # Elevation labels
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2*inch, height - 9.3*inch, "IE=420.0'")
    c.drawString(6.8*inch, height - 9.5*inch, "IE=418.0'")
    c.drawString(2*inch, height - 8.2*inch, "GL=425.0'")
    c.drawString(6.8*inch, height - 8.5*inch, "GL=423.0'")
    
    # Stations
    c.setFont("Helvetica", 8)
    c.drawString(2*inch, height - 9.7*inch, "STA 0+00")
    c.drawString(6.8*inch, height - 9.7*inch, "STA 2+50")
    
    c.save()
    print(f"✅ Created: {output_path}")
    
    # Create ground truth
    ground_truth = {
        "pdf_name": "test_01_simple_storm.pdf",
        "description": "Simple storm drain plan with one RCP pipe",
        "expected_pipes": [
            {
                "discipline": "storm",
                "material": "RCP",
                "diameter_in": 18,
                "length_ft": 250.0,
                "invert_in_ft": 420.0,
                "invert_out_ft": 418.0,
                "ground_elev_ft": 425.0,
                "depth_ft": 5.0
            }
        ],
        "expected_summary": "1 storm drain pipe, 250 LF, 18\" RCP, depth 5-7 ft",
        "expected_retrieval_context": [
            "Storm drain minimum cover requirements",
            "RCP reinforced concrete pipe",
            "storm drain cover depth"
        ],
        "expected_qa_flags": []
    }
    
    gt_path = Path("golden_dataset/ground_truth/test_01_annotations.json")
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(gt_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"✅ Created ground truth: {gt_path}")
    return str(output_path), str(gt_path)


def create_multi_utility_plan():
    """
    Create a plan with storm, sanitary, and water (PDF 2).
    
    Ground truth:
    - 1 storm (RCP 12")
    - 1 sanitary (PVC 8")
    - 1 water (DI 8")
    """
    output_path = Path("golden_dataset/pdfs/test_02_multi_utility.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, "UTILITY PLAN - Test 02")
    
    # Legend
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 2*inch, "LEGEND:")
    c.setFont("Helvetica", 10)
    c.drawString(1.2*inch, height - 2.3*inch, "SD = Storm Drain (Cyan)")
    c.drawString(1.2*inch, height - 2.6*inch, "SS = Sanitary Sewer (Green)")
    c.drawString(1.2*inch, height - 2.9*inch, "WM = Water Main (Blue)")
    c.drawString(1.2*inch, height - 3.2*inch, "MH = Manhole")
    
    # Scale
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 3.8*inch, "SCALE: 1\" = 40'")
    
    # Plan View
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 4.5*inch, "PLAN VIEW")
    
    # Storm drain (cyan, top)
    c.setStrokeColor(colors.cyan)
    c.setLineWidth(2)
    c.line(2*inch, height - 5.2*inch, 7*inch, height - 5.2*inch)
    c.setFont("Helvetica", 8)
    c.setStrokeColor(colors.black)
    c.drawString(4*inch, height - 5.0*inch, "12\" RCP SD - 200 LF")
    
    # Sanitary (green, middle)
    c.setStrokeColor(colors.green)
    c.setLineWidth(2)
    c.line(2*inch, height - 5.8*inch, 7*inch, height - 5.8*inch)
    c.setFont("Helvetica", 8)
    c.setStrokeColor(colors.black)
    c.drawString(4*inch, height - 5.6*inch, "8\" PVC SS - 200 LF")
    
    # Water (blue, bottom)
    c.setStrokeColor(colors.blue)
    c.setLineWidth(2)
    c.line(2*inch, height - 6.4*inch, 7*inch, height - 6.4*inch)
    c.setFont("Helvetica", 8)
    c.setStrokeColor(colors.black)
    c.drawString(4*inch, height - 6.2*inch, "8\" DI WM - 200 LF")
    
    c.save()
    print(f"✅ Created: {output_path}")
    
    # Ground truth
    ground_truth = {
        "pdf_name": "test_02_multi_utility.pdf",
        "description": "Multi-utility plan with storm, sanitary, and water",
        "expected_pipes": [
            {
                "discipline": "storm",
                "material": "RCP",
                "diameter_in": 12,
                "length_ft": 200.0
            },
            {
                "discipline": "sanitary",
                "material": "PVC",
                "diameter_in": 8,
                "length_ft": 200.0
            },
            {
                "discipline": "water",
                "material": "DI",
                "diameter_in": 8,
                "length_ft": 200.0
            }
        ],
        "expected_summary": "3 total pipes: 1 storm (RCP 12\"), 1 sanitary (PVC 8\"), 1 water (DI 8\"), 600 LF total",
        "expected_retrieval_context": [
            "storm drain",
            "sanitary sewer", 
            "water main",
            "RCP reinforced concrete",
            "PVC pipe",
            "ductile iron DI"
        ]
    }
    
    gt_path = Path("golden_dataset/ground_truth/test_02_annotations.json")
    with open(gt_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"✅ Created ground truth: {gt_path}")
    return str(output_path), str(gt_path)


def create_shallow_cover_plan():
    """
    Create plan with validation issues (PDF 3).
    
    Ground truth:
    - 1 storm pipe with shallow cover (should trigger QA flag)
    """
    output_path = Path("golden_dataset/pdfs/test_03_validation.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, "STORM DRAIN - Shallow Cover Test 03")
    
    # Legend
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2*inch, "SCALE: 1\" = 30'")
    c.drawString(1*inch, height - 2.3*inch, "18\" RCP Storm Drain under parking lot")
    
    # Plan View
    c.setStrokeColor(colors.cyan)
    c.setLineWidth(3)
    c.line(2*inch, height - 3*inch, 6*inch, height - 3*inch)
    
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(3.5*inch, height - 2.7*inch, "18\" RCP SD")
    c.drawString(3.5*inch, height - 3.3*inch, "120 LF")
    
    # Profile with shallow cover
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 4.5*inch, "PROFILE")
    
    # Ground line
    c.setStrokeColor(colors.brown)
    c.setLineWidth(2)
    c.line(2*inch, height - 5.5*inch, 6*inch, height - 5.5*inch)
    c.setFont("Helvetica", 8)
    c.drawString(3.5*inch, height - 5.3*inch, "GROUND ELEV = 422.0'")
    
    # Pipe (SHALLOW - only 1ft cover!)
    c.setStrokeColor(colors.cyan)
    c.setLineWidth(2)
    c.line(2*inch, height - 5.6*inch, 6*inch, height - 5.7*inch)
    
    c.setStrokeColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2*inch, height - 5.9*inch, "IE=421.0'")
    c.drawString(5.7*inch, height - 6.0*inch, "IE=420.5'")
    
    # Note about shallow cover
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.red)
    c.drawString(1*inch, height - 6.5*inch, "NOTE: Cover depth = 1.0 ft (BELOW MINIMUM 1.5 ft for parking areas)")
    
    c.save()
    print(f"✅ Created: {output_path}")
    
    # Ground truth
    ground_truth = {
        "pdf_name": "test_03_validation.pdf",
        "description": "Storm drain with shallow cover - should trigger validation flag",
        "expected_pipes": [
            {
                "discipline": "storm",
                "material": "RCP",
                "diameter_in": 18,
                "length_ft": 120.0,
                "invert_in_ft": 421.0,
                "invert_out_ft": 420.5,
                "ground_elev_ft": 422.0,
                "depth_ft": 1.0
            }
        ],
        "expected_summary": "1 storm drain pipe, 120 LF, 18\" RCP, SHALLOW COVER (1.0 ft < 1.5 ft required)",
        "expected_retrieval_context": [
            "Storm drain minimum cover requirements: 1.5 feet under roadways",
            "parking",
            "RCP"
        ],
        "expected_qa_flags": ["STORM_COVER_LOW"]
    }
    
    gt_path = Path("golden_dataset/ground_truth/test_03_annotations.json")
    with open(gt_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"✅ Created ground truth: {gt_path}")
    return str(output_path), str(gt_path)


def main():
    """Generate all golden dataset PDFs."""
    print("\n" + "="*60)
    print("GOLDEN DATASET GENERATION")
    print("="*60)
    print()
    
    pdfs_created = []
    
    # PDF 1: Simple storm
    print("Creating Test 01: Simple Storm Drain...")
    pdf1, gt1 = create_simple_storm_plan()
    pdfs_created.append((pdf1, gt1))
    print()
    
    # PDF 2: Multi-utility
    print("Creating Test 02: Multi-Utility Plan...")
    pdf2, gt2 = create_multi_utility_plan()
    pdfs_created.append((pdf2, gt2))
    print()
    
    # PDF 3: Validation test
    print("Creating Test 03: Validation Test...")
    pdf3, gt3 = create_shallow_cover_plan()
    pdfs_created.append((pdf3, gt3))
    print()
    
    # Create dataset README
    readme_content = f"""# Golden Dataset for RAGAS Evaluation

## Overview

This dataset contains {len(pdfs_created)} annotated test PDFs for evaluating the EstimAI-RAG system.

## Test Cases

### Test 01: Simple Storm Drain
- **File**: test_01_simple_storm.pdf
- **Purpose**: Basic storm drain detection
- **Expected**: 1 storm pipe, 18\" RCP, 250 LF
- **Tests**: Material classification, length measurement, elevation extraction

### Test 02: Multi-Utility Plan
- **File**: test_02_multi_utility.pdf
- **Purpose**: Multiple utility disciplines
- **Expected**: 3 pipes (storm, sanitary, water), 600 LF total
- **Tests**: Discipline classification, multi-network handling

### Test 03: Validation Test
- **File**: test_03_validation.pdf
- **Purpose**: Validation flag generation
- **Expected**: 1 storm pipe with shallow cover (should flag)
- **Tests**: RAG-based validation, cover depth checking

## Ground Truth Format

Each PDF has a corresponding annotation file in `ground_truth/` with:

```json
{{
  "pdf_name": "test_XX_name.pdf",
  "description": "What this test validates",
  "expected_pipes": [
    {{
      "discipline": "storm|sanitary|water",
      "material": "RCP|PVC|DI",
      "diameter_in": 8-48,
      "length_ft": 100-500,
      "invert_in_ft": 400-430,
      "invert_out_ft": 400-430,
      "ground_elev_ft": 420-430,
      "depth_ft": 1-10
    }}
  ],
  "expected_summary": "Text summary for RAGAS ground truth",
  "expected_retrieval_context": [
    "Construction standards that should be retrieved"
  ],
  "expected_qa_flags": ["FLAG_CODE"]
}}
```

## RAGAS Metrics

These PDFs are used to evaluate:

1. **Faithfulness**: Does the agent accurately use retrieved construction standards?
2. **Answer Relevance**: Are pipe counts and details relevant to the takeoff task?
3. **Context Precision**: Do retrieved standards help with classification?
4. **Context Recall**: Were all necessary standards retrieved?

## Usage

```python
from app.evaluation.ragas_eval import RAGASEvaluator

evaluator = RAGASEvaluator()

# Run evaluation
scores = evaluator.evaluate_on_golden_dataset()
print(scores)
```

## Adding More Tests

To add additional test cases:

1. Create PDF in `pdfs/` directory
2. Create annotations in `ground_truth/test_XX_annotations.json`
3. Follow the ground truth format above
4. Re-run evaluation

---

Generated: {len(pdfs_created)} test PDFs  
Format: ReportLab PDF (vector graphics)  
Purpose: RAGAS evaluation and certification
"""
    
    readme_path = Path("golden_dataset/README.md")
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"✅ Created dataset README: {readme_path}")
    
    # Summary
    print("\n" + "="*60)
    print("✅ GOLDEN DATASET COMPLETE!")
    print("="*60)
    print(f"\nCreated {len(pdfs_created)} test PDFs:")
    for pdf, gt in pdfs_created:
        print(f"  - {Path(pdf).name}")
    print(f"\nDataset ready for RAGAS evaluation!")
    print()


if __name__ == "__main__":
    main()

