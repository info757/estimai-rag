#!/usr/bin/env bash
#
# Setup script for EstimAI-RAG
#
# This script:
# 1. Creates Python virtual environment
# 2. Installs dependencies
# 3. Sets up .env file
# 4. Verifies installation

set -e

echo "============================================================"
echo "EstimAI-RAG Setup"
echo "============================================================"
echo

# Step 1: Create virtual environment
echo "Step 1: Creating virtual environment..."
if [ -d "venv" ]; then
    echo "  ⚠️  venv already exists, skipping"
else
    python3 -m venv venv
    echo "  ✅ Virtual environment created"
fi
echo

# Step 2: Activate and install dependencies
echo "Step 2: Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  ✅ Dependencies installed"
echo

# Step 3: Create .env file
echo "Step 3: Setting up .env file..."
if [ -f ".env" ]; then
    echo "  ⚠️  .env already exists, skipping"
else
    cp .env.example .env
    echo "  ✅ Created .env file"
    echo "  ⚠️  IMPORTANT: Edit .env and add your OPENAI_API_KEY"
fi
echo

# Step 4: Check Qdrant
echo "Step 4: Checking Qdrant..."
if curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo "  ✅ Qdrant is running"
else
    echo "  ❌ Qdrant not running"
    echo "  Start with: docker run -p 6333:6333 qdrant/qdrant"
fi
echo

echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Start Qdrant: docker run -p 6333:6333 qdrant/qdrant"
echo "3. Activate venv: source venv/bin/activate"
echo "4. Initialize KB: python scripts/setup_kb.py"
echo "5. Run tests: python scripts/test_system.py"
echo "6. Start server: uvicorn app.main:app --reload"
echo

