Architecture
===

This document provides an overview of the architecture of the TravelCount.

## Technology Stack

- Agent Development Kit (ADK) by Google
- Beancount

## Structure

The TravelCount is a Python application

```
|- agents/                # ADK-based agents
   |- travelcount/        # Main agent module
     |- __init__.py       # Initialization file
|- storage/               # Storage module
   |- __init__.py         # Initialization file
|- web/                   # Web UI, mount ADK's web interface
    |- __init__.py        # Initialization file
|- data/                  # Data storage
    |- [session_id]/      # Session-specific data
        | meta.json       # Metadata file
        |- index.bean     # Bean file for session data
|- docs/                  # Documentation
   |- ARCHITECTURE.md     # Architecture overview
|- tests/                 # Test cases
|- pyproject.toml         # Project configuration
|- README.md              # Project overview
```

## Components

### TravelCount Agent

The TravelCount agent is built using the Agent Development Kit (ADK). It uses LLM (default: Gemini 2.5 Flash ) to process user inputs and help user in their travel, the major function is use beancount to track travel expenses.

### Storage Module

The beancount adapter is responsible to use beancount to store and retrieve travel expense data.

### Web UI

A FastAPI-based web interface use ADK's web interface directly to interact with users.
