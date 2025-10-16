#!/usr/bin/env bash
#
# Start Qdrant with Docker
#

set -e

# Add Docker to PATH
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

echo "🐳 Starting Qdrant with Docker..."
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon not running"
    echo "   Please start Docker Desktop and wait for it to finish starting"
    echo "   (Check for Docker icon in menu bar)"
    exit 1
fi

echo "✅ Docker is running"
echo

# Check if qdrant-estimai container already exists
if docker ps -a | grep -q qdrant-estimai; then
    echo "📦 Qdrant container exists"
    
    # Check if it's running
    if docker ps | grep -q qdrant-estimai; then
        echo "✅ Qdrant is already running"
    else
        echo "   Starting existing container..."
        docker start qdrant-estimai
        sleep 3
        echo "✅ Qdrant started"
    fi
else
    echo "📦 Creating new Qdrant container..."
    docker run -d \
      -p 6333:6333 \
      -p 6334:6334 \
      -v "$(pwd)/qdrant_storage:/qdrant/storage" \
      --name qdrant-estimai \
      qdrant/qdrant
    
    sleep 5
    echo "✅ Qdrant container created and started"
fi

echo

# Verify Qdrant is accessible
if curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo "✅ Qdrant is accessible at http://localhost:6333"
    echo "   Dashboard: http://localhost:6333/dashboard"
else
    echo "❌ Qdrant not accessible"
    echo "   Waiting a bit longer..."
    sleep 5
    if curl -s http://localhost:6333 > /dev/null 2>&1; then
        echo "✅ Qdrant is now accessible"
    else
        echo "❌ Still not accessible - check Docker Desktop"
        exit 1
    fi
fi

echo
echo "🎉 Qdrant is ready!"
echo
echo "Next steps:"
echo "  1. Initialize KB: python scripts/setup_kb.py"
echo "  2. Run tests: python scripts/test_system.py"
echo

