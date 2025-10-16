# Implementation Guide - Next Steps

## ✅ Completed So Far

1. **Repository Structure** - All directories created
2. **Dependencies** - requirements.txt with Qdrant
3. **Configuration** - .env.example
4. **Data Models** - Complete Pydantic models for agents and RAG
5. **Knowledge Base** - 40+ construction standards loaded
6. **README** - Comprehensive project documentation

## 🚀 Next Steps (Priority Order)

### Day 1 Tasks (Continue)

#### 1. Set Up Qdrant Vector Store (2-3 hours)

**File**: `app/rag/retriever.py`

```python
"""
Hybrid retrieval with Qdrant (BM25 + Semantic).
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from rank_bm25 import BM25Okapi
import os

class HybridRetriever:
    def __init__(self):
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )
        self.collection_name = "construction_standards"
        self.embeddings = OpenAIEmbeddings()
        
        # BM25 index (in-memory for now)
        self.bm25 = None
        self.documents = []
    
    def create_collection(self, standards: list):
        """Create Qdrant collection and index standards."""
        # Create vectors
        # Store in Qdrant
        # Build BM25 index
        pass
    
    def retrieve_hybrid(self, query: str, k: int = 5):
        """Retrieve using BM25 + semantic, then fuse."""
        # BM25 retrieval
        # Semantic retrieval
        # Reciprocal rank fusion
        pass
```

**Actions**:
1. Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
2. Implement `retriever.py` above
3. Test with: `python -c "from app.rag.retriever import HybridRetriever; r = HybridRetriever()"`

#### 2. Initialize Script (30 min)

**File**: `scripts/setup_kb.py`

```python
"""Initialize the knowledge base in Qdrant."""
from app.rag.knowledge_base import load_knowledge_base
from app.rag.retriever import HybridRetriever

def main():
    print("Loading construction standards...")
    kb = load_knowledge_base()
    print(f"Loaded {len(kb.standards)} standards")
    
    print("Initializing Qdrant vector store...")
    retriever = HybridRetriever()
    retriever.create_collection(kb.get_standards_with_metadata())
    
    print("✅ Knowledge base ready!")
    print(f"Stats: {kb.get_stats()}")

if __name__ == "__main__":
    main()
```

**Run**: `python scripts/setup_kb.py`

### Day 2 Tasks

#### 3. LangGraph Multi-Agent System (4-5 hours)

**File**: `app/agents/main_agent.py` - Create Main Graph Agent
**File**: `app/agents/supervisor.py` - Create Supervisor Agent
**File**: `app/agents/researchers/storm_researcher.py` - Storm specialist
**File**: `app/agents/researchers/water_researcher.py` - Water specialist
**File**: `app/agents/researchers/elevation_researcher.py` - Elevation specialist

**Key Pattern** (from class):
```python
from langgraph.graph import StateGraph
from app.models import AgentState, SupervisorState

def create_main_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze_pdf", analyze_pdf_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("generate_report", generate_report_node)
    
    # Add edges
    workflow.set_entry_point("analyze_pdf")
    workflow.add_edge("analyze_pdf", "supervisor")
    workflow.add_edge("supervisor", "generate_report")
    
    return workflow.compile()
```

#### 4. FastAPI Endpoint (1 hour)

**File**: `app/main.py`

```python
from fastapi import FastAPI, UploadFile, File
from app.models import TakeoffResponse
from app.agents.main_agent import run_takeoff

app = FastAPI(title="EstimAI-RAG")

@app.post("/takeoff", response_model=TakeoffResponse)
async def takeoff(file: UploadFile = File(...)):
    # Save PDF temporarily
    # Run main agent graph
    # Return results with RAG context
    pass

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Day 3 Tasks

#### 5. Golden Dataset (3-4 hours)

**Actions**:
1. Copy 5-8 test PDFs to `golden_dataset/pdfs/`
2. For each, create `golden_dataset/ground_truth/pdf_X_annotations.json`:

```json
{
  "pdf_name": "site_plan_01.pdf",
  "expected_pipes": [
    {
      "discipline": "storm",
      "material": "RCP",
      "diameter_in": 18,
      "length_ft": 245.0,
      "invert_in_ft": 420.5,
      "invert_out_ft": 418.2
    }
  ],
  "expected_retrieval_context": [
    "Storm drain minimum cover requirements",
    "RCP storm drainage 12-144 inches"
  ],
  "expected_qa_flags": [
    "STORM_COVER_LOW"
  ]
}
```

#### 6. RAGAS Evaluation (2-3 hours)

**File**: `app/evaluation/ragas_eval.py`

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

def evaluate_takeoff(results, ground_truth):
    """Evaluate takeoff results using RAGAS."""
    # Prepare dataset
    # Run RAGAS metrics
    # Return scores
    pass
```

**File**: `scripts/run_baseline_eval.py`

```python
"""Run baseline RAGAS evaluation."""
from app.evaluation.ragas_eval import evaluate_takeoff
import json

def main():
    # Load golden dataset
    # Run takeoff on each PDF
    # Evaluate with RAGAS
    # Print table of results
    pass
```

### Day 4 Tasks

#### 7. Advanced Retrieval (2-3 hours)

**File**: `app/rag/advanced_retriever.py`

```python
"""Multi-query retrieval with fusion."""

class AdvancedRetriever:
    def generate_query_variants(self, query: str) -> list[str]:
        """Use LLM to generate query variations."""
        # Expand technical abbreviations
        # Generate semantic variants
        pass
    
    def retrieve_multi_query(self, query: str, k: int = 5):
        """Retrieve with multiple queries and fuse."""
        variants = self.generate_query_variants(query)
        all_results = []
        for variant in variants:
            results = self.hybrid_retriever.retrieve_hybrid(variant, k)
            all_results.append(results)
        
        # Reciprocal rank fusion
        fused = self.reciprocal_rank_fusion(all_results)
        return fused
```

#### 8. Re-evaluate with Advanced (1 hour)

**File**: `scripts/run_advanced_eval.py` - Similar to baseline but use advanced retriever

### Day 5 Tasks

#### 9. Documentation (2-3 hours)

**File**: `docs/CERTIFICATION_REPORT.md` - Answer ALL rubric questions
**File**: `docs/ARCHITECTURE.md` - System diagrams
**File**: `docs/EVALUATION_RESULTS.md` - RAGAS tables

#### 10. Frontend Demo (2-3 hours)

Minimal React app to show:
- PDF upload
- Takeoff results
- **RAG context shown for each pipe**
- Confidence scores

#### 11. Demo Video (1 hour)

Record 5-min Loom showing:
1. Upload PDF
2. Show results
3. Click pipe → see RAG context retrieved
4. Show baseline vs. advanced metrics table
5. Explain improvement

## 🔑 Key Implementation Tips

### From Class: LangGraph Pattern

```python
# Researcher node example
def storm_researcher_node(state: ResearcherState):
    # 1. Get task from state
    task = state["task"]
    
    # 2. RAG retrieval (specialized for storm)
    retriever = HybridRetriever()
    context = retriever.retrieve_hybrid(
        query=task,
        filter={"discipline": "storm"}
    )
    
    # 3. LLM analysis with context
    prompt = f"""
    You are a storm drain specialist.
    
    Task: {task}
    
    Construction Standards:
    {context}
    
    Provide your findings about storm drains in the PDF.
    """
    
    findings = llm.invoke(prompt)
    
    # 4. Return updated state
    return {
        "researcher_name": "storm",
        "retrieved_context": context,
        "findings": findings,
        "confidence": 0.85
    }
```

### RAGAS Dataset Format

```python
from datasets import Dataset

data = {
    "question": ["What pipes are in this PDF?"],
    "answer": ["3 storm drains, 2 water mains"],
    "contexts": [[
        "Storm drain minimum cover: 1.5ft",
        "Water main sizing: 6-12 inches common"
    ]],
    "ground_truth": ["3 storm drains (RCP 18\"), 2 water mains (DI 8\")"]
}

dataset = Dataset.from_dict(data)
result = evaluate(dataset, metrics=[faithfulness, context_precision])
```

## 📊 Success Checklist

- [ ] Qdrant running and collection created
- [ ] Hybrid retrieval working
- [ ] Multi-agent graph executing end-to-end
- [ ] Golden dataset prepared (5-8 PDFs)
- [ ] RAGAS baseline evaluation complete
- [ ] Advanced retrieval implemented
- [ ] RAGAS comparison table created
- [ ] Frontend shows RAG context
- [ ] Documentation complete
- [ ] Demo video recorded

## 🆘 If You Get Stuck

1. **Qdrant Issues**: Check Docker is running, use Qdrant dashboard at http://localhost:6333/dashboard
2. **LangGraph Errors**: Review class examples, check state typing
3. **RAGAS Fails**: Ensure dataset format matches exactly
4. **Time Running Out**: Focus on core features, simplify frontend

## 📞 Quick Commands

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Initialize KB
python scripts/setup_kb.py

# Run backend
uvicorn app.main:app --reload

# Run eval
python scripts/run_baseline_eval.py

# Run tests
pytest tests/ -v
```

## 🎯 Grading Targets

- Problem/Audience: 10/10 (written in plan)
- Solution/Tools: 6/6 (written in plan)
- Agentic Reasoning: 2/2 (LangGraph multi-agent)
- Data Sources: 5/5 (40+ standards, clear sources)
- Chunking: 5/5 (semantic chunks with metadata)
- **Prototype: 15/15** ← Focus here!
- **Golden Dataset: 10/10** ← Critical!
- **RAGAS Baseline: 10/10** ← Must have table!
- **Advanced Retrieval: 5/5** ← Multi-query
- **Performance Compare: 10/10** ← Must show improvement!
- Documentation: 10/10
- Demo: 10/10

**Target: 98/100** ✨

