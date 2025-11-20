# Partner Design Document

This document outlines the design to implement the [Partner](../features/partner.md) feature in TravelCount using the Agent Development Kit (ADK).

## File Structure

In this feature, following files will be created or modified:

- `agents/travelcount/agent.py` - Register the partner management tool
- `agents/travelcount/tools/partner.py` - Partner management tool implementation
- `storage/beancount_adapter.py` - Beancount storage adapter for partner persistence
- `storage/session_manager.py` - Session-specific ledger file management
- `storage/protocols.py` - Protocol interfaces for repository pattern
- `entities/partner.py` - Partner domain entity
- `entities/__init__.py` - Entities module initialization
- `storage/__init__.py` - Storage module initialization

## Entities

In this feature, the related entities are following:

- **Partner**: Represents a travel partner who participates in shared expenses. Partners are identified by their name and represent the people who pay for expenses during a trip.

For detailed information about these entities, refer to the [Entities Documentation](../entities.md).

## Flow

The following flow describes how the Partner feature operates within TravelCount:

```plaintext
User Input
    |
    v
ADK Agent (root_agent)
    |
    v
Partner Tool (partners function)
    |
    +-- operation: "add" -----> PartnerRepository.add_partner()
    |                                   |
    |                                   v
    |                           BeancountAdapter.write_open_directive()
    |                                   |
    |                                   v
    |                           data/[session_id]/index.bean
    |
    +-- operation: "remove" --> PartnerRepository.remove_partner()
    |                                   |
    |                                   v
    |                           BeancountAdapter.write_close_directive()
    |                                   |
    |                                   v
    |                           data/[session_id]/index.bean
    |
    +-- operation: "list" ----> PartnerRepository.list_partners()
                                        |
                                        v
                                BeancountAdapter.read_partners()
                                        |
                                        v
                                data/[session_id]/index.bean
```

## Dependencies Relationship

In this feature, the components have the following dependencies relationship:

```plaintext
Partner Tool --(uses)--> PartnerRepository (Protocol)
PartnerRepository (Protocol) <--(implements)-- BeancountAdapter
BeancountAdapter --(uses)--> SessionManager
BeancountAdapter --(uses)--> Partner (Entity)
SessionManager --(manages)--> Beancount Files (data/[session_id]/index.bean)
ADK Agent --(registers)--> Partner Tool
```

## Components

### Partner Tool (`agents/travelcount/tools/partner.py`)

A function tool that provides the interface for managing travel partners through the LLM agent. This tool implements the function signature defined in the feature specification:

```python
def partners(operation: str, name: str = None) -> dict:
    """
    Manage travel partners.

    Args:
        operation (str): The operation to perform. Can be "add", "remove", or "list".
        name (str, optional): The name of the partner to add or remove.

    Returns:
        dict: A dictionary containing the result of the operation.
    """
```

**Responsibilities:**
- Validate input parameters (operation type, name presence for add/remove)
- Delegate to PartnerRepository for business logic
- Format responses for the LLM
- Handle errors and edge cases (duplicate adds, non-existent removes)

**Dependencies:**
- PartnerRepository (Protocol) - injected via dependency injection
- Current session context from ADK

### PartnerRepository Protocol (`storage/protocols.py`)

Defines the contract for partner management operations following Clean Architecture's dependency inversion principle:

```python
from typing import Protocol
from entities.partner import Partner

class PartnerRepository(Protocol):
    def add_partner(self, partner: Partner) -> None:
        """Add a new partner to the travel session."""
        ...

    def remove_partner(self, name: str) -> None:
        """Remove an existing partner from the travel session."""
        ...

    def list_partners(self) -> list[Partner]:
        """List all active partners in the travel session."""
        ...

    def partner_exists(self, name: str) -> bool:
        """Check if a partner exists in the travel session."""
        ...
```

**Design Rationale:**
- Using Protocol instead of abstract base class for looser coupling
- Consumer (Partner Tool) defines the interface it needs
- Implementation (BeancountAdapter) provides concrete behavior
- Easy to mock for testing
- Allows future alternative storage implementations

### BeancountAdapter (`storage/beancount_adapter.py`)

Concrete implementation of PartnerRepository that uses Beancount as the storage backend. This adapter translates between the Partner domain entity and Beancount's account system.

**Responsibilities:**
- Translate Partner entities to/from Beancount account directives
- Read and parse Beancount ledger files using `beancount.loader`
- Write Open directives using `beancount.core.data.Open`
- Write Close directives using `beancount.core.data.Close`
- Filter accounts by prefix (Assets:Travel:Partners:*)
- Use `beancount.parser.printer.print_entry` for writing directives

**Key Implementation Details:**
- Partners are stored as Beancount accounts: `Assets:Travel:Partners:[PartnerName]`
- Open directive format: `YYYY-MM-DD open Assets:Travel:Partners:Alice USD`
- Close directive format: `YYYY-MM-DD close Assets:Travel:Partners:Alice`
- Use current date for open/close operations
- Parse existing file to check for duplicates before adding
- Append new directives to maintain chronological order
- Convert account names back to Partner entities when reading

**Dependencies:**
- SessionManager - to get current session's ledger file path
- Partner (Entity) - domain model for partners
- beancount.core.data - for creating directive objects
- beancount.parser.printer - for writing directives to file
- beancount.loader - for parsing existing ledger files

### SessionManager (`storage/session_manager.py`)

Manages session-specific data and file paths for Beancount ledgers.

**Responsibilities:**
- Provide path to current session's ledger file (`data/[session_id]/index.bean`)
- Create session directory if it doesn't exist
- Initialize empty ledger file if needed
- Manage session metadata (`data/[session_id]/meta.json`)

**Key Implementation Details:**
- Get session ID from ADK session context
- Ensure directory structure exists: `data/[session_id]/`
- Create initial `index.bean` with standard Beancount header if new session
- Store session metadata (creation date, description, etc.)

**Dependencies:**
- ADK session service (from environment)
- Python pathlib for file operations
- json module for metadata management

### Partner Entity (`entities/partner.py`)

Domain entity representing a travel partner in the TravelCount system.

**Responsibilities:**
- Represent a partner's identity (name)
- Validate partner names to ensure they can be safely used in storage
- Provide domain meaning separate from storage implementation

**Key Attributes:**
- `name: str` - The partner's name (e.g., "Alice", "Bob")

**Key Methods:**
- `validate_name(name: str)` - Ensure name is valid (non-empty, no special characters that would break Beancount)

**Design Rationale:**
- Plain Python class (not ORM model or Beancount account)
- Keeps domain logic separate from storage details (Beancount accounts are implementation)
- Simple and focused on identifying who paid for expenses
- Self-validating to prevent invalid state

## Testing

### Add New Partner

**Scenario:** User adds a partner named "Alice" to the travel session.

**Deliverables:**
- Partner "Alice" is persisted in the Beancount ledger as `Assets:Travel:Partners:Alice`
- Open directive is written with current date: `YYYY-MM-DD open Assets:Travel:Partners:Alice USD`
- Agent responds "Partner 'Alice' has been added."

**Test Coverage:**
- Unit: `test_create_partner_with_valid_name()`, `test_add_partner_writes_open_directive()`
- Integration: `test_add_list_remove_partner_flow()`, `test_multiple_partners_persistence()`
- Acceptance: `test_scenario_add_new_partner()`

### Remove Existing Partner

**Scenario:** User removes a partner named "Alice" from the travel session.

**Deliverables:**
- Close directive is written with current date: `YYYY-MM-DD close Assets:Travel:Partners:Alice`
- Partner "Alice" no longer appears in partner list
- Agent responds "Partner 'Alice' has been removed."

**Test Coverage:**
- Unit: `test_remove_partner_writes_close_directive()`, `test_list_partners_excludes_closed_partners()`
- Integration: `test_add_list_remove_partner_flow()`
- Acceptance: `test_scenario_remove_existing_partner()`

### List All Partners

**Scenario:** User requests to see all active travel partners.

**Deliverables:**
- Returns all partners with open accounts (excluding closed accounts)
- Formatted response: "Your travel partners are: Alice, Bob."
- Empty list response: "You have no travel partners yet."

**Test Coverage:**
- Unit: `test_list_partners_returns_all_active_partners()`, `test_partners_list_operation_success()`
- Integration: `test_multiple_partners_persistence()`
- Acceptance: `test_scenario_list_all_partners()`

### Handle Duplicate Partner

**Scenario:** User attempts to add a partner that already exists.

**Deliverables:**
- No duplicate entry is created in the ledger
- Error message returned: "Partner 'Alice' already exists."
- System maintains data integrity

**Test Coverage:**
- Unit: `test_add_partner_raises_error_for_duplicate()`, `test_partners_add_handles_duplicate_error()`, `test_partner_exists_returns_true_for_existing_partner()`
- Acceptance: `test_scenario_add_duplicate_partner()`

### Handle Non-existent Partner

**Scenario:** User attempts to remove a partner that doesn't exist.

**Deliverables:**
- No changes to the ledger
- Error message returned: "Partner 'Bob' does not exist."
- System gracefully handles the error

**Test Coverage:**
- Unit: `test_remove_partner_raises_error_for_nonexistent()`, `test_partners_remove_handles_nonexistent_error()`, `test_partner_exists_returns_false_for_nonexistent_partner()`
- Acceptance: `test_scenario_remove_nonexistent_partner()`

### Validate Partner Names

**Scenario:** User provides invalid partner names (empty, special characters, path traversal).

**Deliverables:**
- Validation rejects empty strings, whitespace-only, special characters (@, $, :), path traversal (../)
- Error message indicating invalid name format
- Security: prevents injection attacks and file system manipulation

**Test Coverage:**
- Unit: `test_validate_name_rejects_empty_string()`, `test_validate_name_rejects_whitespace_only()`, `test_validate_name_rejects_special_characters()`, `test_validate_name_rejects_path_traversal_attempts()`

### Session Isolation

**Scenario:** Multiple travel sessions with different partners.

**Deliverables:**
- Each session has its own ledger file: `data/[session_id]/index.bean`
- Partners in session1 are not visible in session2
- Session data remains isolated and secure

**Test Coverage:**
- Integration: `test_session_isolation()`
- Unit: `test_get_ledger_path_returns_correct_path()`, `test_ensure_session_directory_creates_directory()`

### Beancount Integration

**Scenario:** Partner data is correctly persisted and loaded from Beancount files.

**Deliverables:**
- Open directives use correct format and account structure
- Close directives properly mark accounts as closed
- Beancount parser correctly loads partner data
- Account translation works bidirectionally (entity ↔ account name)

**Test Coverage:**
- Unit: `test_account_name_translation_to_partner_entity()`, `test_partner_entity_translation_to_account_name()`, `test_add_partner_uses_current_date()`
- Integration: `test_beancount_file_parsing_integration()`

### Dependency Injection

**Scenario:** Partner tool uses repository protocol for loose coupling.

**Deliverables:**
- Tool accepts PartnerRepository via dependency injection
- Can be tested with mock repositories (no file system needed)
- Implementation can be swapped without changing tool code

**Test Coverage:**
- Unit: `test_partners_tool_uses_dependency_injection()`

### Test Execution

Run tests using pytest:
```bash
pytest                                  # All tests
pytest --cov=. --cov-report=term-missing  # With coverage
pytest tests/test_entities/              # Unit tests (entities)
pytest tests/test_storage/               # Unit tests (storage)
pytest tests/test_tools/                 # Unit tests (tools)
pytest tests/test_integration/           # Integration tests
pytest tests/test_acceptance/            # Acceptance tests
```

**Test Structure:**
```
tests/
├── test_entities/test_partner.py        (6 unit tests)
├── test_storage/test_beancount_adapter.py  (12 unit tests)
├── test_storage/test_session_manager.py    (7 unit tests)
├── test_tools/test_partner_tool.py      (10 unit tests)
├── test_integration/test_partner_operations.py  (4 integration tests)
├── test_acceptance/test_partner_scenarios.py    (5 acceptance tests)
└── conftest.py                          (shared fixtures)
```

**Success Criteria:**
- ✅ All 44 tests pass
- ✅ 100% coverage for domain logic
- ✅ Test execution time < 30 seconds
