# Dawn Ridge Baseline vs. Ground Truth

## Executive Summary

**Detection Rate**: 79.3% (23/29 items)

### By Discipline

| Discipline | Predicted | Expected | Detection Rate | LF Predicted | LF Expected | LF Accuracy |
|-----------|-----------|----------|----------------|--------------|-------------|-------------|
| Storm | 16 | 17 | 94.1% | 1218 | 2957 | 41.2% |
| Sanitary | 7 | 6 | 116.7% | 390 | 1801 | 21.7% |
| Water | 0 | 6 | 0.0% | 0 | 1995 | 0.0% |

## Missing Categories

### Laterals (MISSING - 3 items)

- 4" SS Service: 26.0 count, 816.96 LF
- 6" Fire Lateral: 3.0 count, 42.48 LF
- Copper Service to meter: 26.0 count, 876.61 LF

### Structures (MISSING - 8 items)

- 4" SSL Cleanout: 26.0 count
- Existing SSMH: 1.0 count
- SSMH: 8.0 count
- NCDOT 840.02 Concrete Catch Basin: 14.0 count
- NCDOT 840.14 Drop Inlet: 18.0 count
- ... and 3 more

### Fittings (MISSING - 7 items)

- 15" FES: 1.0 count
- 24" FES: 1.0 count
- 30" FES: 1.0 count
- 48" FES: 2.0 count
- Antiseep Collars w/watertight joints: 2.0 count
- ... and 2 more

### Materials (MISSING - 13 items)

- Construction Entrance: 2996.86 SY
- Block and Gravel Inlet Protection: 32.0 EA
- Sediment Tube Inlet Protection: 14.0 EA
- Concrete Washout: 1.0 EA
- Ditch Matting - SC140: 18046.2 SY
- ... and 8 more

### Volumes (MISSING - 10 items)

- Jobsite: Cut 60523.0, Fill 54747.0
- Regions Total:: Cut 60523.0, Fill 54747.0
- Topsoil: Cut 10794.0, Fill 0
- Stripping Total: Cut 10794.0, Fill 0
- 3/7 Asphalt: Cut 1259.0, Fill 0
- ... and 5 more

## Accuracy Metrics

| Metric | Score |
|--------|-------|
| pipe_count_accuracy | 0.276 |
| material_accuracy | 0.174 |
| elevation_accuracy | 1.000 |
| rag_retrieval_quality | 0.500 |
| overall_accuracy | 0.487 |

## Key Gaps to Address

- **Water**: Only detecting 0.0% of items
- **Laterals**: Missing 3 service connections
- **Structures**: Missing 8 manholes/catch basins/inlets
- **Fittings**: Missing 7 valves/fittings
- **Materials**: Missing entire erosion control/site work category (13 items)

## Recommended Actions

1. **Update Vision Prompts**: Add explicit instructions for laterals, structures, fittings
2. **Enhance RAG**: Add {len(missing['laterals'])+len(missing['structures'])+len(missing['fittings'])} construction terms
3. **New Agents**: Consider erosion control and site work vision agents
4. **Test Iteration**: Re-run with enhanced prompts and measure improvement
