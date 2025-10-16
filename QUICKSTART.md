# QuickStart Guide

## After Installing Docker Desktop

### 1. Start Docker Desktop
- Open Docker Desktop application
- Wait for it to fully start (you'll see "Docker Desktop is running" in menu bar)
- Verify: Run `docker --version` in terminal

### 2. Start Qdrant

```bash
cd /Users/williamholt/estimai-rag

# Start Qdrant container
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name qdrant-estimai \
  qdrant/qdrant

# Wait 5 seconds for startup
sleep 5

# Verify it's running
curl http://localhost:6333
# Should see: {"title":"qdrant - vector search engine",...}
```

### 3. Initialize Knowledge Base

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Initialize Qdrant with construction standards
python scripts/setup_kb.py
```

**Expected Output:**
```
✅ Loaded 48 standards
✅ Connected to Qdrant at http://localhost:6333
✅ Collection created and indexed
✅ Hybrid retrieval working
```

### 4. Run System Tests

```bash
python scripts/test_system.py
```

**Target: 7/7 tests passing** ✅

### 5. Start Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```

**Verify:**
- Go to http://localhost:8000/docs
- Should see FastAPI documentation
- Try `/health` endpoint

### 6. Test Takeoff

```bash
# In another terminal
curl -X POST http://localhost:8000/takeoff/simple \
  -H "Content-Type: application/json" \
  -d '{"pdf_path": "test.pdf", "user_query": "Extract all pipes"}'
```

## Troubleshooting

### Docker Not Starting
- Make sure Docker Desktop is fully running (green light in menu bar)
- Try: `docker ps` to verify

### Qdrant Connection Refused
```bash
# Check if container is running
docker ps | grep qdrant

# If not running, start it
docker start qdrant-estimai

# Or remove and recreate
docker rm qdrant-estimai
docker run -d -p 6333:6333 --name qdrant-estimai qdrant/qdrant
```

### API Key Not Found
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY

# Export manually
export OPENAI_API_KEY=sk-...
```

### Import Errors
```bash
# Activate venv
source venv/bin/activate

# Reinstall if needed
pip install -r requirements.txt
```

## Quick Commands Reference

```bash
# Start everything
docker start qdrant-estimai
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
uvicorn app.main:app --reload

# Stop everything
docker stop qdrant-estimai

# Reset Qdrant (fresh start)
docker rm -f qdrant-estimai
docker run -d -p 6333:6333 --name qdrant-estimai qdrant/qdrant
python scripts/setup_kb.py

# View Qdrant Dashboard
open http://localhost:6333/dashboard
```

## Next Steps After Tests Pass

1. ✅ Test with a real PDF
2. ✅ Create golden dataset
3. ✅ Run RAGAS evaluation
4. ✅ Implement advanced retrieval
5. ✅ Write documentation
6. ✅ Record demo

**You're ready to ace this certification!** 🚀

