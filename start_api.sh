#!/bin/bash

# TRELLIS Text-to-3D API Startup Script
# This script starts the TRELLIS Text-to-3D API server

set -e

# Configuration
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting TRELLIS Text-to-3D API${NC}"
echo -e "${BLUE}=================================${NC}"

# Check if CUDA is available
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
else
    echo -e "${YELLOW}⚠ No NVIDIA GPU detected - API will run on CPU (very slow)${NC}"
fi

# Check Python environment
if ! python -c "import torch; print('PyTorch version:', torch.__version__)" 2>/dev/null; then
    echo -e "${RED}❌ PyTorch not found. Please install the required dependencies.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PyTorch detected${NC}"

# Check if TRELLIS modules are available
if ! python -c "from trellis.pipelines import TrellisTextTo3DPipeline" 2>/dev/null; then
    echo -e "${RED}❌ TRELLIS not found. Please make sure TRELLIS is properly installed.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TRELLIS modules available${NC}"

# Check FastAPI
if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo -e "${RED}❌ FastAPI/Uvicorn not found. Installing...${NC}"
    pip install fastapi uvicorn[standard] pydantic
fi

echo -e "${GREEN}✓ FastAPI dependencies available${NC}"

# Create necessary directories
mkdir -p tmp
mkdir -p generated

# Set environment variables for optimal performance
export SPCONV_ALGO=native

echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "   Host: ${HOST}"
echo -e "   Port: ${PORT}"
echo -e "   Workers: ${WORKERS}"
echo -e "   SPCONV_ALGO: ${SPCONV_ALGO}"
echo ""

echo -e "${BLUE}🌐 API will be available at:${NC}"
echo -e "   ${GREEN}http://localhost:${PORT}${NC} - Main API"
echo -e "   ${GREEN}http://localhost:${PORT}/docs${NC} - Interactive Documentation"
echo -e "   ${GREEN}http://localhost:${PORT}/health${NC} - Health Check"
echo ""

echo -e "${YELLOW}Loading TRELLIS model (this may take a few minutes on first run)...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the API server
python text_to_3d_api.py --host "$HOST" --port "$PORT" --workers "$WORKERS"
