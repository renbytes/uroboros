#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting uroboros Developer Setup...${NC}"

# 1. Check for Python 3.11+
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}Warning: Python 3.11 not found. Please install it.${NC}"
    echo "Recommended: pyenv install 3.11"
fi

# 2. Check for Poetry
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}Poetry not found. Installing...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
else
    echo -e "${GREEN}✓ Poetry found.${NC}"
fi

# 3. Install Dependencies
echo -e "${GREEN}📦 Installing Python Dependencies...${NC}"
poetry install

# 4. Setup Environment Variables
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  ACTION REQUIRED: Edit .env and add your API Keys!${NC}"
else
    echo -e "${GREEN}✓ .env file exists.${NC}"
fi

# 5. Create Data Directory
mkdir -p data/chromadb

# 6. Verify Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Warning: Docker not found. Sandboxing requires Docker.${NC}"
else
    echo -e "${GREEN}✓ Docker found.${NC}"
fi

echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "To run the agent: poetry run python -m uroboros.main"
echo "To run tests:     poetry run pytest"
