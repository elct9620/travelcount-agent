"""Tests for Expense entity."""

import datetime
from decimal import Decimal

import pytest

from agents.travelcount.entities.expense import Expense
from agents.travelcount.entities.partner import Partner


class TestExpenseConstruction:
    """Test Expense entity construction and validation."""

    def test_create_expense_with_valid_attributes(self) -> None:
        """Test creating an expense with valid attributes."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch at restaurant",
            paid_by=partner,
        )

        assert expense.date == datetime.date(2025, 1, 15)
        assert expense.amount == Decimal("50.00")
        assert expense.currency == "USD"
        assert expense.description == "Lunch at restaurant"
        assert expense.paid_by == partner
        assert isinstance(expense.id, str)
        assert len(expense.id) == 8

    def test_create_expense_with_different_currencies(self) -> None:
        """Test creating expenses with different currency codes."""
        partner = Partner("Bob")

        expense_usd = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("100.00"),
            currency="USD",
            description="Hotel",
            paid_by=partner,
        )
        assert expense_usd.currency == "USD"

        expense_eur = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("100.00"),
            currency="EUR",
            description="Hotel",
            paid_by=partner,
        )
        assert expense_eur.currency == "EUR"

        expense_jpy = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("10000"),
            currency="JPY",
            description="Hotel",
            paid_by=partner,
        )
        assert expense_jpy.currency == "JPY"

    def test_create_expense_with_decimal_amount(self) -> None:
        """Test creating expense with precise decimal amount."""
        partner = Partner("Charlie")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("123.45"),
            currency="USD",
            description="Shopping",
            paid_by=partner,
        )
        assert expense.amount == Decimal("123.45")

    def test_create_expense_generates_unique_id(self) -> None:
        """Test that expense ID is generated consistently."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        # Same attributes should produce same ID
        assert expense1.id == expense2.id

    def test_create_expense_different_attributes_generate_different_ids(self) -> None:
        """Test that different attributes generate different IDs."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 16),  # Different date
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        # Different attributes should produce different IDs
        assert expense1.id != expense2.id


class TestExpenseAmountValidation:
    """Test Expense amount validation rules."""

    def test_zero_amount_raises_error(self) -> None:
        """Test that zero amount raises ValueError."""
        partner = Partner("Alice")
        with pytest.raises(ValueError, match="Expense amount must be positive"):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("0"),
                currency="USD",
                description="Free item",
                paid_by=partner,
            )

    def test_negative_amount_raises_error(self) -> None:
        """Test that negative amount raises ValueError."""
        partner = Partner("Bob")
        with pytest.raises(ValueError, match="Expense amount must be positive"):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("-10.00"),
                currency="USD",
                description="Refund",
                paid_by=partner,
            )

    def test_positive_amount_is_valid(self) -> None:
        """Test that positive amounts are valid."""
        partner = Partner("Charlie")

        # Small amount
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("0.01"),
            currency="USD",
            description="Penny",
            paid_by=partner,
        )
        assert expense1.amount == Decimal("0.01")

        # Large amount
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("999999.99"),
            currency="USD",
            description="Expensive",
            paid_by=partner,
        )
        assert expense2.amount == Decimal("999999.99")


class TestExpenseCurrencyValidation:
    """Test Expense currency code validation rules."""

    def test_empty_currency_raises_error(self) -> None:
        """Test that empty currency code raises ValueError."""
        partner = Partner("Alice")
        with pytest.raises(ValueError, match="Currency code cannot be empty"):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="",
                description="Lunch",
                paid_by=partner,
            )

    def test_lowercase_currency_raises_error(self) -> None:
        """Test that lowercase currency code raises ValueError."""
        partner = Partner("Bob")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="usd",
                description="Lunch",
                paid_by=partner,
            )

    def test_mixed_case_currency_raises_error(self) -> None:
        """Test that mixed case currency code raises ValueError."""
        partner = Partner("Charlie")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="Usd",
                description="Lunch",
                paid_by=partner,
            )

    def test_too_short_currency_raises_error(self) -> None:
        """Test that currency code shorter than 3 letters raises ValueError."""
        partner = Partner("Alice")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="US",
                description="Lunch",
                paid_by=partner,
            )

    def test_too_long_currency_raises_error(self) -> None:
        """Test that currency code longer than 3 letters raises ValueError."""
        partner = Partner("Bob")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="USDD",
                description="Lunch",
                paid_by=partner,
            )

    def test_currency_with_numbers_raises_error(self) -> None:
        """Test that currency code with numbers raises ValueError."""
        partner = Partner("Charlie")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="US1",
                description="Lunch",
                paid_by=partner,
            )

    def test_currency_with_special_characters_raises_error(self) -> None:
        """Test that currency code with special characters raises ValueError."""
        partner = Partner("Alice")
        with pytest.raises(
            ValueError, match="Currency code must be 3 uppercase letters"
        ):
            Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("50.00"),
                currency="US$",
                description="Lunch",
                paid_by=partner,
            )

    def test_valid_currency_codes_are_accepted(self) -> None:
        """Test that valid 3-letter uppercase currency codes are accepted."""
        partner = Partner("Alice")

        valid_currencies = ["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD"]
        for currency in valid_currencies:
            expense = Expense(
                date=datetime.date(2025, 1, 15),
                amount=Decimal("100.00"),
                currency=currency,
                description="Test",
                paid_by=partner,
            )
            assert expense.currency == currency


class TestExpenseEquality:
    """Test Expense equality comparison."""

    def test_same_attributes_expenses_are_equal(self) -> None:
        """Test that two expenses with same attributes are equal."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert expense1 == expense2

    def test_different_date_expenses_are_not_equal(self) -> None:
        """Test that expenses with different dates are not equal."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 16),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert expense1 != expense2

    def test_different_amount_expenses_are_not_equal(self) -> None:
        """Test that expenses with different amounts are not equal."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("60.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert expense1 != expense2

    def test_expense_not_equal_to_non_expense_object(self) -> None:
        """Test that expense is not equal to non-Expense objects."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert expense != "Expense"
        assert expense != 123
        assert expense is not None
        assert expense != {}

    def test_expense_not_equal_to_non_expense_returns_not_implemented(self) -> None:
        """Test that comparing with non-Expense returns NotImplemented correctly."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        result = expense.__eq__("Expense")
        assert result == NotImplemented


class TestExpenseHashing:
    """Test Expense hashing for use in sets and dicts."""

    def test_expense_is_hashable(self) -> None:
        """Test that Expense instances are hashable."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        hash_value = hash(expense)
        assert isinstance(hash_value, int)

    def test_same_attributes_expenses_have_same_hash(self) -> None:
        """Test that expenses with same attributes have same hash."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert hash(expense1) == hash(expense2)

    def test_expense_can_be_used_in_set(self) -> None:
        """Test that Expense instances can be used in sets."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 16),
            amount=Decimal("60.00"),
            currency="USD",
            description="Dinner",
            paid_by=partner,
        )
        expense3 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        expense_set = {expense1, expense2, expense3}
        assert len(expense_set) == 2  # expense1 and expense3 are duplicates

    def test_expense_can_be_used_as_dict_key(self) -> None:
        """Test that Expense instances can be used as dictionary keys."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 16),
            amount=Decimal("60.00"),
            currency="USD",
            description="Dinner",
            paid_by=partner,
        )

        expense_dict = {
            expense1: "Lunch expense",
            expense2: "Dinner expense",
        }

        # Create new instances with same attributes to test key lookup
        lookup_expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        assert expense_dict[lookup_expense1] == "Lunch expense"


class TestExpenseRepr:
    """Test Expense string representation."""

    def test_expense_repr_format(self) -> None:
        """Test that __repr__ returns expected format."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        repr_str = repr(expense)

        assert repr_str.startswith("Expense(")
        assert "id=" in repr_str
        assert "date=datetime.date(2025, 1, 15)" in repr_str
        assert "amount=Decimal('50.00')" in repr_str
        assert "currency='USD'" in repr_str
        assert "description='Lunch'" in repr_str
        assert "paid_by=Partner(name='Alice')" in repr_str

    def test_expense_repr_is_useful_for_debugging(self) -> None:
        """Test that repr output contains relevant debugging info."""
        partner = Partner("Bob")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("100.00"),
            currency="EUR",
            description="Hotel",
            paid_by=partner,
        )
        repr_str = repr(expense)

        assert "Expense" in repr_str
        assert "Hotel" in repr_str
        assert "EUR" in repr_str
        assert "Bob" in repr_str


class TestExpenseIdGeneration:
    """Test Expense ID generation logic."""

    def test_id_is_deterministic(self) -> None:
        """Test that same inputs always generate same ID."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        assert expense1.id == expense2.id

    def test_id_changes_with_different_date(self) -> None:
        """Test that ID changes when date changes."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 16),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        assert expense1.id != expense2.id

    def test_id_changes_with_different_amount(self) -> None:
        """Test that ID changes when amount changes."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.01"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        assert expense1.id != expense2.id

    def test_id_changes_with_different_currency(self) -> None:
        """Test that ID changes when currency changes."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="EUR",
            description="Lunch",
            paid_by=partner,
        )

        assert expense1.id != expense2.id

    def test_id_changes_with_different_description(self) -> None:
        """Test that ID changes when description changes."""
        partner = Partner("Alice")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Dinner",
            paid_by=partner,
        )

        assert expense1.id != expense2.id

    def test_id_changes_with_different_partner(self) -> None:
        """Test that ID changes when partner changes."""
        partner1 = Partner("Alice")
        partner2 = Partner("Bob")
        expense1 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner1,
        )
        expense2 = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner2,
        )

        assert expense1.id != expense2.id

    def test_id_is_8_characters_long(self) -> None:
        """Test that generated ID is exactly 8 characters."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        assert len(expense.id) == 8

    def test_id_is_hexadecimal(self) -> None:
        """Test that generated ID contains only hexadecimal characters."""
        partner = Partner("Alice")
        expense = Expense(
            date=datetime.date(2025, 1, 15),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch",
            paid_by=partner,
        )

        # Check if all characters are valid hexadecimal (0-9, a-f)
        assert all(c in "0123456789abcdef" for c in expense.id)
