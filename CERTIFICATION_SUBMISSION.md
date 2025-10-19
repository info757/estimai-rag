# AI Engineering Certification Submission
**Candidate**: William Holt  
**Project**: Multi-Agent RAG Construction Takeoff System  
**Submission Date**: October 22, 2025

---

## Project Overview

An intelligent construction takeoff system that analyzes PDF construction plans using Vision LLM, validates materials against a RAG knowledge base, and escalates to external APIs for unknown materials. The system uses multi-agent orchestration to achieve 100% accuracy on pipe detection and counting.

---

## 1. Multi-Agent Architecture

### Agents Implemented (7 total)

1. **Main Agent** (Orchestrator)
   - LangGraph workflow coordinator
   - State management across agents
   - Error handling and fallback logic

2. **Vision Agent** (GPT-4o)
   - PDF-to-image conversion (300 DPI)
   - Structured data extraction
   - Single source of truth for counts

3. **Supervisor Agent** (Coordinator)
   - Material validation via RAG
   - Unknown detection and API escalation
   - LLM-based intelligent deduplication

4-6. **Specialized Researchers** (Storm, Sanitary, Water)
   - Domain-specific validation
   - RAG context retrieval
   - Standards compliance checking

7. **API Researcher** (Tavily)
   - External knowledge search
   - Deployed for unknown materials
   - ASTM/IPC standard lookup

### Orchestration Technology
- **LangGraph**: State-based workflow management
- **Parallel Execution**: Researchers run concurrently
- **Typed States**: AgentState, SupervisorState with validation

**Evidence**: See `app/agents/` directory, `docs/ARCHITECTURE.md`

---

## 2. RAG Implementation

### Vector Store
- **Technology**: Qdrant (self-hosted)
- **Collection**: construction_standards
- **Documents**: 48 construction standards
- **Embedding Model**: OpenAI text-embedding-3-small (1536 dimensions)

### Hybrid Retrieval
```python
def retrieve_hybrid(query, k=5):
    # 1. Semantic search (vector similarity)
    semantic_results = qdrant.search(embed(query), limit=k)
    
    # 2. BM25 search (keyword matching)
    bm25_results = bm25_encoder.search(query, limit=k)
    
    # 3. Reciprocal Rank Fusion
    return rrf_fusion(semantic_results, bm25_results, k=k)
```

### RAGAS Evaluation Results

| Metric | Score | Meaning |
|--------|-------|---------|
| **Context Precision** | 86.7% | Retrieved docs highly relevant |
| **Context Recall** | 100.0% | All necessary info retrieved |
| **Faithfulness** | 80.0% | Answers grounded in context |
| **Answer Relevancy** | 97.5% | Answers address questions |

**Average RAG Quality**: 91.0%

**Evidence**: `golden_dataset/ragas_results.json`, `app/rag/retriever.py`

---

## 3. Validated Dataset

### Golden Dataset Composition

| Test PDF | Pipes | Purpose | Accuracy |
|----------|-------|---------|----------|
| test_01_simple_storm.pdf | 1 | Basic detection | 1/1 (100%) |
| test_02_multi_utility.pdf | 3 | Multi-discipline | 3/3 (100%) |
| test_03_validation.pdf | 1 | Code compliance | 1/1 (100%) |
| test_04_abbreviations.pdf | 3 | Symbol recognition | 3/3 (100%) |
| test_05_complex_realistic.pdf | 3 | Unknown materials + API | 3/3 (100%) |

**Total**: 11 pipes across 5 PDFs with 100% detection accuracy

### Ground Truth Annotations

Each test includes:
- Expected pipe count by discipline
- Material specifications (RCP, PVC, DI, FPVC, SRPE)
- Diameter and length measurements
- Special test focus (validation, abbreviations, unknowns)

**Evidence**: `golden_dataset/ground_truth/*.json`, `golden_dataset/VERIFICATION_REPORT.md`

---

## 4. Key Innovations

### Vision-First Architecture
**Problem**: Traditional approach had researchers hallucinating pipes without seeing PDF  
**Solution**: Vision is single source of truth, researchers only validate  
**Result**: Eliminated over-counting (Test 02: 4/3 → 3/3)

### Content-Based Material Validation
**Problem**: RAG was returning generic results for unknown materials  
**Solution**: Check if material abbreviation appears in retrieved content  
**Result**: FPVC and SRPE correctly flagged as unknown, Tavily escalation working

### Prompt-Driven Deduplication
**Problem**: Multi-view drawings show same pipe twice  
**Solution**: LLM reasoning with context-aware prompt  
**Result**: Handles any naming convention without hard-coded rules

---

## 5. Production Readiness

### Performance
- **Average processing time**: 13 seconds per PDF
- **Vision analysis**: 8-10 seconds (OpenAI API)
- **RAG queries**: < 1 second each
- **Scalability**: Can handle multi-page documents

### Error Handling
- Vision failure → Fallback to researcher extraction
- RAG unavailable → Vision-only mode
- API rate limits → Graceful degradation
- All failures logged with traceback

### Testing
- Unit tests for retrieval (`tests/`)
- Integration tests for full workflow
- Golden dataset for regression testing
- RAGAS evaluation for RAG quality

**Evidence**: `app/main.py` (error handling), `scripts/test_*.py`

---

## 6. Demonstration Capability

### Live Demo Available
- **Endpoint**: `http://localhost:8000/takeoff`
- **Frontend**: `frontend/index.html` (drag-and-drop PDF upload)
- **Response**: Real-time JSON with pipe counts, materials, validation

### Demo Flow
1. Upload test_02_multi_utility.pdf
2. System detects: 3 pipes (storm, sanitary, water)
3. Validates all materials against RAG
4. Returns detailed report in ~13 seconds

### Advanced Demo (Unknown Materials)
1. Upload test_05_complex_realistic.pdf
2. System detects: 3 pipes with FPVC and SRPE
3. RAG validation: Materials not in knowledge base
4. Escalates to Tavily API automatically
5. Returns pipes + alert about unknown materials

---

## 7. Code Quality

### Architecture Principles
- **Separation of Concerns**: Each agent has single responsibility
- **Type Safety**: Pydantic models for all data structures
- **Logging**: Comprehensive logging at all levels
- **Modularity**: Easy to add new agents or capabilities

### Testing Coverage
- RAG retrieval quality (RAGAS: 91% avg)
- End-to-end workflow (Golden dataset: 100%)
- Known material validation (RCP, PVC, DI)
- Unknown material escalation (FPVC, SRPE → Tavily)

---

## 8. Documentation

### Included Documents
1. `README.md` - Project overview and setup
2. `QUICKSTART.md` - Get started in 5 minutes
3. `docs/ARCHITECTURE.md` - System architecture details
4. `docs/DEMO_SCRIPT.md` - Step-by-step demo guide
5. `DEMO_AND_CERT_STATUS.md` - Current status and timeline
6. `golden_dataset/VERIFICATION_REPORT.md` - Test validation results
7. `SUNDAY_STATUS.md` - Final implementation status

---

## 9. Repository

**GitHub**: https://github.com/info757/estimai-rag  
**Branch**: master  
**Latest Commit**: `523bb1f` - RAG validation fix (content-based checking)

### Key Files
- `app/agents/main_agent.py` - Main orchestrator
- `app/agents/supervisor.py` - Supervisor with validation
- `app/vision/` - Vision agent framework
- `app/rag/retriever.py` - Hybrid RAG retrieval
- `app/evaluation/ragas_eval.py` - RAGAS evaluation framework

---

## 10. Future Roadmap

### Immediate (Post-Certification)
- Add Earthworks Vision Agent
- Expand RAG to include grading standards
- Multi-page profile sheet handling

### 3-Month
- Foundation and structural takeoff
- Cost estimation integration
- Export to estimating software

### 6-Month
- Full MEP (mechanical, electrical, plumbing) support
- Integration with BIM models
- Automated code compliance checking

---

## Certification Checklist

- [x] Multi-agent system with 7+ agents
- [x] LangGraph orchestration
- [x] RAG implementation with vector store
- [x] Hybrid retrieval (BM25 + Semantic + RRF)
- [x] RAGAS evaluation (91% avg score)
- [x] Validated golden dataset (100% accuracy)
- [x] Vision LLM integration (GPT-4o)
- [x] API fallback (Tavily for unknowns)
- [x] Production-ready error handling
- [x] Comprehensive documentation
- [x] Live demo capability
- [x] Open source repository

---

## Appendix: Sample Output

### Test 05 Response (Unknown Materials)
```json
{
  "filename": "test_05_complex_realistic.pdf",
  "result": {
    "summary": {
      "total_pipes": 3,
      "storm_pipes": 1,
      "sanitary_pipes": 1,
      "water_pipes": 1,
      "total_lf": 1050.0
    },
    "pipes": [
      {
        "discipline": "storm",
        "material": "FPVC",
        "diameter_in": 24.0,
        "length_ft": 350.0
      },
      {
        "discipline": "sanitary",
        "material": "SRPE",
        "diameter_in": 12.0,
        "length_ft": 280.0
      },
      {
        "discipline": "water",
        "material": "DI",
        "diameter_in": 8.0,
        "length_ft": 420.0
      }
    ]
  },
  "user_alerts": {
    "severity": "WARNING",
    "message": "2 unknown materials detected: FPVC, SRPE",
    "unknown_materials": ["FPVC", "SRPE"]
  },
  "researcher_results": {
    "api_FPVC": {
      "task": "Research FPVC material",
      "findings": "... Tavily search results ..."
    },
    "api_SRPE": {
      "task": "Research SRPE material",
      "findings": "... Tavily search results ..."
    }
  }
}
```

---

**Submitted by**: William Holt  
**Project Repository**: https://github.com/info757/estimai-rag  
**Submission Date**: October 22, 2025

