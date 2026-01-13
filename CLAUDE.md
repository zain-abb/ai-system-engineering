# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SE-Agent** is an AI-powered Software Engineering Assistant built with Anthropic's Claude API. It assists developers with code generation, test generation, code review, requirements analysis, and documentation. The project includes a research component evaluating LLM quality attributes (correctness, robustness, safety, hallucination).

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY

# Run the API server
python -m src.main

# Run with Docker
docker-compose up --build

# Run tests
pytest tests/ -v

# Run linting
ruff check src/
mypy src/
```

## Architecture

```
USER INTERFACE (FastAPI + React Frontend)
            |
    ORCHESTRATION (Agent Controller)
            |
    CAPABILITY MODULES (Code Gen, Test Gen, Review, Requirements, Docs)
            |
    RAG LAYER (ChromaDB + Embeddings)
            |
    LLM SERVICE (Claude API Client)
            |
    EVALUATION (Correctness, Robustness, Safety, Hallucination)
```

## Source Code Structure

- `src/config.py` - Configuration management (API keys, costs, app settings)
- `src/main.py` - FastAPI application entry point
- `src/services/claude_client.py` - Anthropic API wrapper with cost tracking
- `src/agent/` - Agent orchestration and intent routing
- `src/capabilities/` - Code gen, test gen, review, requirements, docs modules
- `src/rag/` - Code indexer, vector store, retriever
- `src/evaluation/` - Quality evaluators (correctness, robustness, safety, hallucination)
- `src/ui/` - CLI interface

## Key APIs

```python
# Generate code
from src.services.claude_client import ClaudeClient
client = ClaudeClient()
result = client.generate(prompt="Write a function to...", system_prompt="You are an expert...")

# Check usage
stats = client.get_usage_stats()
```

## Environment Variables

Required in `.env`:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `CHROMA_HOST` - ChromaDB host (default: localhost)
- `CHROMA_PORT` - ChromaDB port (default: 8001)
- `DAILY_API_BUDGET` - Daily cost limit in USD (default: 10.0)

## Docker

```bash
# Start all services
docker-compose up --build

# Frontend UI at http://localhost:3000
# Backend API at http://localhost:8000
# ChromaDB at http://localhost:8001
```

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=src tests/
```
