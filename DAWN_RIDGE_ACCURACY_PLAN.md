# Production Accuracy Plan for Dawn Ridge 25-Page PDF

## Current State Analysis

**Ground Truth (Human Estimator)**:
- **Utilities**: 34 distinct items across 3 disciplines (Storm, Sanitary, Water)
  - Storm: 19 items (pipes, structures, fittings) - 2,956 LF of pipe
  - Sanitary: 6 items (pipes, laterals, structures) - 1,801 LF of pipe  
  - Water: 5 items (pipes, laterals, structures) - 1,118 LF of pipe
- **Materials**: 16 erosion control/site items (fencing, retaining walls, matting, seeding)
- **Earthwork**: Complex volumes (60,523 CY cut, 54,747 CY fill, 10,794 CY topsoil stripping)

**Current System Output**:
- 5 pipes detected (~1,178 LF total)
- Missing ~80% of items and categories
- Missing: erosion control, retaining walls, fencing, detailed earthwork breakdown
- Missing: laterals (service connections), fittings, many structures

**Gap**: We're only catching mainline pipes. Missing laterals, fittings, structures, site work, and accurate earthwork calculations.

---

## Root Cause Analysis

### 1. **Vision Agent Scope** 
   - Current: Focused on mainline pipes only
   - Missing: Laterals (4" SS Service, Copper Service), fittings (FES, valves), vertical structures (manholes, catch basins, inlets)

### 2. **Material/Abbreviation Knowledge**
   - Spreadsheet reveals: "DIP", "HDPE", "Corrugated HDPE", "FES", "SS Service", "SSL Cleanout"
   - Current RAG may not have all abbreviations decoded

### 3. **Earthwork Methodology**
   - Spreadsheet shows sophisticated calculations: Cut vs. Fill, Compaction factors, Stripping, Sectional analysis
   - Current system: Basic trench volumes only

### 4. **Missing Categories**
   - Erosion control (silt fence, inlet protection, seeding)
   - Site work (retaining walls, fencing)
   - These require enhanced Vision prompts

---

## Strategic Approach

### Phase 1: Diagnostic & Knowledge Enrichment (Week 1)
**Goal**: Parse spreadsheets, identify all missing materials/abbreviations, enhance RAG with construction industry knowledge

1. **Parse Spreadsheets Programmatically**
   - Extract all unique materials: "DIP", "Corrugated HDPE", "FES", "SSL Cleanout", etc.
   - Extract all structure types: "SSMH", "NCDOT 840.02 Concrete Catch Basin", etc.
   - Build comprehensive vocabulary list (50-100 terms)

2. **Generate Definitions for RAG (ONE-TIME SETUP)**

**NOT runtime web scraping - this is a ONE-TIME knowledge base enhancement**

For each abbreviation found in spreadsheet, generate definition using GPT-4:
```python
# Example: Extract "DIP" from spreadsheet
abbreviation = "DIP"
prompt = f"What does {abbreviation} mean in construction/sitework context? Provide brief definition."
definition = gpt4(prompt)  # "Ductile Iron Pipe - strong, flexible water/sewer pipe"

# Add to RAG knowledge base
add_to_rag({
  "term": "DIP",
  "definition": definition,
  "category": "pipe_material"
})
```

**Alternative**: Use Tavily for definitions if GPT-4 hallucinations are a concern:
```python
definition = tavily_search(f"construction term {abbreviation} definition")
```

**Key Point**: This happens ONCE during setup, NOT during every takeoff

3. **Enhance RAG Knowledge Base**
   - Add 100+ material definitions to RAG
   - Add structure type specifications
   - Add lateral/service connection standards
   - Add fitting/appurtenance descriptions

4. **Create Ground Truth Comparison**
   - Build JSON file mapping spreadsheet items to expected PDF locations
   - Manual annotation: Review PDF, note which pages contain laterals, fittings, structures

### Phase 2: Prompt & Context Engineering (Week 2)
**Goal**: Use enhanced prompts + RAG context to capture ALL categories (NO new agents needed)

**Core Philosophy**: GPT-4o Vision is smart enough - we just need to ASK for the right things and PROVIDE the right context.

1. **Enhanced PipesVisionAgent Prompt** (Single prompt handles everything)

Add explicit instructions to existing prompt:
```
COMPREHENSIVE EXTRACTION - Extract ALL of the following:

1. MAINLINE PIPES: Storm, sanitary, water mains with diameter, material, length
2. LATERALS/SERVICES: Service connections from main to buildings
   - Look for: "4\" SS Service", "Copper Service to meter", "6\" Fire Lateral"
   - Often shown as dashed lines or smaller pipes branching off mains
3. STRUCTURES (Vertical): Count and identify all
   - Manholes: MH-1, MH-2, SSMH (Sanitary Sewer Manhole)
   - Catch Basins: CB-1, CB-2, NCDOT 840.02 Concrete Catch Basin
   - Drop Inlets: DI-1, DI-2, NCDOT 840.14 Drop Inlet
   - Cleanouts: CO, SSL Cleanout
   - Hydrants: Fire hydrant assemblies
4. FITTINGS/APPURTENANCES:
   - FES (Flared End Section)
   - Valves (gate valves, check valves)
   - Tees, reducers, bends
   - Antiseep collars
5. DEPTHS: For each item, look for depth callouts in format:
   - "0-6'" (0 to 6 feet deep)
   - "6-8'" (6 to 8 feet deep)
   - "Average Depth: 9.2 ft"
```

2. **Enhanced GradingVisionAgent Prompt**

Add erosion control and site work detection:
```
SITE WORK & EROSION CONTROL - Look for:

1. EROSION CONTROL:
   - Silt fence / Diversion ditch (shown as wavy lines on perimeter)
   - Construction entrance (gravel pad at site entrance)
   - Inlet protection symbols (circles around storm inlets)
   - Slope matting areas (hatched areas on slopes)
   - Seeding/grassing areas (usually noted in legend or notes)
2. SITE IMPROVEMENTS:
   - Retaining walls (thick lines with height callouts)
   - Fencing (chain link, privacy fence with LF measurements)
3. GRADING VOLUMES:
   - Cut/Fill areas (usually shaded or hatched differently)
   - Topsoil stripping depth notes
```

3. **RAG Context Engineering** (The Secret Weapon)

Instead of new agents, enhance RAG with:
- **Material decoder**: "DIP = Ductile Iron Pipe, HDPE = High-Density Polyethylene, FES = Flared End Section"
- **Structure specs**: "NCDOT 840.02 = 4ft diameter concrete catch basin with 2ft sump"
- **Estimating formulas**: "Service lateral = main to building connection, typically 4\" diameter, average 30 LF per house"
- **Visual cues**: "Laterals shown as dashed lines perpendicular to mains"

When Vision LLM sees "4\" SS Service" → queries RAG → gets context → understands it's a lateral

### Phase 3: Calculation Engine Overhaul (Week 3)
**Goal**: Match human estimator's earthwork methodology

1. **Reverse-Engineer Calculations**
   - From spreadsheet: Cut Volume = 60,523 CY, Fill Volume = 54,747 CY
   - Formulas shown: "Cut Compacted", "Fill Compacted", "Export-Import", "Per 0.1 ft"
   - Build calculation modules matching these

2. **Implement Advanced Earthwork**
   - Cut/Fill analysis (not just trench volumes)
   - Compaction factors (Fill Compacted = Fill × 1.15)
   - Topsoil stripping (shown as 10,794 CY at 0.667 ft depth)
   - Sectional analysis (asphalt, curb, sidewalk, greenspace)

3. **Structure Excavation**
   - Manholes, catch basins need box excavation (not trench)
   - Depth-based calculations from spreadsheet depth columns

### Phase 4: Validation Using Existing RAGAS + Custom Metrics
**Goal**: Use your built-in evaluation framework to measure prompt iteration improvements

**You Already Have Perfect Evaluation Infrastructure!**

1. **Convert Spreadsheet to Ground Truth Format**

Create ground truth JSON matching your existing format:
```python
{
  "expected_pipes": [
    {
      "discipline": "sanitary",
      "material": "DIP",  # From "8\" DIP" in spreadsheet
      "diameter_in": 8,
      "length_ft": 177.67,  # From "Total Measure" column
      "depth_ft": 9.2,  # From "Average Depth" column
      # ... more fields
    },
    # ... 34 total items from Utilities spreadsheet
  ],
  "expected_retrieval_keywords": [
    "DIP", "Ductile Iron Pipe", "HDPE", "FES", "Flared End Section", "SSMH"
  ],
  "expected_summary": "34 utility items: 19 storm, 6 sanitary, 5 water..."
}
```

2. **Run Iterative Evaluation Loop**
```python
# Baseline (current prompts)
baseline_result = run_takeoff("Dawn Ridge.pdf")
baseline_scores = evaluate_both(baseline_result, ground_truth)

# Iteration 1: Add laterals to prompt
# ... update prompt ...
iter1_result = run_takeoff("Dawn Ridge.pdf")
iter1_scores = evaluate_both(iter1_result, ground_truth)

# Compare improvements
compare_results_table(baseline_scores, iter1_scores)
```

3. **Track These Metrics Per Iteration**

**Custom Metrics** (Domain Accuracy):
- `pipe_count_accuracy`: 5/34 detected → 20/34 detected → 30/34 detected
- `material_accuracy`: 60% → 80% → 90%
- `elevation_accuracy`: 100% (already good)

**RAGAS Metrics** (RAG Effectiveness):
- `faithfulness`: Is Vision citing RAG correctly for unknown materials?
- `context_recall`: Are we retrieving DIP, HDPE, FES definitions?
- `answer_relevancy`: Are results focused on utilities (not noise)?

4. **Automated Reporting After Each Iteration**

Your existing `format_custom_results_table()` and `compare_results_table()` already generate markdown reports!

### Phase 5: Generalization & Testing (Week 5)
**Goal**: Ensure system works on OTHER projects, not just Dawn Ridge

1. **Test on Different PDFs**
   - Run on 3-5 other sitework projects
   - Measure accuracy improvement across projects

2. **Make Knowledge Transferable**
   - Don't hardcode Dawn Ridge specifics
   - Ensure abbreviation decoder works for any project
   - Auto-extract project-specific legends (already built)

---

## Implementation Priorities (Immediate Action)

### Priority 1: MUST HAVE (Production Blockers)
1. ✅ **Laterals Detection** - Missing 52 service connections (huge cost item!)
2. ✅ **Structure Extraction** - Missing 69 structures (manholes, inlets, catch basins)
3. ✅ **Material Vocabulary** - Add DIP, HDPE, FES, SSL to RAG

### Priority 2: HIGH VALUE (Accuracy Drivers)  
4. ✅ **Fitting Detection** - Valves, FES, collars (14 items)
5. ✅ **Depth-Based Calculations** - Use Average Depth from spreadsheet methodology
6. ✅ **Comparison Dashboard** - Side-by-side AI vs. Ground Truth

### Priority 3: NICE TO HAVE (Future Enhancements)
7. 🔵 **Erosion Control Agent** - New category (16 items)
8. 🔵 **Site Work Agent** - Retaining walls, fencing
9. 🔵 **Advanced Earthwork** - Cut/Fill/Stripping breakdown

---

## How to Use Spreadsheet Data (CORE STRATEGY)

**The Spreadsheet is Our Diagnostic Tool, Not Training Data**

### The Iterative Improvement Loop:

```
1. Parse spreadsheet → Extract what human found (ground truth)
2. Run current system → Get AI output
3. Compare → Identify gaps (what we missed)
4. Analyze WHY we missed it:
   - Prompt didn't ask for it? → Update prompt
   - Material abbreviation unknown? → Add to RAG
   - Visual pattern not described? → Add visual cues to RAG
5. Re-run → Measure improvement
6. Repeat until 85%+ accuracy
```

### Three Uses of Spreadsheet:

**Use #1: Vocabulary Extraction (for RAG)**
- Parse all materials/abbreviations from spreadsheet
- Generate definitions (using GPT-4 if needed, not web scraping)
- Add to RAG so Vision LLM has context when it encounters them

**Use #2: Prompt Gap Analysis**
- Spreadsheet shows 26 "4\" SS Service" laterals
- Current output: 0 laterals detected
- **Action**: Add "LATERALS" section to Vision prompt with examples

**Use #3: Accuracy Measurement**
- After each prompt iteration, compare output to spreadsheet
- Quantify: recall (% items found), precision (% items correct), quantity accuracy
- Track improvement over iterations

### Grading/Earthwork Strategy

**Challenge**: Spreadsheet shows final volumes (60,523 CY cut) but NOT the input data (elevation grids)

**Solution**:
1. Focus on INPUT extraction first: Get ALL spot elevations, contours, grid points from PDF
2. Don't try to replicate estimator's software - just capture raw elevation data
3. Simple validation: If we extract N elevation points, human can verify completeness
4. Advanced: Build grid-based cut/fill calculator (like estimator's software)

---

## Success Metrics

**Phase 1 Complete**: RAG has 200+ construction terms, spreadsheet parsed into structured JSON

**Phase 2 Complete**: Detect 30+ of 34 utility items (88% recall)

**Phase 3 Complete**: Earthwork calculations within 10% of ground truth

**Phase 4 Complete**: Estimator validates output in <30 minutes (vs. 3-5 days manual)

**Production Ready**: 90%+ item detection, 85%+ quantity accuracy, <1 hour processing time

---

## Files to Create

1. `scripts/parse_ground_truth_spreadsheets.py` - Extract all items into JSON
2. `scripts/generate_construction_definitions.py` - Generate abbreviation definitions
3. `scripts/enhance_rag_from_ground_truth.py` - Add to knowledge base
4. `scripts/compare_output_to_ground_truth.py` - Accuracy measurement
5. Enhanced prompts in existing Vision agents (no new agent files needed)
6. `app/calculations/advanced_earthwork.py` - Cut/Fill analysis
7. `golden_dataset/ground_truth/dawn_ridge_annotations.json` - Ground truth from spreadsheets

---

## Risk Mitigation

**Risk 1**: PDF pages don't clearly show laterals/fittings
- **Mitigation**: Manual review of PDF first, annotate 5-10 examples, use as prompt training

**Risk 2**: Definition generation too slow/unreliable
- **Mitigation**: Use cached construction dictionary, GPT-4 to generate definitions (one-time setup)

**Risk 3**: Earthwork calculation methodology unknown
- **Mitigation**: Focus on input extraction, partner with estimator to explain calculations

**Risk 4**: Over-optimization for Dawn Ridge
- **Mitigation**: Test on 2-3 other projects in parallel, ensure generalizability

---

## Implementation Tasks

- [ ] **Task 1**: Parse 4 ground truth spreadsheets into structured JSON with all materials, abbreviations, and quantities
- [ ] **Task 2**: Extract unique materials/abbreviations and generate definitions for RAG enhancement
- [ ] **Task 3**: Run comparison: current system output vs. ground truth spreadsheet to quantify gaps
- [ ] **Task 4**: Update PipesVisionAgent prompts to detect laterals, fittings, and structure details
- [ ] **Task 5**: Update GradingVisionAgent prompts for erosion control and site work
- [ ] **Task 6**: Add 100+ construction terms/definitions to RAG knowledge base
- [ ] **Task 7**: Build advanced earthwork module for structure excavation and depth-based calculations
- [ ] **Task 8**: Create comparison script showing AI output vs. ground truth with RAGAS + custom metrics
- [ ] **Task 9**: Run iterative prompt improvement cycles with metric tracking
- [ ] **Task 10**: Validate system works on 2-3 other sitework PDFs to ensure generalizability

---

**Plan Created**: October 23, 2025  
**Target**: Production-ready accuracy for Dawn Ridge 25-page PDF  
**Approach**: Prompt engineering + RAG context enhancement (no model fine-tuning)  
**Success Criteria**: 90%+ item detection, 85%+ quantity accuracy

