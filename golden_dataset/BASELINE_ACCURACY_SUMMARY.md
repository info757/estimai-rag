# Dawn Ridge Baseline Accuracy Analysis

**Date:** October 23, 2025  
**System**: Current EstimAI-RAG (before prompt enhancements)  
**PDF**: Dawn Ridge Homes - 25 pages  
**Ground Truth Source**: Human estimator spreadsheets

---

## Executive Summary

**Current Detection Rate: 24.1% (7/29 items)**  
**Lin

ear Footage Accuracy: 21.2% (1,430/6,752 LF)**

### Critical Gap Identified

The system is only catching **mainline pipes** and missing entire categories:
- ❌ **26 Service Laterals** (0% detection)
- ❌ **35 Structures** (manholes, catch basins, cleanouts - 0% detection)
- ❌ **14 Fittings** (FES, valves - 0% detection)
- ❌ **13 Erosion Control items** (100% missing category)
- ❌ **10 Earthwork volume entries** (100% missing category)

---

## Detailed Comparison

### Current System Output (Baseline)
```
Total Pipes: 7
- Storm: 6 pipes (1,180 LF)
- Sanitary: 1 pipe (250 LF)
- Water: 0 pipes

Vision Processing: 12 pipes detected → 7 after deduplication
Processing Time: ~8 minutes (25 pages @ 300 DPI)
```

### Ground Truth (Human Estimator)
```
Total Utility Items: 29
- Storm: 17 items (2,957 LF)
  - 7 mainline pipes
  - 7 structures (catch basins, inlets, manholes)
  - 3 fittings (FES, etc.)
- Sanitary: 6 items (1,801 LF)
  - 2 mainline pipes  
  - 26 service laterals (4" SS Service)
  - 26 cleanouts (SSL Cleanout)
  - 1 manhole
- Water: 6 items (1,995 LF)
  - 1 mainline (8" DIP)
  - 3 fire laterals (6")
  - 26 copper service lines
  - 3 hydrant assemblies
  - 3 gate valves

Additional Categories (Not Detected):
- Materials: 13 erosion control/site work items
- Volumes: 10 earthwork calculation entries
```

---

## Gap Analysis by Category

### 1. Mainline Pipes ⚠️ PARTIAL SUCCESS
**Detection**: 7/16 mainline pipes (43.8%)  
**Issue**: Some mainlines detected but quantities understated  
**Root Cause**: Vision prompt not asking comprehensively

### 2. Service Laterals ❌ COMPLETE MISS
**Detection**: 0/55 lateral connections (0%)  
**Missing Items**:
- 26× 4" SS Service (sanitary laterals) - 817 LF
- 26× Copper Service to meter - 877 LF  
- 3× 6" Fire Lateral - 42 LF

**Root Cause**: Vision prompt doesn't explicitly ask for laterals/service connections

### 3. Structures ❌ COMPLETE MISS  
**Detection**: 0/69 structures (0%)  
**Missing Items**:
- 14× NCDOT 840.02 Catch Basin
- 18× NCDOT 840.14 Drop Inlet
- 2× NCDOT 840.53 Manhole
- 8× SSMH (Sanitary Sewer Manhole)
- 26× 4" SSL Cleanout
- 3× 6" Hydrant Assembly
- 1× Outlet Control Structure

**Root Cause**: Vision prompt doesn't ask for vertical structures

### 4. Fittings ❌ COMPLETE MISS
**Detection**: 0/14 fittings (0%)  
**Missing Items**:
- 5× FES (Flared End Section)
- 2× Antiseep Collars
- 3× 8" Gate Valve
- 1× Tie into Existing
- 3× Fire hydrant valves/connections

**Root Cause**: Vision prompt doesn't ask for fittings/appurtenances

### 5. Erosion Control ❌ MISSING CATEGORY
**Detection**: 0/13 items (0%)  
**Missing Items**:
- Diversion Ditch (1,749 LF)
- Construction Entrance (333 SY)
- Block and Gravel Inlet Protection (32 EA)
- Sediment Tube Inlet Protection (14 EA)
- Ditch Matting SC-140 (2,005 SY)
- Slope Matting (13,026 SY)
- Grassing/Seeding (6.77 AC)
- Retaining Wall Fencing (490 LF)
- Wet Pond Fencing (622 LF)

**Root Cause**: No erosion control vision agent deployed

### 6. Earthwork Volumes ❌ MISSING CATEGORY  
**Detection**: 0/10 volume items (0%)  
**Missing Items**:
- Cut Volume: 60,523 CY
- Fill Volume: 54,747 CY
- Topsoil Stripping: 10,794 CY
- Sectional breakdown (asphalt, curb, sidewalk, greenspace)

**Root Cause**: Grading agent not extracting earthwork data

---

## Performance by Discipline

| Discipline | Predicted | Expected | Detection % | LF Predicted | LF Expected | LF % |
|-----------|-----------|----------|-------------|--------------|-------------|------|
| **Storm** | 6 | 17 | 35.3% | 1,180 | 2,957 | 39.9% |
| **Sanitary** | 1 | 6 | 16.7% | 250 | 1,801 | 13.9% |
| **Water** | 0 | 6 | 0% | 0 | 1,995 | 0% |
| **TOTAL** | 7 | 29 | 24.1% | 1,430 | 6,752 | 21.2% |

---

## Root Cause Analysis

### Primary Issues

**1. Vision Prompt Scope Too Narrow**
- Current prompt: "Extract pipes with diameter, material, length"
- Missing: Explicit instructions for laterals, structures, fittings
- Missing: Visual cues (dashed lines = laterals, circles = manholes)

**2. Missing Material Definitions in RAG**
- "SS Service" not decoded (should be "Sanitary Sewer Service Lateral")
- "SSL" not decoded (should be "Sanitary Sewer Lateral")  
- "DI" not decoded (should be "Ductile Iron")
- "FES" not decoded (should be "Flared End Section")
- NCDOT spec numbers (840.02, 840.14, 840.53) not explained

**3. No Category-Specific Agents**
- Erosion control requires separate detection logic
- Earthwork volumes require elevation grid extraction
- Structures need different identification patterns than pipes

**4. JSON Parsing Issues**
- Multiple "No JSON found in response" warnings in logs
- Vision LLM sometimes returns text instead of structured JSON
- Needs more robust JSON extraction

---

## Recommended Actions (Priority Order)

### Phase 1: Enhance Vision Prompts (IMMEDIATE - High Impact)

**1.1 Update PipesVisionAgent Prompt**
```python
Add sections for:
- MAINLINE PIPES: [existing]
- LATERALS/SERVICES: "Look for dashed lines, 4\" SS Service, Copper Service..."
- STRUCTURES: "Count manholes (MH-1), catch basins (CB-1), cleanouts..."
- FITTINGS: "Identify FES, valves, tees, reducers..."
- DEPTHS: "Extract depth callouts: 0-6', 6-8', Average Depth..."
```

**Impact**: Should increase detection from 24% → 60-70%

**1.2 Enhance GradingVisionAgent Prompt**
```python
Add sections for:
- EROSION CONTROL: "Silt fence, inlet protection, slope matting..."
- SITE WORK: "Retaining walls, fencing..."  
- GRADING VOLUMES: "Cut/fill areas, topsoil stripping..."
```

**Impact**: Should capture erosion control items (currently 0%)

### Phase 2: Enhance RAG Knowledge Base (IMMEDIATE - Medium Impact)

**2.1 Add Construction Term Definitions**
- Already generated 40 terms in `construction_knowledge_base.json`
- Need to ingest into Qdrant RAG collection
- Terms include: DIP, HDPE, FES, SS, SSL, SSMH, NCDOT specs

**Impact**: Better material recognition, fewer "unknowns"

**2.2 Add Visual Cues**
- "Service laterals shown as dashed lines perpendicular to mains"
- "Manholes shown as circles with MH-1, MH-2 labels"
- "Catch basins shown as rectangles with CB-1, CB-2 labels"

**Impact**: Vision LLM understands what to look for visually

### Phase 3: Fix JSON Parsing (QUICK WIN)

**3.1 More Robust JSON Extraction**
- Add fallback parsing for markdown code blocks
- Handle responses without proper JSON formatting
- Log failed parses for debugging

**Impact**: Reduce "No JSON found" errors, capture more items

### Phase 4: Test & Iterate (VALIDATION)

**4.1 Re-run Baseline After Phase 1-3**
- Measure new detection rate  
- Target: 70%+ detection, 80%+ LF accuracy

**4.2 Compare Using RAGAS + Custom Metrics**
- Use existing evaluation framework
- Track improvement iteration-by-iteration

---

## Expected Outcomes After Phase 1-3

### Optimistic Projection
```
Detection Rate: 24% → 75% (+51 points)
Linear Footage: 21% → 85% (+64 points)

Storm: 35% → 80%
Sanitary: 17% → 70%  
Water: 0% → 65%

Laterals: 0% → 60% (30/55 detected)
Structures: 0% → 50% (35/69 detected)
Fittings: 0% → 40% (6/14 detected)
```

### Conservative Projection
```
Detection Rate: 24% → 55% (+31 points)
Linear Footage: 21% → 65% (+44 points)

Laterals: 0% → 40%
Structures: 0% → 30%
Fittings: 0% → 20%
```

---

## Files Generated

1. `dawn_ridge_annotations.json` - Ground truth from spreadsheets (29 items)
2. `construction_knowledge_base.json` - 40 construction term definitions
3. `BASELINE_ACCURACY_SUMMARY.md` - This file
4. `baseline_comparison.log` - Full system run logs

---

## Next Steps

1. ✅ **Complete**: Parse spreadsheets → ground truth JSON
2. ✅ **Complete**: Generate construction definitions → RAG knowledge  
3. ✅ **Complete**: Run baseline comparison → identify gaps
4. ⏭️ **Next**: Update PipesVisionAgent prompt (Phase 1.1)
5. ⏭️ **Next**: Update GradingVisionAgent prompt (Phase 1.2)
6. ⏭️ **Next**: Ingest construction knowledge into RAG (Phase 2)
7. ⏭️ **Next**: Re-run and measure improvement

---

**Status**: Baseline complete. Ready to implement prompt enhancements.  
**Confidence**: High - clear gaps identified with specific solutions.  
**Timeline**: Phase 1-3 can be completed in 2-3 hours, testing in 1 hour.

