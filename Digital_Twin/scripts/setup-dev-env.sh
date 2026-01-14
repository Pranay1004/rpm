#!/bin/bash
# Complete Development Environment Setup Script
# Run this once to set up the entire RPM Digital Twin project

set -e

echo "================================"
echo "RPM Digital Twin Setup"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node -v)${NC}"
echo -e "${GREEN}✓ Python $(python3 --version)${NC}"

# Frontend setup
echo -e "\n${YELLOW}Setting up Frontend...${NC}"
cd src/frontend
npm install
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
cd ../..

# Backend setup
echo -e "\n${YELLOW}Setting up Backend...${NC}"
cd src/backend
npm install
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file (review and update database credentials)${NC}"
fi
cd ../..

# Analytics setup
echo -e "\n${YELLOW}Setting up Analytics (Python)...${NC}"
cd src/analytics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
echo -e "${GREEN}✓ Python virtual environment created${NC}"
echo -e "${GREEN}✓ Dependencies installed${NC}"

deactivate
cd ../..

# C++ setup (optional, requires CMake)
if command -v cmake &> /dev/null; then
    echo -e "\n${YELLOW}Setting up C++ Real-Time Engine...${NC}"
    cd src/rt_engine
    mkdir -p build
    cd build
    cmake ..
    make
    echo -e "${GREEN}✓ C++ engine built successfully${NC}"
    cd ../../..
else
    echo -e "${YELLOW}CMake not found. Skipping C++ build (install CMake to build RT engine)${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating data directories...${NC}"
mkdir -p data logs

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Review and update database credentials in src/backend/.env"
echo "2. Start the system in separate terminals:"
echo ""
echo "   Terminal 1 (Backend API):"
echo "   cd src/backend && npm run dev"
echo ""
echo "   Terminal 2 (Frontend GUI):"
echo "   cd src/frontend && npm run dev"
echo ""
echo "   Terminal 3 (Analytics):"
echo "   cd src/analytics && source venv/bin/activate && python app.py"
echo ""
echo "3. Open browser: http://localhost:5173"
echo ""
echo -e "${GREEN}Documentation:${NC}"
echo "- Quick Start: START_HERE.md"
echo "- Setup Guide: GETTING_STARTED.md"
echo "- Architecture: docs/architecture.md"
