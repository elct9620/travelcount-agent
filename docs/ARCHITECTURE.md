Architecture
===

This document provides an overview of the architecture of the TravelCount.

## Technology Stack

- Agent Development Kit (ADK) by Google
- Beancount

## Structure

The TravelCount is a Python application

```
|- agents/                # ADK agents directory
   |- travelcount/        # Main agent module
     |- __init__.py       # Initialization file
     |- agent.py          # Agent definition
     |- tools/            # Agent tools
     |- entities/         # Domain entities
     |- storage/          # Storage adapters
|- data/                  # Data storage
    |- [session_id]/      # Session-specific data
        |- meta.json      # Metadata file
        |- index.bean     # Beancount ledger file
|- docs/                  # Documentation
|- tests/                 # Test cases
|- main.py               # FastAPI entry point
|- pyproject.toml        # Project configuration
```

## Components

We are following Clean Architecture principles to structure the TravelCount application into distinct layers, each with specific responsibilities.

- The interface is defined by consumers, such as the TravelCount agent and web UI not the adapters.
- Use dependency inversion principle to decouple high-level modules from low-level modules.

### Entities

The domain entities define the domain models used in the TravelCount application, such as Account, Transaction, and Category.

- Plain Python classes are used to represent these entities.
- Not data models or ORM models, it should represent the core business logic and rules.

### TravelCount Agent

The TravelCount agent is built using the Agent Development Kit (ADK). It uses LLM (default: Gemini 2.5 Flash ) to process user inputs and help user in their travel, the major function is use beancount to track travel expenses.

The agent defines a `typing.Protocol` interface to as contract that other modules can implement it to provide specific functionalities.

```python
from typing import Protocol

class AccountRepository(Protocol):
    def add_account(self, name: str, currency: str) -> None:
        ...

    def remove_account(self, name: str) -> None:
        ...

    def list_accounts(self) -> list[str]:
        ...
```

### Storage Module

The beancount adapter is responsible to use beancount to store and retrieve travel expense data.

### Web UI

A FastAPI-based web interface use ADK's web interface directly to interact with users.
