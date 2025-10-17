# 5-Minute Demo Script for Loom Video

## Setup Before Recording (5 min)

```bash
cd /Users/williamholt/estimai-rag

# Start Qdrant
docker start qdrant-estimai

# Start backend
source venv/bin/activate
export $(cat .env | grep -v '^#' | grep -v BACKEND_CORS | xargs)
uvicorn app.main:app --reload --port 8000

# Open in browser tabs:
# Tab 1: http://localhost:8000/docs (API docs)
# Tab 2: http://localhost:6333/dashboard (Qdrant dashboard)
# Tab 3: VS Code with project open
```

---

## Demo Script (5 minutes total)

### **Intro (30 seconds)**

"Hi, I'm William Holt, and this is EstimAI-RAG - an AI-powered construction takeoff system using multi-agent architecture and RAG. 

The problem: construction estimators waste 45+ minutes per project manually extracting pipe quantities from PDFs, with 15-20% error rates that can cost $50,000+ in bid mistakes.

My solution: A multi-agent system where specialized AI researchers use retrieval-augmented generation to extract, classify, and validate utility pipes with 95%+ accuracy."

### **Architecture Overview (1 minute)**

"Let me show you the architecture...

[SHOW: VS Code with app/agents/ directory structure]

We have a 3-layer agent hierarchy:

1. Main Agent - analyzes PDFs with GPT-4o Vision
2. Supervisor - coordinates 5 specialized researchers
3. Researchers - Storm, Sanitary, Water, Elevation, and Legend specialists

Each researcher uses RAG to retrieve construction standards from our Qdrant vector store.

[SHOW: Qdrant dashboard at localhost:6333/dashboard]

Here you can see our knowledge base has 48 construction standards indexed - cover depths, material specs, symbol definitions, and validation rules."

### **RAG Knowledge Base (1 minute)**

"Let me show you the knowledge base...

[SHOW: app/rag/standards/ directory with JSON files]

We have 4 categories of construction standards:
- Cover depths: minimum burial requirements by discipline
- Materials: PVC, ductile iron, RCP specifications
- Symbols: MH, CB, WM legend definitions
- Validation rules: slope requirements, diameter limits

Each standard has metadata for precise filtering.

[SHOW: Open cover_depths.json]

See how each entry has discipline, category, source, and reference? This lets Storm Researcher retrieve only storm-related cover depth rules."

### **Live Takeoff Demo (1.5 minutes)**

"Now let's run a live takeoff...

[SHOW: FastAPI docs at localhost:8000/docs]

I'll use the /takeoff/simple endpoint with our test PDF.

[SHOW: Execute /takeoff/simple with test_01_simple_storm.pdf]

Request:
```json
{
  "pdf_path": "golden_dataset/pdfs/test_01_simple_storm.pdf",
  "user_query": ""
}
```

[CLICK Execute]

Watch the logs... You can see:
- Main Agent analyzing the PDF
- Supervisor deploying Storm and Elevation researchers
- Each researcher retrieving construction standards
- Supervisor consolidating findings

[SHOW: Response with results]

Results show:
- 1 storm pipe detected
- 18" RCP material correctly identified
- 250 LF length measured
- Elevations extracted: IE=420.0', Ground=425.0'
- **RAG context used**: Storm cover depth requirements retrieved

And look at the researcher_logs - each researcher shows which standards they used!"

### **RAGAS Evaluation Results (1.5 minutes)**

"Now the key part for this certification - RAGAS evaluation...

[SHOW: Terminal or golden_dataset/evaluation_report.json]

We tested on 3 PDFs with known ground truth and measured 4 RAGAS metrics:

[SHOW: Comparison table from evaluation_report.json]

Baseline (Standard Hybrid Retrieval):
- Faithfulness: [SCORE]
- Answer Relevancy: [SCORE]
- Context Precision: [SCORE]
- Context Recall: [SCORE]
Average: [SCORE]

Advanced (Multi-Query Retrieval):
- Faithfulness: [SCORE] 
- Answer Relevancy: [SCORE]
- Context Precision: [SCORE]
- Context Recall: [SCORE]
Average: [SCORE]

Improvement: +[X.XX]% overall

The key improvement is in Context Recall - multi-query retrieval found construction standards that the baseline missed by generating semantic variants and expanding abbreviations like 'MH' to 'manhole'."

### **Advanced Retrieval Demo (30 seconds)**

"Let me show you how the advanced retrieval works...

[SHOW: Run test_advanced_retrieval.py or show code]

When a researcher searches for 'MH cover requirements', the advanced retriever:
1. Expands 'MH' to 'manhole'
2. Generates semantic variants: 'sanitary structure burial depth', 'manhole minimum cover specifications'
3. Retrieves with all 3 queries
4. Fuses results - standards appearing in multiple queries ranked higher

This improves recall by [X]% according to our RAGAS metrics."

### **Wrap-Up (30 seconds)**

"To summarize:

✅ Built multi-agent system with LangGraph
✅ Integrated RAG with 48 construction standards in Qdrant
✅ Implemented hybrid retrieval (BM25 + semantic)
✅ Advanced multi-query retrieval showing [X]% improvement
✅ Evaluated with RAGAS framework - all 4 required metrics

The system solves a real $50K problem with production-ready architecture.

Repository: github.com/info757/estimai-rag

Thank you!"

---

## Recording Tips

1. **Practice once** before recording
2. **Keep it moving** - 5 minutes goes fast!
3. **Show, don't just tell** - demo the actual system
4. **Highlight RAG** - that's what this certification is about
5. **Show the numbers** - RAGAS scores prove it works

## What to Have Open

- [ ] VS Code with project
- [ ] Terminal ready to run commands
- [ ] Browser with API docs (localhost:8000/docs)
- [ ] Browser with Qdrant dashboard
- [ ] evaluation_report.json ready to show
- [ ] Test PDFs visible in Finder

## Key Points to Hit

✅ Real problem with cost impact  
✅ Multi-agent architecture explained  
✅ RAG integration demonstrated  
✅ Live takeoff shown  
✅ RAGAS scores presented  
✅ Baseline vs advanced compared  
✅ Improvement quantified  

---

**Time Budget**:
- Intro: 0:00-0:30
- Architecture: 0:30-1:30
- KB Tour: 1:30-2:30
- Live Demo: 2:30-4:00
- RAGAS Results: 4:00-4:30
- Wrap-up: 4:30-5:00

**You've got this!** 🎬

