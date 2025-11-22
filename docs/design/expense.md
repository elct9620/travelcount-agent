# Expense Tracking Design Document

This document outlines the design to implement the [Expense Tracking](../features/expense.md) feature in TravelCount using the Agent Development Kit (ADK).

## File Structure

In this feature, following files will be created or modified:

- `agents/travelcount/entities/expense.py` - Expense domain entity (existing)
- `agents/travelcount/tools/expense.py` - Expense tool functions and ExpenseRepository protocol (modify to improve aggregation logic)
- `agents/travelcount/storage/beancount_adapter.py` - Extended to implement ExpenseRepository (existing)
- `agents/travelcount/agent.py` - Register expense tool with session-aware wrapper (existing)
- `tests/test_entities/test_expense.py` - Unit tests for Expense entity (existing)
- `tests/test_tools/test_expense.py` - Unit tests for expense tools (add tests for improved aggregation)
- `tests/test_storage/test_beancount_adapter_expense.py` - Unit tests for expense storage (existing)
- `tests/test_acceptance/test_expense.py` - Acceptance tests from feature scenarios (existing)

## Entities

In this feature, the related entities are following:

- **Expense**: Represents a travel expense with amount, currency, description, date, and payer information
- **Partner**: Existing entity representing travel partners who participate in shared expenses

For detailed information about these entities, refer to the [Entities Documentation](../entities.md).

## Flow

The following flow describes how the expense tracking feature operates within TravelCount:

```plaintext
User Input (via ADK Agent)
    |
    v
Expense Tool (log_expense/split_expense/get_expenses)
    |
    v
ExpenseRepository Protocol
    |
    v
BeancountAdapter (implements ExpenseRepository)
    |
    v
SessionManager (provides session-specific ledger path)
    |
    v
Beancount Ledger File (data/[session_id]/index.bean)
    - Transaction directives for expenses
    - Posting entries for splits
```

## Dependencies Relationship

In this feature, the components have the following dependencies relationship:

```plaintext
expense_tool --(defines)--> ExpenseRepository (Protocol)
BeancountAdapter --(implements)--> ExpenseRepository
BeancountAdapter --(depends)--> SessionManager
expense_tool --(uses)--> Expense (Entity)
expense_tool --(uses)--> Partner (Entity)
agent.py --(registers)--> expense_tool (with session injection)
```

## Components

### Expense Entity

The Expense entity represents a single travel expense entry with the following attributes:

- `id`: Unique identifier for the expense (generated from hash of expense details)
- `date`: Date of the expense (datetime.date)
- `amount`: Decimal amount of the expense
- `currency`: Currency code (e.g., "USD")
- `description`: Brief description of the expense
- `paid_by`: Partner who paid for the expense

**Domain logic methods:**
- `validate_amount(amount)`: Ensures amount is positive
- `validate_currency(currency)`: Ensures currency code is valid (3-letter uppercase)
- `generate_id()`: Generates consistent ID from expense attributes

### ExpenseRepository Protocol

Defined by the expense tool (consumer-driven contract):

```python
class ExpenseRepository(Protocol):
    def log_expense(
        self,
        expense: Expense,
        default_partner: Partner | None = None
    ) -> str:
        """Log an expense. Returns expense ID."""
        ...

    def split_expense(
        self,
        expense_id: str,
        partners: list[Partner],
        ratios: list[float] | None = None
    ) -> None:
        """Split expense among partners with optional ratios."""
        ...

    def get_expenses(
        self,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None
    ) -> list[Expense]:
        """Retrieve expenses within optional date range."""
        ...

    def get_expense_by_id(self, expense_id: str) -> Expense | None:
        """Retrieve a specific expense by ID."""
        ...
```

### Expense Tool Functions

Three tool functions exposed to the ADK agent:

#### log_expense

```python
def log_expense(
    amount: float,
    currency: str,
    description: str,
    paid_by: str = None,
    repository: ExpenseRepository = None
) -> dict:
    """Log a travel expense."""
```

**Logic:**
1. Validate amount is positive
2. Validate currency format
3. If paid_by is None, get first partner from repository
4. Create Expense entity with current date
5. Call repository.log_expense()
6. Return success message with expense ID

**Error handling:**
- ValueError: Invalid amount (negative/zero)
- ValueError: Invalid currency format
- ValueError: Partner not found
- ValueError: No partners in session

#### split_expense

```python
def split_expense(
    expense_id: str,
    partners: list[str],
    ratios: list[float] = None,
    repository: ExpenseRepository = None
) -> dict:
    """Split an expense among travel partners."""
```

**Logic:**
1. Validate expense_id exists via repository.get_expense_by_id()
2. Validate all partner names exist
3. If ratios provided, validate they sum to 1.0 (100%)
4. Convert partner names to Partner entities
5. Call repository.split_expense()
6. Return success message

**Error handling:**
- ValueError: Expense not found
- ValueError: Partner not found
- ValueError: Invalid ratios (don't sum to 100%)
- ValueError: Ratios length doesn't match partners length

#### get_expenses

```python
def get_expenses(
    range: str = "all",
    aggregate: bool = True,
    repository: ExpenseRepository = None
) -> list[dict]:
    """Retrieve logged expenses for the current session."""
```

**Logic:**
1. Parse range parameter to date_from/date_to
2. Call repository.get_expenses(date_from, date_to)
3. Load split transaction data from Beancount ledger (transactions with "split-for" metadata)
4. Calculate each partner's share based on splits
5. If aggregate=True:
   - Group by partner
   - Calculate total_expense for each partner (sum of their shares)
   - Return: `[{"partner": "Alice", "total_expense": 85.00, "currency": "USD"}, ...]`
6. If aggregate=False:
   - For each expense, create entries for each partner showing their share
   - Return: `[{"description": "Hotel Stay", "shared_by": "Alice", "amount": 50.00}, ...]`
7. Return expense list

**Range parsing:**
- "all": No date filter
- "YYYY-MM-DD": Single date
- "YYYY-MM-DD to YYYY-MM-DD": Date range

**Return format per feature spec:**
- When `aggregate=True`: `[{"partner": "Alice", "total_expense": 85.00, "currency": "USD"}, ...]`
- When `aggregate=False`: `[{"description": "Hotel Stay", "shared_by": "Alice", "amount": 50.00}, ...]`

### BeancountAdapter Extension

Extend the existing BeancountAdapter class to implement ExpenseRepository:

#### log_expense implementation

**Beancount format:**
```beancount
2024-06-01 * "Lunch at Cafe"
  expense-id: "abc123"
  Expenses:Travel:Food          50.00 USD
  Assets:Travel:Partners:Alice
```

**Logic:**
1. Create Transaction directive with expense date and description
2. Add metadata: expense-id
3. Create two postings:
   - Debit: `Expenses:Travel:[Category]` with amount
   - Credit: `Assets:Travel:Partners:[PaidBy]` (balancing, no amount)
4. Append transaction to ledger using `_write_directive()`
5. Return expense ID

**Category inference:**
- Parse description for keywords (Food, Transport, Hotel, etc.)
- Default to `Expenses:Travel:Misc`

#### split_expense implementation

**Beancount format (equal split between Alice and Bob, where Alice paid $50):**
```beancount
2024-06-01 * "Split: Lunch at Cafe"
  split-for: "abc123"
  Assets:Travel:Partners:Alice    25.00 USD
  Assets:Travel:Partners:Bob     -25.00 USD
```

**Logic:**
1. Retrieve original expense via get_expense_by_id()
2. Convert ratios to Decimal if provided (default equal split using Decimal arithmetic per [feature requirements](../features/expense.md#data-model))
3. Calculate split amounts with ROUND_UP strategy per [feature requirements](../features/expense.md#data-model):
   - All amounts rounded to 2 decimal places maximum for simplicity
   - Calculate each non-payer's share and quantize using ROUND_UP
   - Calculate payer's net amount by difference to absorb any remainder
4. For each partner, calculate their net position:
   - If partner is not the payer: amount owed BY them = their share rounded up (negative)
   - If partner is the payer: amount owed TO them = total - sum(other shares rounded up)
5. Create Transaction directive with same date as original
6. Add metadata: split-for (references expense ID)
7. Create postings only for non-zero net amounts:
   - Partners who owe money: debit (negative amount)
   - Payer receives: credit (positive amount for what others owe)
8. Append transaction to ledger

**Example calculations:**

Equal split with rounding:
- Alice paid 10.00 USD, split equally among Alice, Bob, Charlie (3 people)
  - Bob's share: 10.00 / 3 = 3.333... → rounds up to 3.34 USD
  - Charlie's share: 10.00 / 3 = 3.333... → rounds up to 3.34 USD
  - Alice's share (payer): 10.00 - 3.34 - 3.34 = 3.32 USD (gets remainder)
  - Alice net: 10.00 - 3.32 = 6.68 USD (receives from others)
  - Bob net: -3.34 USD (owes)
  - Charlie net: -3.34 USD (owes)
  - Result: `Alice +6.68 USD, Bob -3.34 USD, Charlie -3.34 USD`
  - Balance check: 6.68 + (-3.34) + (-3.34) = 0 ✓

Ratio split:
- Alice paid $100, split 70-30 between Alice and Bob
  - Alice's share: $70, Bob's share: $30
  - Alice net: 100 - 70 = $30 (receives from Bob)
  - Bob net: -$30 (owes Alice)
  - Result: `Alice +30 USD, Bob -30 USD`

**Important:** The split transaction only records the settlement/transfer amounts, not the full expense redistribution. This avoids double-posting to the payer's account.

#### get_expenses implementation

**Logic:**
1. Load ledger entries via `_load_entries()`
2. Filter Transaction directives with "expense-id" metadata
3. Apply date range filter if provided
4. Parse each transaction to construct Expense entities
5. Return list of Expense objects

**Note:** Split information is stored separately in Beancount transactions with "split-for" metadata. The tool layer (`_handle_get_expenses`) will need to load both expenses and splits from the ledger to calculate each partner's actual expense amounts.

#### get_expense_by_id implementation

**Logic:**
1. Load ledger entries
2. Find Transaction with matching "expense-id" metadata
3. Parse transaction to Expense entity
4. Return Expense or None

### Agent Registration

In `agents/travelcount/agent.py`, add wrapper function:

```python
def expense(
    operation: str,
    amount: float = None,
    currency: str = None,
    description: str = None,
    paid_by: str = None,
    expense_id: str = None,
    partners: list[str] = None,
    ratios: list[float] = None,
    range: str = "all",
    aggregate: bool = True,
    tool_context: ToolContext = None
) -> dict:
    """Expense management tool wrapper with session injection."""
    session_id = tool_context.session.id
    session_manager = SessionManager(session_id)
    adapter = BeancountAdapter(session_manager)

    if operation == "log":
        return log_expense(amount, currency, description, paid_by, adapter)
    elif operation == "split":
        return split_expense(expense_id, partners, ratios, adapter)
    elif operation == "get":
        return get_expenses(range, aggregate, adapter)
```

Register with root_agent:
```python
root_agent = Agent(
    model="gemini-2.5-flash",
    tools=[partners, expense]
)
```

## Testing

### Scenario: Log a new expense paid by a specific partner

**Test file:** `tests/test_acceptance/test_expense.py::test_log_expense_with_partner`

**Coverage:**
- Expense entity creation with valid data
- BeancountAdapter.log_expense() creates correct Transaction directive
- Beancount file contains expense with proper metadata
- Tool returns success message

### Scenario: Split an expense equally among partners

**Test file:** `tests/test_acceptance/test_expense.py::test_split_expense_equal`

**Coverage:**
- Expense splitting with equal ratios (default)
- BeancountAdapter.split_expense() creates correct postings
- Split transaction references original expense ID
- Amounts balance correctly (sum to zero)

### Scenario: Split an expense with specified ratios

**Test file:** `tests/test_acceptance/test_expense.py::test_split_expense_ratios`

**Coverage:**
- Custom ratio validation (sum to 100%)
- Split calculation accuracy
- Posting amounts reflect specified ratios

### Scenario: Retrieve all expenses for the session

**Test file:** `tests/test_acceptance/test_expense.py::test_get_all_expenses`

**Coverage:**
- BeancountAdapter.get_expenses() parses all expense transactions
- Non-aggregated view shows individual expenses with split details per partner
- Each expense displays who paid and each partner's actual share
- Correctly filters out non-expense transactions

**Expected behavior per feature spec (lines 109-122, 153-165):**
When retrieving expenses without aggregation (`aggregate=False`), return individual expense items showing each partner's share:
```json
[
  {"description": "Hotel Stay", "shared_by": "Alice", "amount": 50.00},
  {"description": "Hotel Stay", "shared_by": "Bob", "amount": 50.00},
  {"description": "Lunch at Cafe", "shared_by": "Alice", "amount": 35.00},
  {"description": "Lunch at Cafe", "shared_by": "Bob", "amount": 15.00}
]
```

### Scenario: Retrieve aggregated expenses for a partner

**Test file:** `tests/test_acceptance/test_expense.py::test_get_aggregated_expenses`

**Coverage:**
- Aggregation logic calculates net amounts per partner
- Combines original expenses (what they paid) and split amounts (what they owe)
- Returns partner summary with total_paid, total_expense, and net_settlement
- Net settlement = total_paid - total_expense (positive means owed TO them, negative means they owe)

**Expected behavior per feature spec (lines 124-134):**
When retrieving expenses with aggregation (`aggregate=True`), return partner totals:
```json
[
  {"partner": "Alice", "total_expense": 85.00, "currency": "USD"},
  {"partner": "Bob", "total_expense": 65.00, "currency": "USD"}
]
```
The `total_expense` field shows each partner's total share across all expenses after splits.

### Scenario: Retrieve expenses within a specific date range

**Test file:** `tests/test_acceptance/test_expense.py::test_get_expenses_date_range`

**Coverage:**
- Date range parsing from string format
- Filtering logic correctly includes/excludes expenses
- Boundary conditions (inclusive dates)

### Scenario: Error handling for invalid inputs

**Test files:**
- `tests/test_tools/test_expense.py::test_log_expense_negative_amount`
- `tests/test_tools/test_expense.py::test_split_expense_invalid_ratios`
- `tests/test_tools/test_expense.py::test_split_expense_nonexistent`

**Coverage:**
- Negative/zero amount validation
- Invalid ratio validation (doesn't sum to 100%)
- Non-existent expense ID handling
- Non-existent partner handling
