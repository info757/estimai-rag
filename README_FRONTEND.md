# Frontend Demo Instructions

## Start Backend

```bash
cd /Users/williamholt/estimai-rag
source venv/bin/activate
export $(cat .env | grep -v '^#' | grep -v BACKEND_CORS | xargs)

# Ensure Qdrant is running
docker start qdrant-estimai

# Start API
uvicorn app.main:app --reload --port 8000
```

## Open Frontend

```bash
# Open in browser
open frontend/index.html

# Or manually navigate to:
file:///Users/williamholt/estimai-rag/frontend/index.html
```

## Demo Workflow

### Test 1: Realistic Site (Kernersville Commerce Park)
1. Upload `golden_dataset/pdfs/test_06_realistic_site.pdf`
2. Watch processing indicator
3. See results:
   - 3 sewer pipes detected (8" PVC, 8" PVC, 10" PVC)
   - No alerts (materials known)
   - RAG contexts shown (PVC specs, sewer standards)
   - All confidence > 70%
4. Test editing: Click any cell, change value, see "edited" highlight
5. Click "Save Corrections"

### Test 2: Unknown Materials (FPVC Test)
1. Upload `golden_dataset/pdfs/test_05_complex_realistic.pdf`
2. See CRITICAL alert appear
3. FPVC row highlighted red (low confidence)
4. User alert shows: "FPVC - unknown material, manual review required"
5. Options:
   - Mark as verified
   - Edit material name
   - Save corrections
6. Demonstrates unknown detection + human oversight

## Features Demonstrated

✅ PDF viewing alongside results  
✅ Automatic AI processing  
✅ User alerts for unknowns  
✅ Editable table (Human-in-the-Loop)  
✅ Confidence-based highlighting  
✅ RAG transparency (contexts shown)  
✅ Researcher activity logs  
✅ Export to CSV

