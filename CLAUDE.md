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

# Run tests
pytest                                  # All tests
pytest --cov=. --cov-report=term-missing  # With coverage
pytest tests/test_entities/              # Unit tests (entities)
pytest tests/test_storage/               # Unit tests (storage)
pytest tests/test_tools/                 # Unit tests (tools)
pytest tests/test_integration/           # Integration tests
pytest tests/test_acceptance/            # Acceptance tests

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

The project follows **Clean Architecture** principles with clear separation of concerns:
- **Domain entities** define core business logic (plain Python classes, not ORM models)
- **Protocol interfaces** defined by consumers (tools), not providers (storage)
- **Storage adapters** implement repository protocols using dependency inversion
- **Dependency injection** via ADK's `ToolContext` for session-aware operations

Key patterns:
- Tools define `Protocol` interfaces they need (consumer-driven contracts)
- BeancountAdapter implements those protocols as storage backend
- Agent wrapper functions inject session-specific repositories into tools
- SessionManager handles per-session file paths and ledger initialization

See `docs/ARCHITECTURE.md` for detailed architectural decisions and patterns.

### ADK Agent System

The project uses Google ADK's agent discovery pattern:
- **main.py**: FastAPI entry point using `get_fast_api_app()` from google.adk
  - `AGENT_DIR`: Points to `agents/` directory for auto-discovery
  - `SESSION_SERVICE_URI`: SQLite storage at `data/sessions.db`
  - `SERVE_WEB_INTERFACE`: Set to True to serve ADK web UI
- **agents/travelcount/agent.py**: Defines `root_agent` using ADK's `Agent` class
  - Model: gemini-2.5-flash
  - Tools registered with session-aware dependency injection wrappers
  - Wrappers extract session_id from `ToolContext` and inject session-specific repositories

### Module Structure

The agent follows Clean Architecture with these modules:

- **agents/travelcount/entities/**: Domain entities (Partner, etc.) as plain Python classes
- **agents/travelcount/storage/**: Storage adapters (BeancountAdapter, SessionManager)
- **agents/travelcount/tools/**: Agent tools and Protocol interfaces defined by consumers
- Sessions stored in `data/[session_id]/`:
  - `index.bean`: Beancount ledger file per session
  - `meta.json`: Session metadata (planned)

### Key Dependencies

- `google-adk>=1.18.0`: Agent framework with FastAPI integration
- `beancount>=3.2.0` & `beangulp>=0.2.0`: Accounting system
- `fastapi>=0.121.2` & `uvicorn[standard]>=0.38.0`: Web server
- `pytest>=9.0.1`: Testing framework
- `ruff>=0.14.5`: Linter/formatter (dev)

## Testing

Tests are organized by scope:
- `tests/test_entities/`: Unit tests for domain entities
- `tests/test_storage/`: Unit tests for storage adapters
- `tests/test_tools/`: Unit tests for agent tools
- `tests/test_integration/`: Integration tests across modules
- `tests/test_acceptance/`: End-to-end acceptance tests
- `tests/conftest.py`: Shared fixtures (temp_dir, session_manager, beancount_adapter, etc.)

Run tests using pytest (see Common Commands section above).

## Custom Slash Commands

This project includes custom slash commands in `.claude/commands/`:
- `/design feature_name [clarify to update]`: Create or update feature design documents
  - Searches `docs/features/` for feature specs
  - Creates design in `docs/design/` using template
  - Updates `docs/entities.md` if entities are involved
  - Uses Task tool to research codebase and external dependencies in parallel
- `/implement feature_name`: Implement feature based on design document
  - Searches `docs/design/` for design specs
  - Breaks down tasks and assigns to parallel Task tool agents
  - Monitors progress and integrates completed work

## Documentation

Feature workflow follows this structure:
1. Feature specs in `docs/features/`: User requirements and stories
2. Design docs in `docs/design/`: Technical design and implementation plan (created via `/design`)
3. Entity docs in `docs/entities.md`: Domain entity definitions (updated via `/design`)

Templates available in `docs/template/`:
- `design.md`: Feature design document template
- `entities.md`: Entity documentation template

## Implementation Status

- ✅ FastAPI server with ADK integration
- ✅ Agent registration with partner management tool
- ✅ Testing framework setup (unit, integration, acceptance)
- ✅ Documentation templates and workflow
- ✅ Partner entity and Beancount storage adapter
- ✅ Session-specific ledger management
- ⏳ Expense tracking functionality
- ⏳ Transaction management
- ⏳ Expense splitting and settlement
