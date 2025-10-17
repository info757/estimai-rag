# Golden Dataset for RAGAS Evaluation

## Overview

This dataset contains 3 annotated test PDFs for evaluating the EstimAI-RAG system.

## Test Cases

### Test 01: Simple Storm Drain
- **File**: test_01_simple_storm.pdf
- **Purpose**: Basic storm drain detection
- **Expected**: 1 storm pipe, 18" RCP, 250 LF
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
{
  "pdf_name": "test_XX_name.pdf",
  "description": "What this test validates",
  "expected_pipes": [
    {
      "discipline": "storm|sanitary|water",
      "material": "RCP|PVC|DI",
      "diameter_in": 8-48,
      "length_ft": 100-500,
      "invert_in_ft": 400-430,
      "invert_out_ft": 400-430,
      "ground_elev_ft": 420-430,
      "depth_ft": 1-10
    }
  ],
  "expected_summary": "Text summary for RAGAS ground truth",
  "expected_retrieval_context": [
    "Construction standards that should be retrieved"
  ],
  "expected_qa_flags": ["FLAG_CODE"]
}
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

Generated: 3 test PDFs  
Format: ReportLab PDF (vector graphics)  
Purpose: RAGAS evaluation and certification
