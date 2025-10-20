# EstimAI-RAG: Multi-Agent Construction Takeoff System

**AI Engineering Bootcamp Certification Project**

An intelligent construction takeoff system that analyzes PDF construction plans using Vision LLM, validates materials against a RAG knowledge base, and achieves 100% accuracy through multi-agent orchestration.

---

## 🎯 What It Does

Upload a construction PDF → Get instant, validated pipe counts with materials, lengths, and code compliance.

**Key Features**:
- ✅ 100% pipe counting accuracy (11/11 on test suite)
- ✅ Automatic material validation against construction standards
- ✅ Legend decoding for abbreviations (FPVC, SRPE, etc.)
- ✅ Unknown material detection with automatic web research (Tavily)
- ✅ Multi-view deduplication (plan + profile views)
- ✅ Real-time processing (~15 seconds per PDF)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- Tavily API key (optional, for unknown material research)

### Installation

```bash
# 1. Clone repo
git clone https://github.com/info757/estimai-rag.git
cd estimai-rag

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and TAVILY_API_KEY

# 5. Start Qdrant vector database
docker run -d -p 6333:6333 qdrant/qdrant

# 6. Initialize knowledge base
python scripts/setup_kb.py

# 7. Start backend
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 --loop asyncio
```

### Usage

**Option 1: Web UI**
1. Open browser: `http://localhost:8000/frontend/`
2. Drag-and-drop a construction PDF
3. Wait ~15 seconds
4. View results: pipe counts, materials, validation

**Option 2: API**
```bash
curl -X POST http://localhost:8000/takeoff \
  -F "file=@your_construction_plan.pdf"
```

---

## 🏗️ Architecture

### Multi-Agent System

```
PDF → Vision Agent (GPT-4o)
        ↓
      Supervisor Agent
        ↓
   ┌────┴────┬─────────┬────────┐
   ↓         ↓         ↓        ↓
 Storm   Sanitary   Water    Legend
Researcher Researcher Researcher Researcher
   ↓         ↓         ↓        ↓
        RAG Knowledge Base
         (48 standards)
              ↓
        Tavily API (fallback)
              ↓
        Validated Report
```

### Technology Stack

- **Vision**: GPT-4o (PDF analysis)
- **Orchestration**: LangGraph (agent workflow)
- **Vector DB**: Qdrant (hybrid search)
- **Retrieval**: BM25 + Semantic + RRF fusion
- **API Framework**: FastAPI
- **Evaluation**: RAGAS + Custom Metrics
- **External Search**: Tavily

---

## 📊 Performance

### Golden Dataset Results

| Test PDF | Pipes | Accuracy | Processing Time |
|----------|-------|----------|-----------------|
| test_01_simple_storm | 1 | 1/1 (100%) | ~10s |
| test_02_multi_utility | 3 | 3/3 (100%) | ~13s |
| test_03_validation | 1 | 1/1 (100%) | ~9s |
| test_04_abbreviations | 3 | 3/3 (100%) | ~13s |
| test_05_complex | 3 | 3/3 (100%) | ~18s |

**Overall**: 11/11 pipes (100% accuracy)

### RAGAS Evaluation

| Metric | Score |
|--------|-------|
| Context Precision | 86.7% |
| Context Recall | 100% |
| Faithfulness | 80% |
| Answer Relevancy | 97.5% |
| **Average** | **91.0%** |

---

## 🎓 Certification Deliverables

All certification requirements addressed in [`CERTIFICATION.md`](CERTIFICATION.md):

- ✅ Task 1: Problem & Audience definition
- ✅ Task 2: Solution proposal & tech stack
- ✅ Task 3: Data sources & chunking strategy
- ✅ Task 4: Working end-to-end prototype
- ✅ Task 5: RAGAS evaluation with golden dataset
- ✅ Task 6: Advanced retrieval implementation
- ✅ Task 7: Performance comparison baseline vs. advanced
- ✅ Final: Demo video + comprehensive documentation

---

## 📁 Project Structure

```
estimai-rag/
├── app/                          # Backend application
│   ├── agents/                   # Multi-agent system
│   │   ├── main_agent.py        # LangGraph orchestrator
│   │   ├── supervisor.py        # Validation coordinator
│   │   └── researchers/         # Domain-specific agents
│   ├── vision/                   # Vision agent framework
│   ├── rag/                      # RAG implementation
│   │   ├── retriever.py         # Hybrid search (BM25+Semantic)
│   │   ├── knowledge_base.py    # KB initialization
│   │   └── standards/           # Construction standards (JSON)
│   ├── evaluation/              # RAGAS framework
│   └── main.py                  # FastAPI server
├── frontend/                     # Web UI
│   └── index.html               # Drag-and-drop interface
├── golden_dataset/              # Test suite
│   ├── pdfs/                    # 5 test PDFs
│   └── ground_truth/            # Annotations
├── scripts/                      # Utilities
│   ├── setup_kb.py              # Initialize Qdrant
│   ├── run_ragas_comparison.py  # Evaluation
│   └── generate_*.py            # Test PDF generators
├── CERTIFICATION.md             # All certification deliverables
└── README.md                    # This file
```

---

## 🧪 Testing

### Run Full Evaluation

```bash
# Run RAGAS evaluation
python scripts/run_ragas_comparison.py

# Test all 5 golden dataset PDFs
python scripts/test_system.py
```

### Test Individual PDFs

```bash
# Via frontend: http://localhost:8000/frontend/
# Upload files from golden_dataset/pdfs/

# Via API:
curl -X POST http://localhost:8000/takeoff \
  -F "file=@golden_dataset/pdfs/test_02_multi_utility.pdf"
```

---

## 🎬 Demo

**Live Demo**: Upload any construction PDF at `http://localhost:8000/frontend/`

**Recommended Test**: `golden_dataset/pdfs/test_05_complex_realistic.pdf`
- Shows legend decoding in action
- Demonstrates unknown material detection
- Triggers Tavily API research
- Displays complete validation workflow

**Demo Video**: [5-Minute Loom Recording](https://www.loom.com/share/your-video-id)

---

## 📖 Documentation

- **[CERTIFICATION.md](CERTIFICATION.md)** - Complete certification submission
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture details
- **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** - Step-by-step demo guide
- **[golden_dataset/README.md](golden_dataset/README.md)** - Test dataset documentation

---

## 🔮 Future Roadmap

### Next Features
- Earthworks Vision Agent (grading, excavation quantities)
- Foundations Agent (footings, walls, slabs)
- Cost estimation integration
- Export to Excel/CSV for estimating software

### Scaling
- Multi-page PDF support (currently single page)
- Batch processing (multiple PDFs)
- Custom construction standards upload
- Integration with BIM models

---

## 📝 License

MIT License - See LICENSE file

---

## 👤 Author

**William Holt** - AI Engineering Bootcamp Certification Project  
**Cohort**: 8  
**Submission Date**: October 22, 2025

---

## 🙏 Acknowledgments

- AI Engineering Bootcamp instructors
- OpenAI (GPT-4o Vision)
- LangChain & LangGraph team
- Qdrant vector database
- Tavily API
