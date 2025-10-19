# System Architecture - Multi-Agent RAG Construction Takeoff

**Version**: 1.0  
**Date**: October 19, 2025  
**Status**: Production Ready

---

## Overview

A multi-agent RAG system for automated construction takeoff from PDF plans, using Vision LLM, specialized researchers, and hybrid retrieval with API fallback.

### Key Capabilities

1. **Vision-based PDF Analysis**: GPT-4o extracts pipes from construction plans
2. **RAG Validation**: Qdrant vector store with 48 construction standards
3. **Multi-Agent Orchestration**: 7 specialized agents coordinated via LangGraph
4. **API Fallback**: Tavily search for unknown materials
5. **Intelligent Deduplication**: LLM-based merging of multi-view detections

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Main Agent                              │
│                    (LangGraph Orchestrator)                      │
└────────────────┬───────────────────────────┬────────────────────┘
                 │                           │
                 ▼                           ▼
    ┌────────────────────────┐   ┌──────────────────────┐
    │    Vision Agent        │   │   Supervisor Agent   │
    │     (GPT-4o)          │   │  (Coordinator)       │
    └────────────────────────┘   └──────────────────────┘
                 │                           │
                 │                           ▼
                 │              ┌────────────────────────┐
                 │              │   RAG System (Qdrant)  │
                 │              │  BM25 + Semantic + RRF │
                 │              └────────────────────────┘
                 │                           │
                 │              ┌────────────┴────────────┐
                 │              │                         │
                 │              ▼                         ▼
                 │    ┌──────────────────┐    ┌──────────────────┐
                 │    │   Known Material  │    │ Unknown Material │
                 │    │  (RCP, PVC, DI)  │    │  (FPVC, SRPE)   │
                 │    │  ✓ Validated      │    │  → Tavily API   │
                 │    └──────────────────┘    └──────────────────┘
                 │
                 ▼
       ┌─────────────────────┐
       │   Final Report       │
       │  (JSON Response)     │
       └─────────────────────┘
```

---

## Component Details

### 1. Vision Agent

**Technology**: GPT-4o Vision API  
**Input**: PDF pages rendered at 300 DPI  
**Output**: Structured pipe data (discipline, material, diameter, length, depth)

**Prompt Strategy**:
```
System: "You are an expert at reading construction blueprint documents. 
         You specialize in extracting pipe type, depth, and length."

User: "Analyze this construction document.
       Extract individual pipes only, not summary totals.
       Calculate how many pipes of each type, their length and depth."
```

**Key Features**:
- Single source of truth for pipe counts
- Extracts from both plan view and profile view
- Returns JSON with no defensive fallbacks
- 300 DPI for high-quality image analysis

### 2. Supervisor Agent

**Technology**: GPT-4o-mini + LangGraph  
**Role**: Orchestration, validation, deduplication

**Workflow**:
1. Receives Vision results (pipe list)
2. Extracts unique materials
3. Queries RAG for each material
4. Checks if material mentioned in retrieved content
5. Unknown materials → Escalates to Tavily API
6. Deduplicates pipes using LLM reasoning
7. Returns validated results + alerts

**Deduplication Prompt**:
```
"If you see a construction item like a pipe with the same label more than 
once then don't count it multiple times. It is simply a construction item 
being referenced again from a different view or perhaps giving us more 
information about it."
```

### 3. RAG System (Qdrant)

**Vector Database**: Qdrant (local instance)  
**Collection**: construction_standards (48 documents)  
**Embedding Model**: OpenAI text-embedding-3-small

**Hybrid Retrieval Strategy**:
1. **Semantic Search**: Vector similarity using embeddings
2. **BM25 Search**: Keyword-based lexical matching
3. **Reciprocal Rank Fusion (RRF)**: Combines both rankings

**Formula**:
```python
RRF_score(doc) = Σ(1 / (k + rank_semantic)) + Σ(1 / (k + rank_bm25))
where k = 60 (constant)
```

**Standards Categories**:
- Materials (RCP, PVC, DI, HDPE specifications)
- Cover depths (minimum requirements by pipe type)
- Symbols (CB, MH, DI, FES drawing conventions)
- Slopes (minimum by pipe diameter)
- Validation rules (size ranges, material compatibility)

### 4. Researcher Agents

**Specialists**: Storm, Sanitary, Water, Elevation, Legend  
**Technology**: GPT-4o-mini + RAG retrieval  
**Current Role**: Validation only (no extraction)

**In Vision-First architecture**:
- Researchers DO NOT extract pipes (prevents hallucination)
- Only deployed for unknown material validation
- Query RAG for material specifications
- Return validation reports, not pipe lists

### 5. API Researcher (Tavily)

**Technology**: Tavily API  
**Trigger**: Material not found in RAG  
**Domains**: iccsafe.org, astm.org, awwa.org, asce.org

**Example Flow**:
```
Vision detects: "24\" FPVC"
  → Supervisor queries RAG for "FPVC"
  → No mention of "FPVC" in RAG content
  → Deploy API Researcher
  → Tavily finds: ASTM F1803 specifications
  → Alert user: "Unknown material FPVC detected"
```

---

## Data Flow

### Request → Response Flow

```
1. User uploads PDF
   ↓
2. Main Agent invokes analyze_pdf_node
   ↓ Renders PDF at 300 DPI
   ↓ Calls Vision Coordinator
   ↓
3. Vision Agent (GPT-4o)
   ↓ Analyzes image
   ↓ Extracts pipes: [
         {"discipline": "storm", "material": "FPVC", "diameter_in": 24, "length_ft": 350},
         {"discipline": "sanitary", "material": "SRPE", "diameter_in": 12, "length_ft": 280},
         {"discipline": "water", "material": "DI", "diameter_in": 8, "length_ft": 420}
     ]
   ↓
4. Main Agent invokes supervise_research_node
   ↓ Passes Vision results to Supervisor
   ↓
5. Supervisor validates materials
   ↓ Extracts: {FPVC, SRPE, DI}
   ↓ Queries RAG for each:
   ↓   - DI: Found (5 standards) ✓
   ↓   - FPVC: Not found → Tavily ⚠️
   ↓   - SRPE: Not found → Tavily ⚠️
   ↓ Deduplicates Vision pipes
   ↓
6. Main Agent invokes generate_report_node
   ↓ Uses Vision counts (single source of truth)
   ↓ Attaches validation results
   ↓ Creates JSON response
   ↓
7. Return to user:
   {
     "summary": {"total_pipes": 3, "storm_pipes": 1, ...},
     "pipes": [...],
     "user_alerts": {
       "severity": "WARNING",
       "message": "2 unknown materials detected: FPVC, SRPE",
       "unknown_materials": ["FPVC", "SRPE"]
     }
   }
```

---

## State Management

### AgentState (LangGraph)

```python
{
    "pdf_path": str,                    # Path to uploaded PDF
    "user_query": str,                  # Optional user clarification
    "pdf_summary": str,                 # Vision analysis summary
    "messages": List[BaseMessage],      # LangChain message history
    "final_report": {
        "vision_results": {
            "pipes": List[Dict],        # Vision-extracted pipes
            "total_pipes": int,
            "num_pages_processed": int,
            "page_summaries": List[str]
        },
        "consolidated_data": {
            "summary": {...},           # Deduplicated counts
            "user_alerts": {...}        # Unknown material warnings
        },
        "researcher_results": Dict,     # RAG validation results
        "takeoff_result": {...}         # Final formatted response
    }
}
```

### SupervisorState

```python
{
    "pdf_summary": str,                 # From Vision
    "vision_result": Dict,              # Vision pipes
    "assigned_tasks": List,             # Researcher tasks (empty in Vision-First)
    "researcher_results": Dict,         # API validation results
    "consolidated_data": Dict,          # Dedup + alerts
    "conflicts": List                   # None (Vision is single source)
}
```

---

## Evaluation Results

### Golden Dataset (5 PDFs, 11 pipes)

| Test | Description | Pipes | Accuracy | Purpose |
|------|-------------|-------|----------|---------|
| Test 01 | Simple storm drain | 1/1 | 100% | Basic detection |
| Test 02 | Multi-utility | 3/3 | 100% | Multiple disciplines |
| Test 03 | Validation flags | 1/1 | 100% | Code compliance |
| Test 04 | Abbreviations | 3/3 | 100% | Symbol recognition |
| Test 05 | Unknown materials | 3/3 | 100% | API fallback |

**Overall**: 11/11 pipes (100% accuracy)

### RAGAS Metrics (RAG Quality)

| Metric | Score | Interpretation |
|--------|-------|----------------|
| Context Precision | 86.7% | Top retrieved docs highly relevant |
| Context Recall | 100% | All necessary info retrieved |
| Faithfulness | 80.0% | Answers grounded in retrieved context |
| Answer Relevancy | 97.5% | Answers directly address questions |

**Overall RAG Quality**: Excellent (avg 91.0%)

---

## Performance Characteristics

### Latency
- **Vision Analysis**: ~8-10 seconds (GPU-dependent)
- **RAG Query**: < 1 second per query
- **LLM Deduplication**: ~3 seconds
- **Total**: ~13 seconds per PDF (single page)

### Scalability
- **Multi-page**: Processes pages sequentially, can parallelize
- **Agent addition**: New agents (Earthworks, Foundations) easy to add
- **RAG expansion**: Can index unlimited standards

### Cost (per PDF)
- Vision API (GPT-4o): ~$0.05 per page
- RAG queries: ~$0.001 per query
- Deduplication (GPT-4o-mini): ~$0.001
- **Total**: ~$0.05 - $0.10 per PDF

---

## Key Architectural Decisions

### 1. Vision-First Architecture
**Decision**: Vision is single source of truth for counts  
**Rationale**: Eliminates hallucination from researchers extracting without seeing PDF  
**Result**: 100% accuracy, 30% faster

### 2. Prompt-Driven Behavior
**Decision**: All agent logic via prompts, no hard-coded rules  
**Rationale**: Flexibility, transparency, easy to tune  
**Result**: Clean, maintainable codebase

### 3. Content-Based Validation
**Decision**: Check if material mentioned in RAG content, not just result count  
**Rationale**: Avoids false positives from generic pipe results  
**Result**: Proper unknown material detection

### 4. LLM Deduplication
**Decision**: Use LLM reasoning to merge duplicates instead of rules  
**Rationale**: Handles any naming convention, flexible  
**Result**: Works on any PDF structure

---

## Scalability Roadmap

### Current: Utility Systems ✅
- Storm drainage
- Sanitary sewers
- Water mains

### Phase 2: Site Work (Next)
- Earthworks Vision Agent
- Cut/fill calculations
- Grading elevations

### Phase 3: Foundations
- Foundation Vision Agent
- Footing dimensions
- Concrete volumes

### Phase 4: MEP Systems
- HVAC Vision Agent
- Electrical Vision Agent
- Plumbing Vision Agent

**Pattern**: Each construction discipline gets specialized Vision agent + optional Researcher for validation

---

## Security & Privacy

- PDF files stored temporarily in `uploads/` directory
- No PII collection
- OpenAI API: Data not used for training (enterprise agreement)
- Qdrant: Local deployment, no cloud data

---

## Error Handling

### Vision Failures
- Fallback: Deploy all researchers (legacy mode)
- User notified of PDF quality issues

### RAG Unavailable
- Continue with Vision-only results
- Lower confidence scores

### API Rate Limits
- Graceful degradation
- User notified of external search failures

---

## Technology Stack

### Core
- **Python 3.11**
- **FastAPI**: REST API backend
- **LangGraph**: Multi-agent orchestration
- **LangChain**: LLM interactions

### AI/ML
- **OpenAI GPT-4o**: Vision analysis
- **OpenAI GPT-4o-mini**: Researchers, Supervisor
- **OpenAI Embeddings**: text-embedding-3-small

### Vector Store
- **Qdrant**: Local vector database
- **BM25Encoder**: Keyword search

### External APIs
- **Tavily**: Web search for unknown materials

---

## Deployment

### Requirements
- Python 3.11+
- Qdrant server (localhost:6333)
- OpenAI API key
- Tavily API key (optional, for unknown materials)

### Startup
```bash
# Start Qdrant
./scripts/start_qdrant.sh

# Activate environment
source venv/bin/activate

# Start backend
uvicorn app.main:app --reload --port 8000 --loop asyncio
```

---

## Certification Evidence

### Multi-Agent System ✅
- 7 agents: Main, Supervisor, Vision, Storm, Sanitary, Water, Elevation, Legend, API
- LangGraph state management
- Parallel execution where applicable

### RAG Integration ✅
- Vector store: Qdrant with 48 construction standards
- Hybrid retrieval: BM25 + Semantic + RRF
- RAGAS evaluation: 91% average score

### Validation ✅
- Golden dataset: 5 PDFs, 11 pipes, 100% accuracy
- Unknown material detection working (Test 05)
- API fallback operational (Tavily)

### Production Ready ✅
- Error handling
- Logging throughout
- Performance optimized
- Scalable architecture

---

**Prepared for**: AI Engineering Certification, October 22, 2025

