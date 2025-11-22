# Validation Design Document

This document outlines the design to implement the [Validation](../features/validation.md) feature in TravelCount using the Agent Development Kit (ADK).

## File Structure

In this feature, following files will be created or modified:

- `agents/travelcount/storage/beancount_adapter.py`
- `agents/travelcount/storage/validator.py`
- `tests/test_storage/test_validator.py`
- `tests/test_integration/test_validation_integration.py`

## Entities

This feature does not introduce new domain entities. It operates at the storage layer to ensure data integrity.

For detailed information about existing entities, refer to the [Entities Documentation](../entities.md).

## Flow

The following flow describes how the validation feature operates within TravelCount:

```plaintext
┌─────────────────┐
│  Tool Layer     │
│ (add_partner,   │
│  log_expense)   │
└────────┬────────┘
         │
         v
┌─────────────────────────────┐
│  BeancountAdapter           │
│                             │
│  1. Create directive        │
│  2. _write_directive()      │
│  3. Append to index.bean    │
└────────┬────────────────────┘
         │
         v
┌─────────────────────────────┐
│  Validator                  │
│                             │
│  1. Load ledger file        │
│  2. Parse entries + errors  │
│  3. Run beancount.ops       │
│     .validation.validate()  │
│  4. Collect all errors      │
└────────┬────────────────────┘
         │
         ├─── Errors found ───> Raise ValidationError
         │
         └─── No errors ────> Return success
```

## Dependencies Relationship

In this feature, the components have the following dependencies relationship:

```plaintext
BeancountAdapter --(uses)--> Validator
Validator --(depends on)--> beancount.ops.validation
Validator --(depends on)--> beancount.loader
BeancountAdapter --(raises)--> ValidationError
```

## Components

### Validator Module (`storage/validator.py`)

A dedicated validation module that encapsulates Beancount validation logic. This module is responsible for:

- Loading and parsing Beancount ledger files
- Collecting parse errors from `beancount.loader.load_file()`
- Running validation checks using `beancount.ops.validation.validate()`
- Aggregating and formatting validation errors into user-friendly messages

**Key Functions:**

1. `validate_ledger(ledger_path: Path) -> list[ValidationError]`
   - Loads the ledger file using `beancount.loader.load_file()`
   - Checks for parse errors in the returned errors list
   - Runs `beancount.ops.validation.validate(entries, options_map)`
   - Returns aggregated list of all validation errors

2. `format_error(error) -> str`
   - Formats Beancount error objects into readable error messages
   - Includes file path, line number, and error description
   - Follows the same format as `bean-check` command output

**Exception Class:**

- `ValidationError(Exception)` - Custom exception raised when validation fails
  - Contains formatted error message with all validation issues
  - Raised by BeancountAdapter after failed validation

### BeancountAdapter Integration

The existing `BeancountAdapter` class will be modified to integrate validation:

**Modified Method: `_write_directive()`**

Changes:
1. Read and store current ledger content as backup
2. Append directive to ledger file
3. Call `Validator.validate_ledger(ledger_path)`
4. If validation errors exist:
   - Restore ledger from backup
   - Raise `ValidationError` with formatted error message
5. If validation succeeds, proceed normally

**Integration Points:**

All public write methods automatically benefit from validation through `_write_directive()`:
- `add_partner()`
- `remove_partner()`
- `log_expense()`
- `split_expense()`

**Error Handling Strategy:**

- Backup ledger content before writing
- Validation occurs after the directive is written to disk
- If validation fails, restore ledger from backup and raise `ValidationError`
- Ledger remains in valid state at all times
- Caller catches exception and returns error to user

### Beancount Validation API Usage

Based on research from the [Beancount documentation](https://beancount.github.io/docs/api_reference/beancount.ops.html), the following validation functions are available:

**Core Validation Function:**

```python
from beancount.ops import validation

errors = validation.validate(entries, options_map, log_timings=None, extra_validations=None)
```

**Available Validators:**

1. `validate_active_accounts()` - Ensures accounts referenced in entries have been opened
2. `validate_check_transaction_balances()` - Verifies transaction postings balance correctly
3. `validate_currency_constraints()` - Checks currencies comply with account restrictions
4. `validate_data_types()` - Confirms entries contain proper data types
5. `validate_documents_paths()` - Validates document file paths exist and are accessible
6. `validate_duplicate_balances()` - Detects duplicate balance assertions
7. `validate_duplicate_commodities()` - Identifies duplicate commodity declarations
8. `validate_open_close()` - Ensures proper account open/close sequencing

The `validate()` function runs all standard validation checks and returns a list of `ValidationError` tuples with structure: `(source, message, entry)`.

## Testing

### Valid Beancount file update

**Test file:** `tests/test_integration/test_validation_integration.py`

**Scenario:** Given an updated Beancount file with correct syntax, when the user tries to interact with accounting data, then the agent should proceed without errors.

**Deliverables:**
- Create a temporary ledger with valid directives
- Call `BeancountAdapter.add_partner()` to append new valid directive
- Verify no `ValidationError` is raised
- Verify ledger file contains the new directive

### Invalid Beancount file update

**Test file:** `tests/test_integration/test_validation_integration.py`

**Scenario:** Given an updated Beancount file with incorrect directive, when the user tries to interact with accounting data, then the agent should respond with internal error indicating validation failure.

**Deliverables:**
- Create a ledger with partner account opened and closed
- Attempt to call `BeancountAdapter.add_partner()` with same partner name
- Verify `ValidationError` is raised
- Verify error message contains validation details about account reopening issue

### Unit Tests for Validator

**Test file:** `tests/test_storage/test_validator.py`

**Scenarios:**
1. `test_validate_ledger_success()` - Validate ledger with no errors
2. `test_validate_ledger_parse_errors()` - Detect syntax errors
3. `test_validate_ledger_duplicate_open()` - Detect duplicate open directives
4. `test_validate_ledger_reopen_closed_account()` - Detect reopening closed accounts
5. `test_format_error()` - Verify error formatting matches expected output

**Deliverables:**
- Unit tests for all validator functions
- Test fixtures with various invalid ledger scenarios
- Verify error messages are user-friendly and actionable

### Acceptance Tests

**Test file:** `tests/test_acceptance/test_validation_acceptance.py`

**Scenarios:**
1. End-to-end validation workflow through agent tools
2. Verify error propagation from storage layer to tool layer
3. Confirm user receives clear error messages when validation fails

**Deliverables:**
- Acceptance tests using actual tool functions
- Verify validation prevents invalid data from being persisted
- Ensure error messages guide users to fix issues
