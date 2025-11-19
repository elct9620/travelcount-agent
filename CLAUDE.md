# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TravelCount is an agent built on Google's Agent Development Kit (ADK) and Beancount, designed to track and analyze travel expenses by session with friends. The agent uses LLM (default: Gemini 2.5 Flash) to process user inputs and manage travel expense tracking through beancount.

## Development Environment

This project uses **Devbox** for environment management with **uv** as the package manager. The `.envrc` file automatically activates the devbox environment via direnv.

### Common Commands

```bash
# Activate devbox shell (automatically activates .venv)
devbox shell

# Install/sync dependencies
uv sync

# Run the FastAPI development server
python main.py

# Lint and format Python code
ruff check --fix .
ruff format .
```

### Environment Setup

- Python >=3.13 required
- `PORT`: Override default port 8080
- `VENV_DIR`: Virtual environment directory (defaults to `.venv`)
- Auto-formatting: PostToolUse hook automatically runs `ruff check --fix` and `ruff format` on Python files after Edit/Write operations

## Architecture

### ADK Agent System

The project uses Google ADK's agent discovery pattern:
- **main.py**: FastAPI entry point using `get_fast_api_app()` from google.adk
  - `AGENT_DIR`: Points to `agents/` directory for auto-discovery
  - `SESSION_SERVICE_URI`: SQLite storage at `data/sessions.db`
  - `SERVE_WEB_INTERFACE`: Set to True to serve ADK web UI
- **agents/travelcount/agent.py**: Defines `root_agent` using ADK's `Agent` class
  - Model: gemini-2.5-flash
  - Currently a basic agent stub needing expense tracking implementation

### Planned Data Layer (Not Implemented)

Sessions will be stored in `data/[session_id]/`:
- `index.bean`: Beancount ledger file per session
- `meta.json`: Session metadata
- `storage/`: Beancount adapter module (planned)

### Key Dependencies

- `google-adk>=1.18.0`: Agent framework with FastAPI integration
- `beancount>=3.2.0` & `beangulp>=0.2.0`: Accounting system
- `fastapi>=0.121.2` & `uvicorn[standard]>=0.38.0`: Web server
- `ruff>=0.14.5`: Linter/formatter (dev)

## Implementation Status

- ✅ FastAPI server with ADK integration
- ✅ Basic agent registration
- ⏳ Beancount storage adapter
- ⏳ Expense tracking agent logic
- ⏳ Session-specific ledger management
