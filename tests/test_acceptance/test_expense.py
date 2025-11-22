"""Acceptance tests for expense tracking scenarios in TravelCount.

These tests verify complete user workflows from the user's perspective, testing
that expense tracking operations work correctly end-to-end with real components
(SessionManager, BeancountAdapter, and expense tools).

Test scenarios based on docs/design/expense.md:
1. Log expense with partner
2. Split expense equally
3. Split expense with custom ratios
4. Get all expenses
5. Get aggregated expenses
6. Get expenses by date range
7. Log expense with negative amount (error handling)
8. Split expense with invalid ratios (error handling)
9. Split expense that doesn't exist (error handling)
"""

import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from beancount import loader

from agents.travelcount.entities.expense import Expense
from agents.travelcount.entities.partner import Partner
from agents.travelcount.storage.beancount_adapter import BeancountAdapter
from agents.travelcount.storage.session_manager import SessionManager
from agents.travelcount.tools.expense import log_expense, split_expense, get_expenses


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data and clean up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_data_dir):
    """Create a SessionManager with temporary directory."""
    manager = SessionManager("test-session-expense")
    manager._base_data_dir = temp_data_dir
    manager.ensure_session_directory()
    manager.initialize_ledger()
    return manager


@pytest.fixture
def beancount_adapter(session_manager):
    """Create a BeancountAdapter with SessionManager."""
    return BeancountAdapter(session_manager)


def _get_transactions_with_metadata(ledger_path: Path, metadata_key: str) -> list:
    """Helper to get all transactions with specific metadata from ledger.

    Args:
        ledger_path: Path to the Beancount ledger file
        metadata_key: Metadata key to filter by (e.g., 'expense-id', 'split-for')

    Returns:
        List of Transaction entries with the specified metadata
    """
    if not ledger_path.exists():
        return []

    entries, errors, options = loader.load_file(str(ledger_path))

    from beancount.core.data import Transaction

    return [
        entry
        for entry in entries
        if isinstance(entry, Transaction) and metadata_key in entry.meta
    ]


def _get_transaction_by_expense_id(ledger_path: Path, expense_id: str):
    """Helper to get a specific transaction by expense ID.

    Args:
        ledger_path: Path to the Beancount ledger file
        expense_id: The expense ID to search for

    Returns:
        Transaction entry if found, None otherwise
    """
    transactions = _get_transactions_with_metadata(ledger_path, "expense-id")
    for txn in transactions:
        if txn.meta.get("expense-id") == expense_id:
            return txn
    return None


def _get_split_transactions_for_expense(ledger_path: Path, expense_id: str) -> list:
    """Helper to get all split transactions for a specific expense.

    Args:
        ledger_path: Path to the Beancount ledger file
        expense_id: The expense ID to search for

    Returns:
        List of Transaction entries with split-for metadata matching expense_id
    """
    transactions = _get_transactions_with_metadata(ledger_path, "split-for")
    return [txn for txn in transactions if txn.meta.get("split-for") == expense_id]


class TestScenarioLogExpenseWithPartner:
    """Scenario: User logs a new expense paid by a specific partner.

    Reference: docs/design/expense.md lines 305-313
    """

    def test_log_expense_with_partner(self, beancount_adapter, session_manager):
        """Test logging an expense through the tool interface.

        Verifies:
        - Expense created with correct Transaction directive
        - Beancount file contains expense with expense-id metadata
        - Tool returns success with expense_id
        """
        # Arrange: Add partner Alice
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Act: Log expense through tool
        result = log_expense(
            amount=50.0,
            currency="USD",
            description="Lunch at cafe",
            paid_by="Alice",
            repository=beancount_adapter,
        )

        # Assert: Tool returns success
        assert result["success"] is True
        assert "expense_id" in result
        assert "Lunch at cafe" in result["message"]
        assert "Alice" in result["message"]

        expense_id = result["expense_id"]
        assert expense_id is not None

        # Assert: Expense exists in repository
        expense = beancount_adapter.get_expense_by_id(expense_id)
        assert expense is not None
        assert expense.amount == Decimal("50.00")
        assert expense.currency == "USD"
        assert expense.description == "Lunch at cafe"
        assert expense.paid_by.name == "Alice"
        assert expense.date == date.today()

        # Assert: Transaction written to ledger with correct metadata
        ledger_path = session_manager.get_ledger_path()
        transaction = _get_transaction_by_expense_id(ledger_path, expense_id)
        assert transaction is not None
        assert transaction.meta["expense-id"] == expense_id
        assert transaction.narration == "Lunch at cafe"
        assert transaction.date == date.today()

        # Assert: Verify postings in transaction
        assert len(transaction.postings) == 2
        expense_posting = next(
            p for p in transaction.postings if "Expenses:" in p.account
        )
        partner_posting = next(p for p in transaction.postings if "Alice" in p.account)
        assert expense_posting.units.number == Decimal("50.00")
        assert expense_posting.units.currency == "USD"
        assert partner_posting.account == "Assets:Travel:Partners:Alice"

        # Assert: Ledger file content verification
        ledger_content = ledger_path.read_text()
        assert "Lunch at cafe" in ledger_content
        assert "expense-id:" in ledger_content


class TestScenarioSplitExpenseEqual:
    """Scenario: User splits an expense equally among partners.

    Reference: docs/design/expense.md lines 315-322
    """

    def test_split_expense_equal(self, beancount_adapter, session_manager):
        """Test splitting an expense equally through the tool interface.

        Verifies:
        - Split transaction references original expense ID (split-for metadata)
        - Amounts balance correctly (Alice -50, Bob +50)
        - Equal split ratios applied correctly
        """
        # Arrange: Add partners
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Log expense paid by Alice
        log_result = log_expense(
            amount=100.0,
            currency="USD",
            description="Hotel room",
            paid_by="Alice",
            repository=beancount_adapter,
        )
        expense_id = log_result["expense_id"]

        # Act: Split expense equally through tool
        split_result = split_expense(
            expense_id=expense_id,
            partners=["Alice", "Bob"],
            ratios=None,  # None means equal split
            repository=beancount_adapter,
        )

        # Assert: Tool returns success
        assert split_result["success"] is True
        assert "2 partners" in split_result["message"]

        # Assert: Split transaction written to ledger
        ledger_path = session_manager.get_ledger_path()
        split_transactions = _get_split_transactions_for_expense(
            ledger_path, expense_id
        )
        assert len(split_transactions) == 1

        split_txn = split_transactions[0]
        assert split_txn.meta["split-for"] == expense_id
        assert "Split:" in split_txn.narration
        assert "Hotel room" in split_txn.narration

        # Assert: Verify split amounts use net settlement calculation
        # Alice paid $100, owes $50 (50%), net = +$50 (receives)
        # Bob paid $0, owes $50 (50%), net = -$50 (owes)
        assert len(split_txn.postings) == 2  # Only net amounts

        alice_posting = next(p for p in split_txn.postings if "Alice" in p.account)
        bob_posting = next(p for p in split_txn.postings if "Bob" in p.account)

        assert alice_posting.units.number == Decimal("50.00")  # Alice receives net
        assert alice_posting.units.currency == "USD"

        assert bob_posting.units.number == Decimal("-50.00")  # Bob owes net
        assert bob_posting.units.currency == "USD"

        # Total should balance to zero
        total = sum(p.units.number for p in split_txn.postings)
        assert total == Decimal("0.00")


class TestScenarioSplitExpenseRatios:
    """Scenario: User splits an expense with custom ratios.

    Reference: docs/design/expense.md lines 324-331
    """

    def test_split_expense_ratios(self, beancount_adapter, session_manager):
        """Test splitting an expense with custom ratios.

        Verifies:
        - Split amounts: Alice 0.5 (45), Bob 0.3 (27), Charlie 0.2 (18)
        - Ratios are respected in split transaction
        - All amounts sum to original expense total
        """
        # Arrange: Add partners
        alice = Partner("Alice")
        bob = Partner("Bob")
        charlie = Partner("Charlie")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)
        beancount_adapter.add_partner(charlie)

        # Log expense paid by Alice
        log_result = log_expense(
            amount=90.0,
            currency="USD",
            description="Taxi ride",
            paid_by="Alice",
            repository=beancount_adapter,
        )
        expense_id = log_result["expense_id"]

        # Act: Split expense with custom ratios
        split_result = split_expense(
            expense_id=expense_id,
            partners=["Alice", "Bob", "Charlie"],
            ratios=[0.5, 0.3, 0.2],
            repository=beancount_adapter,
        )

        # Assert: Tool returns success
        assert split_result["success"] is True
        assert "3 partners" in split_result["message"]

        # Assert: Split transaction written to ledger
        ledger_path = session_manager.get_ledger_path()
        split_transactions = _get_split_transactions_for_expense(
            ledger_path, expense_id
        )
        assert len(split_transactions) == 1

        split_txn = split_transactions[0]
        assert split_txn.meta["split-for"] == expense_id

        # Assert: Verify split amounts respect ratios using net settlement
        # Alice paid $90, owes $45 (50%), net = +$45 (receives)
        # Bob paid $0, owes $27 (30%), net = -$27 (owes)
        # Charlie paid $0, owes $18 (20%), net = -$18 (owes)
        assert len(split_txn.postings) == 3  # Net amounts for each partner

        # Verify each partner's net position
        alice_posting = next(p for p in split_txn.postings if "Alice" in p.account)
        bob_posting = next(p for p in split_txn.postings if "Bob" in p.account)
        charlie_posting = next(p for p in split_txn.postings if "Charlie" in p.account)

        assert alice_posting.units.number == Decimal("45.00")  # Net: 90 - 45
        assert bob_posting.units.number == Decimal("-27.00")  # Net: 0 - 27
        assert charlie_posting.units.number == Decimal("-18.00")  # Net: 0 - 18

        # Assert: All amounts sum to zero (balanced transaction)
        total = sum(p.units.number for p in split_txn.postings)
        assert total == Decimal("0.00")


class TestScenarioGetAllExpenses:
    """Scenario: User retrieves all expenses for the session.

    Reference: docs/design/expense.md lines 333-340
    """

    def test_get_all_expenses(self, beancount_adapter, session_manager):
        """Test retrieving all expenses through the tool interface.

        Verifies:
        - All expenses returned
        - Expense data is complete and correct
        - Multiple expenses with different attributes handled correctly
        """
        # Arrange: Add partner and log multiple expenses
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Create expenses manually with different dates

        expense1 = Expense(
            date=date.today() - timedelta(days=2),
            amount=Decimal("50.00"),
            currency="USD",
            description="Breakfast",
            paid_by=alice,
        )
        expense2 = Expense(
            date=date.today() - timedelta(days=1),
            amount=Decimal("75.50"),
            currency="USD",
            description="Lunch",
            paid_by=alice,
        )
        expense3 = Expense(
            date=date.today(),
            amount=Decimal("120.00"),
            currency="USD",
            description="Dinner",
            paid_by=alice,
        )

        # Log expenses directly through adapter
        beancount_adapter.log_expense(expense1)
        beancount_adapter.log_expense(expense2)
        beancount_adapter.log_expense(expense3)

        # Act: Retrieve all expenses through tool
        result = get_expenses(
            range="all", aggregate=False, repository=beancount_adapter
        )

        # Assert: Tool returns success
        assert result["success"] is True
        assert "expenses" in result

        expenses = result["expenses"]
        assert len(expenses) == 3

        # Assert: Verify expense data is complete (new format: shared_by, description, amount)
        breakfast = next(exp for exp in expenses if exp["description"] == "Breakfast")
        assert breakfast["amount"] == 50.0
        assert breakfast["shared_by"] == "Alice"

        lunch = next(exp for exp in expenses if exp["description"] == "Lunch")
        assert lunch["amount"] == 75.5
        assert lunch["shared_by"] == "Alice"

        dinner = next(exp for exp in expenses if exp["description"] == "Dinner")
        assert dinner["amount"] == 120.0
        assert dinner["shared_by"] == "Alice"


class TestScenarioGetAggregatedExpenses:
    """Scenario: User retrieves aggregated expenses for partners.

    Reference: docs/design/expense.md lines 342-349
    """

    def test_get_aggregated_expenses(self, beancount_adapter, session_manager):
        """Test retrieving aggregated expenses.

        Verifies:
        - Net amounts calculated correctly per partner
        - Aggregation combines original expenses paid by each partner
        - Split amounts affect net balances (simplified aggregation)

        Note: Current implementation does simple aggregation by who paid.
        Full implementation would track splits and calculate net balances.
        """
        # Arrange: Add partners
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Log expense paid by Alice
        log_result1 = log_expense(
            amount=100.0,
            currency="USD",
            description="Hotel",
            paid_by="Alice",
            repository=beancount_adapter,
        )
        expense_id1 = log_result1["expense_id"]

        # Log expense paid by Bob
        log_expense(
            amount=60.0,
            currency="USD",
            description="Groceries",
            paid_by="Bob",
            repository=beancount_adapter,
        )

        # Split first expense equally between Alice and Bob
        split_expense(
            expense_id=expense_id1,
            partners=["Alice", "Bob"],
            repository=beancount_adapter,
        )

        # Act: Retrieve aggregated expenses
        result = get_expenses(range="all", aggregate=True, repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True
        assert "expenses" in result

        aggregated = result["expenses"]
        assert len(aggregated) >= 2  # At least Alice and Bob

        # Assert: Verify aggregated amounts (new format: total_expense shows actual share)
        alice_agg = next(exp for exp in aggregated if exp["partner"] == "Alice")
        bob_agg = next(exp for exp in aggregated if exp["partner"] == "Bob")

        # After splitting expense1 (100.00) equally, Alice's share is 50.00, Bob's is 50.00
        # Alice paid 100.00 total, her share is 50.00, so total_expense = 50.00
        # Bob paid 60.00, no splits on that, so his share is 60.00
        assert alice_agg["total_expense"] == 50.0  # Alice's share after split
        assert alice_agg["currency"] == "USD"

        assert bob_agg["total_expense"] == 110.0  # Bob's 60.00 + his 50.00 share
        assert bob_agg["currency"] == "USD"


class TestScenarioGetExpensesDateRange:
    """Scenario: User retrieves expenses within a specific date range.

    Reference: docs/design/expense.md lines 351-358
    """

    def test_get_expenses_date_range(self, beancount_adapter, session_manager):
        """Test retrieving expenses filtered by date range.

        Verifies:
        - Only expenses within date range returned
        - Boundary conditions (inclusive dates)
        - Date range parsing works correctly
        """
        # Arrange: Add partner and log expenses on different dates
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Create expenses with specific dates
        expense1 = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("30.00"),
            currency="USD",
            description="June 1 expense",
            paid_by=alice,
        )
        expense2 = Expense(
            date=date(2024, 6, 5),
            amount=Decimal("50.00"),
            currency="USD",
            description="June 5 expense",
            paid_by=alice,
        )
        expense3 = Expense(
            date=date(2024, 6, 10),
            amount=Decimal("70.00"),
            currency="USD",
            description="June 10 expense",
            paid_by=alice,
        )

        beancount_adapter.log_expense(expense1)
        beancount_adapter.log_expense(expense2)
        beancount_adapter.log_expense(expense3)

        # Act: Retrieve expenses for range "2024-06-02 to 2024-06-08"
        result = get_expenses(
            range="2024-06-02 to 2024-06-08",
            aggregate=False,
            repository=beancount_adapter,
        )

        # Assert: Tool returns success
        assert result["success"] is True
        assert "expenses" in result

        expenses = result["expenses"]

        # Assert: Only June 5 expense in range (new format)
        assert len(expenses) == 1
        assert expenses[0]["description"] == "June 5 expense"
        assert expenses[0]["shared_by"] == "Alice"
        assert expenses[0]["amount"] == 50.0

    def test_get_expenses_date_range_inclusive(
        self, beancount_adapter, session_manager
    ):
        """Test that date range boundaries are inclusive.

        Verifies:
        - Expenses on start date are included
        - Expenses on end date are included
        """
        # Arrange: Add partner and log expenses
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        expense1 = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("10.00"),
            currency="USD",
            description="Start date",
            paid_by=alice,
        )
        expense2 = Expense(
            date=date(2024, 6, 5),
            amount=Decimal("20.00"),
            currency="USD",
            description="End date",
            paid_by=alice,
        )

        beancount_adapter.log_expense(expense1)
        beancount_adapter.log_expense(expense2)

        # Act: Query range matching exact dates
        result = get_expenses(
            range="2024-06-01 to 2024-06-05",
            aggregate=False,
            repository=beancount_adapter,
        )

        # Assert: Both expenses included (new format checks descriptions instead of IDs)
        assert result["success"] is True
        expenses = result["expenses"]
        assert len(expenses) == 2

        descriptions = {exp["description"] for exp in expenses}
        assert "Start date" in descriptions
        assert "End date" in descriptions


class TestScenarioLogExpenseNegativeAmount:
    """Scenario: User attempts to log expense with negative amount (error handling).

    Reference: docs/design/expense.md lines 360-372
    """

    def test_log_expense_negative_amount(self, beancount_adapter, session_manager):
        """Test logging expense with negative amount returns error.

        Verifies:
        - ValueError raised or error response returned
        - Tool returns error response
        - No expense created in ledger
        """
        # Arrange: Add partner
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        ledger_path = session_manager.get_ledger_path()
        initial_content = ledger_path.read_text()

        # Act: Attempt to log expense with negative amount
        result = log_expense(
            amount=-50.0,
            currency="USD",
            description="Invalid negative expense",
            paid_by="Alice",
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "error" in result
        assert "positive" in result["error"].lower()

        # Assert: Ledger unchanged
        final_content = ledger_path.read_text()
        assert initial_content == final_content

        # Assert: No expense transactions added
        expense_transactions = _get_transactions_with_metadata(
            ledger_path, "expense-id"
        )
        assert len(expense_transactions) == 0

    def test_log_expense_zero_amount(self, beancount_adapter, session_manager):
        """Test logging expense with zero amount returns error.

        Verifies:
        - Zero amount also rejected
        - Consistent error handling
        """
        # Arrange: Add partner
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Act: Attempt to log expense with zero amount
        result = log_expense(
            amount=0.0,
            currency="USD",
            description="Zero amount expense",
            paid_by="Alice",
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "error" in result
        assert "positive" in result["error"].lower()


class TestScenarioSplitExpenseInvalidRatios:
    """Scenario: User attempts to split expense with invalid ratios (error handling).

    Reference: docs/design/expense.md lines 360-372
    """

    def test_split_expense_invalid_ratios(self, beancount_adapter, session_manager):
        """Test splitting expense with ratios that don't sum to 1.0.

        Verifies:
        - Error response returned
        - No split transaction created
        - Data integrity maintained
        """
        # Arrange: Add partners and log expense
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        log_result = log_expense(
            amount=100.0,
            currency="USD",
            description="Test expense",
            paid_by="Alice",
            repository=beancount_adapter,
        )
        expense_id = log_result["expense_id"]

        # Get ledger path for verification
        ledger_path = session_manager.get_ledger_path()

        # Act: Attempt to split with invalid ratios (sum to 0.9, not 1.0)
        result = split_expense(
            expense_id=expense_id,
            partners=["Alice", "Bob"],
            ratios=[0.6, 0.3],  # Sum is 0.9, not 1.0
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "error" in result
        assert "1.0" in result["error"] or "100%" in result["error"]

        # Assert: No split transaction created
        split_transactions = _get_split_transactions_for_expense(
            ledger_path, expense_id
        )
        assert len(split_transactions) == 0

    def test_split_expense_ratios_length_mismatch(self, beancount_adapter):
        """Test splitting expense with ratios length not matching partners length.

        Verifies:
        - Error response for length mismatch
        - Clear error message
        """
        # Arrange: Add partners and log expense
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        log_result = log_expense(
            amount=100.0,
            currency="USD",
            description="Test expense",
            paid_by="Alice",
            repository=beancount_adapter,
        )
        expense_id = log_result["expense_id"]

        # Act: Attempt to split with mismatched ratios
        result = split_expense(
            expense_id=expense_id,
            partners=["Alice", "Bob"],
            ratios=[1.0],  # Only 1 ratio for 2 partners
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "error" in result
        assert "length" in result["error"].lower() or "match" in result["error"].lower()


class TestScenarioSplitExpenseNonexistent:
    """Scenario: User attempts to split non-existent expense (error handling).

    Reference: docs/design/expense.md lines 360-372
    """

    def test_split_expense_nonexistent(self, beancount_adapter, session_manager):
        """Test splitting a non-existent expense returns error.

        Verifies:
        - Error response returned
        - No transaction created
        - Graceful error handling
        """
        # Arrange: Add partners (but no expense)
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        ledger_path = session_manager.get_ledger_path()
        initial_content = ledger_path.read_text()

        # Act: Attempt to split non-existent expense
        result = split_expense(
            expense_id="nonexistent123",
            partners=["Alice", "Bob"],
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

        # Assert: Ledger unchanged
        final_content = ledger_path.read_text()
        assert initial_content == final_content

        # Assert: No split transactions created
        split_transactions = _get_transactions_with_metadata(ledger_path, "split-for")
        assert len(split_transactions) == 0
