"""Tests for expense management tool.

This module tests the expense tool's ability to handle LLM interactions,
validate inputs, delegate to repository implementations, and format responses
for the ADK agent system.
"""

import datetime
from decimal import Decimal
from unittest.mock import Mock

from agents.travelcount.entities.expense import Expense
from agents.travelcount.entities.partner import Partner
from agents.travelcount.tools.expense import get_expenses, log_expense, split_expense


class TestLogExpenseValidation:
    """Test input validation for the log_expense tool."""

    def test_log_expense_missing_repository(self) -> None:
        """Test that missing repository returns error."""
        result = log_expense(50.0, "USD", "Lunch", repository=None)

        assert result["success"] is False
        assert "Repository not provided" in result["error"]

    def test_log_expense_negative_amount(self, mock_expense_repository: Mock) -> None:
        """Test that negative amount returns error."""
        result = log_expense(
            -10.0, "USD", "Invalid", repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Amount must be positive" in result["error"]

    def test_log_expense_zero_amount(self, mock_expense_repository: Mock) -> None:
        """Test that zero amount returns error."""
        result = log_expense(0.0, "USD", "Invalid", repository=mock_expense_repository)

        assert result["success"] is False
        assert "Amount must be positive" in result["error"]

    def test_log_expense_invalid_currency_lowercase(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that lowercase currency code returns error."""
        result = log_expense(50.0, "usd", "Lunch", repository=mock_expense_repository)

        assert result["success"] is False
        assert "Currency must be 3 uppercase letters" in result["error"]

    def test_log_expense_invalid_currency_too_short(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that currency code with wrong length returns error."""
        result = log_expense(50.0, "US", "Lunch", repository=mock_expense_repository)

        assert result["success"] is False
        assert "Currency must be 3 uppercase letters" in result["error"]

    def test_log_expense_invalid_currency_too_long(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that currency code with wrong length returns error."""
        result = log_expense(50.0, "USDD", "Lunch", repository=mock_expense_repository)

        assert result["success"] is False
        assert "Currency must be 3 uppercase letters" in result["error"]

    def test_log_expense_invalid_currency_with_numbers(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that currency code with numbers returns error."""
        result = log_expense(50.0, "US1", "Lunch", repository=mock_expense_repository)

        assert result["success"] is False
        assert "Currency must be 3 uppercase letters" in result["error"]

    def test_log_expense_no_partners_in_session(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that logging expense without partners returns error."""
        mock_expense_repository.list_partners.return_value = []

        result = log_expense(
            50.0, "USD", "Lunch", paid_by=None, repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "No partners in session" in result["error"]

    def test_log_expense_partner_not_found(self, mock_expense_repository: Mock) -> None:
        """Test that non-existent partner returns error."""
        mock_expense_repository.list_partners.return_value = [Partner("Alice")]

        result = log_expense(
            50.0, "USD", "Lunch", paid_by="Bob", repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Partner 'Bob' not found" in result["error"]


class TestLogExpenseSuccess:
    """Test successful log_expense operations."""

    def test_log_expense_with_explicit_payer(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test successful expense logging with explicit payer."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_abc123"

        result = log_expense(
            50.0, "USD", "Lunch", paid_by="Alice", repository=mock_expense_repository
        )

        assert result["success"] is True
        assert "Expense logged" in result["message"]
        assert "50.0 USD" in result["message"]
        assert "Lunch" in result["message"]
        assert "Alice" in result["message"]
        assert result["expense_id"] == "exp_abc123"

        # Verify log_expense was called
        mock_expense_repository.log_expense.assert_called_once()

    def test_log_expense_with_default_payer(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test successful expense logging with default payer."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        mock_expense_repository.list_partners.return_value = [alice, bob]
        mock_expense_repository.log_expense.return_value = "exp_abc123"

        result = log_expense(
            50.0, "USD", "Lunch", paid_by=None, repository=mock_expense_repository
        )

        assert result["success"] is True
        assert "Alice" in result["message"]  # First partner is default
        assert result["expense_id"] == "exp_abc123"

    def test_log_expense_uses_today_date(self, mock_expense_repository: Mock) -> None:
        """Test that expense is logged with today's date."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_abc123"

        result = log_expense(
            50.0, "USD", "Lunch", paid_by="Alice", repository=mock_expense_repository
        )

        assert result["success"] is True

        # Verify the expense entity passed to repository
        call_args = mock_expense_repository.log_expense.call_args
        expense_arg = call_args[0][0]
        assert isinstance(expense_arg, Expense)
        assert expense_arg.date == datetime.date.today()

    def test_log_expense_with_various_currencies(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test expense logging with different valid currencies."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_abc123"

        currencies = ["USD", "EUR", "JPY", "GBP", "CNY"]
        for currency in currencies:
            result = log_expense(
                50.0,
                currency,
                "Test",
                paid_by="Alice",
                repository=mock_expense_repository,
            )
            assert result["success"] is True
            assert currency in result["message"]

    def test_log_expense_with_decimal_amount(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test expense logging with decimal amounts."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_abc123"

        result = log_expense(
            12.99, "USD", "Coffee", paid_by="Alice", repository=mock_expense_repository
        )

        assert result["success"] is True
        assert "12.99" in result["message"]


class TestSplitExpenseValidation:
    """Test input validation for the split_expense tool."""

    def test_split_expense_missing_repository(self) -> None:
        """Test that missing repository returns error."""
        result = split_expense("exp_123", ["Alice", "Bob"], repository=None)

        assert result["success"] is False
        assert "Repository not provided" in result["error"]

    def test_split_expense_not_found(self, mock_expense_repository: Mock) -> None:
        """Test that non-existent expense returns error."""
        mock_expense_repository.get_expense_by_id.return_value = None

        result = split_expense(
            "exp_invalid", ["Alice"], repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Expense 'exp_invalid' not found" in result["error"]

    def test_split_expense_empty_partners_list(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that empty partners list returns error."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense

        result = split_expense("exp_123", [], repository=mock_expense_repository)

        assert result["success"] is False
        assert "Partner list cannot be empty" in result["error"]

    def test_split_expense_partner_not_found(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that non-existent partner in split returns error."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [Partner("Alice")]

        result = split_expense(
            "exp_123", ["Alice", "Bob"], repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Partner 'Bob' not found" in result["error"]

    def test_split_expense_ratios_length_mismatch(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that mismatched ratios and partners lengths returns error."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
        ]

        result = split_expense(
            "exp_123",
            ["Alice", "Bob"],
            ratios=[1.0],
            repository=mock_expense_repository,
        )

        assert result["success"] is False
        assert "Ratios length (1) must match partners length (2)" in result["error"]

    def test_split_expense_ratios_dont_sum_to_one(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that ratios not summing to 1.0 returns error."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
        ]

        result = split_expense(
            "exp_123",
            ["Alice", "Bob"],
            ratios=[0.6, 0.3],
            repository=mock_expense_repository,
        )

        assert result["success"] is False
        assert "Ratios must sum to 1.0 (100%)" in result["error"]


class TestSplitExpenseSuccess:
    """Test successful split_expense operations."""

    def test_split_expense_equal_split(self, mock_expense_repository: Mock) -> None:
        """Test successful expense split without ratios (equal split)."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
        ]

        result = split_expense(
            "exp_123", ["Alice", "Bob"], repository=mock_expense_repository
        )

        assert result["success"] is True
        assert "Expense split among 2 partners" in result["message"]

        # Verify split_expense was called with correct parameters
        mock_expense_repository.split_expense.assert_called_once()
        call_args = mock_expense_repository.split_expense.call_args
        assert call_args[0][0] == "exp_123"
        assert len(call_args[0][1]) == 2
        assert call_args[0][2] is None  # No ratios provided

    def test_split_expense_with_ratios(self, mock_expense_repository: Mock) -> None:
        """Test successful expense split with custom ratios."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("100.0"),
            currency="USD",
            description="Dinner",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
        ]

        result = split_expense(
            "exp_123",
            ["Alice", "Bob"],
            ratios=[0.6, 0.4],
            repository=mock_expense_repository,
        )

        assert result["success"] is True
        assert "Expense split among 2 partners" in result["message"]

        # Verify split_expense was called with ratios
        call_args = mock_expense_repository.split_expense.call_args
        assert call_args[0][2] == [0.6, 0.4]

    def test_split_expense_with_three_partners(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test expense split among three partners."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("90.0"),
            currency="USD",
            description="Trip",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
            Partner("Charlie"),
        ]

        result = split_expense(
            "exp_123",
            ["Alice", "Bob", "Charlie"],
            repository=mock_expense_repository,
        )

        assert result["success"] is True
        assert "Expense split among 3 partners" in result["message"]

    def test_split_expense_ratios_with_tolerance(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that ratios within tolerance are accepted."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("100.0"),
            currency="USD",
            description="Dinner",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
            Partner("Charlie"),
        ]

        # Ratios that sum to 1.00005 (within 0.0001 tolerance)
        result = split_expense(
            "exp_123",
            ["Alice", "Bob", "Charlie"],
            ratios=[0.33334, 0.33333, 0.33333],
            repository=mock_expense_repository,
        )

        assert result["success"] is True


class TestGetExpensesValidation:
    """Test input validation for the get_expenses tool."""

    def test_get_expenses_missing_repository(self) -> None:
        """Test that missing repository returns error."""
        result = get_expenses("all", repository=None)

        assert result["success"] is False
        assert "Repository not provided" in result["error"]

    def test_get_expenses_invalid_date_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that invalid date format returns error."""
        result = get_expenses("2025/01/15", repository=mock_expense_repository)

        assert result["success"] is False
        assert "error" in result

    def test_get_expenses_invalid_date_range_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that invalid date range format returns error."""
        result = get_expenses(
            "2025-01-15 - 2025-01-20", repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Invalid isoformat string" in result["error"]

    def test_get_expenses_start_after_end_date(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that start date after end date returns error."""
        result = get_expenses(
            "2025-01-20 to 2025-01-15", repository=mock_expense_repository
        )

        assert result["success"] is False
        assert "Start date must be before or equal to end date" in result["error"]


class TestGetExpensesSuccess:
    """Test successful get_expenses operations."""

    def test_get_expenses_all_range(self, mock_expense_repository: Mock) -> None:
        """Test retrieving all expenses."""
        expenses = [
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.0"),
                currency="USD",
                description="Lunch",
                paid_by=Partner("Alice"),
            ),
            Expense(
                date=datetime.date(2025, 1, 16),
                amount=Decimal("30.0"),
                currency="USD",
                description="Coffee",
                paid_by=Partner("Bob"),
            ),
        ]
        mock_expense_repository.get_expenses.return_value = expenses

        result = get_expenses(
            "all", aggregate=False, repository=mock_expense_repository
        )

        assert result["success"] is True
        assert len(result["expenses"]) == 2
        assert result["expenses"][0]["description"] == "Lunch"
        assert result["expenses"][1]["description"] == "Coffee"

        # Verify repository was called with no date limits
        mock_expense_repository.get_expenses.assert_called_once_with(None, None)

    def test_get_expenses_single_date(self, mock_expense_repository: Mock) -> None:
        """Test retrieving expenses for a single date."""
        expenses = [
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.0"),
                currency="USD",
                description="Lunch",
                paid_by=Partner("Alice"),
            ),
        ]
        mock_expense_repository.get_expenses.return_value = expenses

        result = get_expenses(
            "2025-01-15", aggregate=False, repository=mock_expense_repository
        )

        assert result["success"] is True
        assert len(result["expenses"]) == 1

        # Verify repository was called with same date for from/to
        mock_expense_repository.get_expenses.assert_called_once_with(
            datetime.date(2025, 1, 15), datetime.date(2025, 1, 15)
        )

    def test_get_expenses_date_range(self, mock_expense_repository: Mock) -> None:
        """Test retrieving expenses for a date range."""
        expenses = [
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.0"),
                currency="USD",
                description="Lunch",
                paid_by=Partner("Alice"),
            ),
            Expense(
                date=datetime.date(2025, 1, 20),
                amount=Decimal("30.0"),
                currency="USD",
                description="Coffee",
                paid_by=Partner("Bob"),
            ),
        ]
        mock_expense_repository.get_expenses.return_value = expenses

        result = get_expenses(
            "2025-01-15 to 2025-01-20",
            aggregate=False,
            repository=mock_expense_repository,
        )

        assert result["success"] is True
        assert len(result["expenses"]) == 2

        # Verify repository was called with correct date range
        mock_expense_repository.get_expenses.assert_called_once_with(
            datetime.date(2025, 1, 15), datetime.date(2025, 1, 20)
        )

    def test_get_expenses_aggregate_mode(self, mock_expense_repository: Mock) -> None:
        """Test retrieving expenses with aggregation."""
        expenses = [
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.0"),
                currency="USD",
                description="Lunch",
                paid_by=Partner("Alice"),
            ),
            Expense(
                date=datetime.date(2025, 1, 16),
                amount=Decimal("30.0"),
                currency="USD",
                description="Coffee",
                paid_by=Partner("Alice"),
            ),
            Expense(
                date=datetime.date(2025, 1, 17),
                amount=Decimal("20.0"),
                currency="USD",
                description="Snack",
                paid_by=Partner("Bob"),
            ),
        ]
        mock_expense_repository.get_expenses.return_value = expenses

        result = get_expenses("all", aggregate=True, repository=mock_expense_repository)

        assert result["success"] is True
        assert len(result["expenses"]) == 2  # Two partners

        # Find Alice's and Bob's aggregated totals
        alice_total = next(e for e in result["expenses"] if e["partner"] == "Alice")
        bob_total = next(e for e in result["expenses"] if e["partner"] == "Bob")

        assert alice_total["total_paid"] == 80.0  # 50 + 30
        assert bob_total["total_paid"] == 20.0

    def test_get_expenses_empty_result(self, mock_expense_repository: Mock) -> None:
        """Test retrieving expenses when none exist."""
        mock_expense_repository.get_expenses.return_value = []

        result = get_expenses(
            "all", aggregate=False, repository=mock_expense_repository
        )

        assert result["success"] is True
        assert result["expenses"] == []

    def test_get_expenses_response_format(self, mock_expense_repository: Mock) -> None:
        """Test that expense response has correct format."""
        expenses = [
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.0"),
                currency="USD",
                description="Lunch",
                paid_by=Partner("Alice"),
            ),
        ]
        mock_expense_repository.get_expenses.return_value = expenses

        result = get_expenses(
            "all", aggregate=False, repository=mock_expense_repository
        )

        assert result["success"] is True
        expense_dict = result["expenses"][0]

        # Verify all required fields are present
        assert "id" in expense_dict
        assert "date" in expense_dict
        assert "amount" in expense_dict
        assert "currency" in expense_dict
        assert "description" in expense_dict
        assert "paid_by" in expense_dict

        # Verify field types and values
        assert expense_dict["date"] == "2025-01-15"
        assert expense_dict["amount"] == 50.0
        assert expense_dict["currency"] == "USD"
        assert expense_dict["description"] == "Lunch"
        assert expense_dict["paid_by"] == "Alice"


class TestExpenseToolResponseFormat:
    """Test response formatting for LLM integration."""

    def test_log_expense_success_response_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that success responses have correct format."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_123"

        result = log_expense(
            50.0, "USD", "Lunch", paid_by="Alice", repository=mock_expense_repository
        )

        # Success response should have success=True, message, and expense_id
        assert "success" in result
        assert result["success"] is True
        assert "message" in result
        assert isinstance(result["message"], str)
        assert "expense_id" in result
        assert isinstance(result["expense_id"], str)
        assert "error" not in result

    def test_log_expense_error_response_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that error responses have correct format."""
        result = log_expense(
            -10.0, "USD", "Invalid", repository=mock_expense_repository
        )

        # Error response should have success=False and error
        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert "message" not in result
        assert "expense_id" not in result

    def test_split_expense_success_response_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that split success responses have correct format."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [
            Partner("Alice"),
            Partner("Bob"),
        ]

        result = split_expense(
            "exp_123", ["Alice", "Bob"], repository=mock_expense_repository
        )

        assert "success" in result
        assert result["success"] is True
        assert "message" in result
        assert isinstance(result["message"], str)
        assert "error" not in result

    def test_get_expenses_success_response_format(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test that get expenses success responses have correct format."""
        mock_expense_repository.get_expenses.return_value = []

        result = get_expenses("all", repository=mock_expense_repository)

        assert "success" in result
        assert result["success"] is True
        assert "expenses" in result
        assert isinstance(result["expenses"], list)
        assert "error" not in result


class TestExpenseToolEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_log_expense_large_amount(self, mock_expense_repository: Mock) -> None:
        """Test logging expense with large amount."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_123"

        result = log_expense(
            999999.99,
            "USD",
            "Expensive",
            paid_by="Alice",
            repository=mock_expense_repository,
        )

        assert result["success"] is True

    def test_log_expense_small_amount(self, mock_expense_repository: Mock) -> None:
        """Test logging expense with very small amount."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_123"

        result = log_expense(
            0.01, "USD", "Cheap", paid_by="Alice", repository=mock_expense_repository
        )

        assert result["success"] is True

    def test_split_expense_single_partner(self, mock_expense_repository: Mock) -> None:
        """Test splitting expense with single partner."""
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.0"),
            currency="USD",
            description="Lunch",
            paid_by=Partner("Alice"),
        )
        mock_expense_repository.get_expense_by_id.return_value = expense
        mock_expense_repository.list_partners.return_value = [Partner("Alice")]

        result = split_expense("exp_123", ["Alice"], repository=mock_expense_repository)

        assert result["success"] is True
        assert "Expense split among 1 partners" in result["message"]

    def test_get_expenses_same_start_and_end_date(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test date range with same start and end date."""
        mock_expense_repository.get_expenses.return_value = []

        result = get_expenses(
            "2025-01-15 to 2025-01-15", repository=mock_expense_repository
        )

        assert result["success"] is True

        # Verify repository was called with same date
        mock_expense_repository.get_expenses.assert_called_once_with(
            datetime.date(2025, 1, 15), datetime.date(2025, 1, 15)
        )

    def test_log_expense_with_long_description(
        self, mock_expense_repository: Mock
    ) -> None:
        """Test logging expense with long description."""
        alice = Partner("Alice")
        mock_expense_repository.list_partners.return_value = [alice]
        mock_expense_repository.log_expense.return_value = "exp_123"

        long_description = "A" * 500

        result = log_expense(
            50.0,
            "USD",
            long_description,
            paid_by="Alice",
            repository=mock_expense_repository,
        )

        assert result["success"] is True
