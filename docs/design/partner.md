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

## Implementation Notes

### Beancount Storage Mapping

Partners (domain entities) are persisted as Beancount accounts using this structure:
```
Assets:Travel:Partners:[PartnerName]
```

Where:
- `Assets` - Root account type (one of five: Assets, Liabilities, Equity, Income, Expenses)
- `Travel` - Subaccount for travel-related assets
- `Partners` - Subaccount grouping all partner accounts
- `[PartnerName]` - Individual partner's name (capitalized, no spaces)

**Important:** This is a storage implementation detail. The domain layer works with Partner entities, not Beancount accounts. The BeancountAdapter handles the translation.

### Error Handling

The partner tool should handle these scenarios gracefully:
- Adding duplicate partner - return error message
- Removing non-existent partner - return error message
- Invalid partner names (spaces, special characters) - validate and return error
- Missing required parameters - return error message
- File I/O errors - log and return user-friendly error

### Testing Strategy

Following TDD principles, tests should be written for:
1. **Unit Tests:**
   - Partner entity validation logic
   - BeancountAdapter translation between Partner and Beancount accounts
   - BeancountAdapter read/write operations (mock file system)
   - Partner tool parameter validation

2. **Integration Tests:**
   - End-to-end partner add/remove/list operations
   - SessionManager with real file system (temporary directories)
   - Beancount file parsing and writing

3. **Acceptance Tests:**
   - Gherkin scenarios from feature specification
   - Test against actual ADK agent integration

### Security Considerations

- Validate partner names to prevent directory traversal or injection attacks
- Sanitize inputs before writing to Beancount files
- Ensure session isolation (one session cannot access another's ledger)
- Use ADK's session service for authentication/authorization

### Performance Considerations

- Parse Beancount file only once per operation (cache in memory if needed)
- Append-only writes to avoid full file rewrites
- Consider using Beancount's `beancount.loader.load_file()` with caching for large ledgers
