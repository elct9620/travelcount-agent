# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TravelCount is an agent built on Google's Agent Development Kit (ADK) and Beancount, designed to track and analyze travel expenses by session with friends. The agent uses LLM (default: Gemini 2.5 Flash) to process user inputs and manage travel expense tracking through beancount.

## Development Environment

This project uses **Devbox** for environment management with **uv** as the package manager.

### Setup Commands

```bash
# Activate devbox shell (automatically activates .venv)
devbox shell

# Install dependencies
uv sync

# Run the FastAPI development server
python main.py

# The server runs on http://localhost:8080 by default
```

Environment variables:
- `PORT`: Override the default port 8080
- `VENV_DIR`: Virtual environment directory (defaults to `.venv`)

## Architecture

### Key Components

1. **main.py**: FastAPI entry point that initializes the ADK web interface
   - Uses `get_fast_api_app()` from google.adk to mount the agent
   - Configures session storage with SQLite (`data/sessions.db`)
   - Serves the ADK web interface directly

2. **agents/travelcount/**: Main agent module
   - `agent.py`: Defines the root_agent using ADK's `Agent` class
   - Currently a basic agent configuration using gemini-2.5-flash model

3. **Planned Components** (per ARCHITECTURE.md, not yet implemented):
   - `storage/`: Beancount adapter for expense data
   - `web/`: Web UI mounting point
   - `data/[session_id]/`: Session-specific beancount files
     - `meta.json`: Session metadata
     - `index.bean`: Beancount ledger file

### ADK Integration

The project uses Google ADK's FastAPI integration:
- Agents are discovered from the `agents/` directory
- Session management via `session_service_uri` (SQLite)
- CORS configured for local development and production
- Web interface automatically served when `web=True`

### Data Architecture

Sessions are stored in `data/[session_id]/`:
- Each session has its own beancount ledger (`index.bean`)
- Metadata tracked in `meta.json`
- Sessions managed through ADK's session service

## Dependencies

Core dependencies:
- `google-adk>=1.18.0`: Agent Development Kit framework
- `beancount>=3.2.0`: Double-entry accounting system
- `beangulp>=0.2.0`: Beancount ingestion framework
- `fastapi>=0.121.2` & `uvicorn[standard]>=0.38.0`: Web framework

Requires Python >=3.13

## Development Notes

- The storage module (beancount adapter) is planned but not yet implemented
- The agent currently uses a basic LLM configuration and needs expansion for expense tracking features
- Session data is stored in SQLite; beancount files are session-specific
- The web interface is served directly from ADK without custom UI components
