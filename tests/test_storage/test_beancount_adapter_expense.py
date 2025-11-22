"""Tests for BeancountAdapter implementing ExpenseRepository protocol.

This module tests the Beancount storage adapter's ability to manage expenses
through Transaction directives, including expense logging, splitting, and retrieval.
"""

from datetime import date
from decimal import Decimal

import pytest

from beancount.core import data
from agents.travelcount.entities.partner import Partner
from agents.travelcount.entities.expense import Expense
from agents.travelcount.storage.beancount_adapter import BeancountAdapter
from agents.travelcount.storage.session_manager import SessionManager


class TestBeancountAdapterCategoryInference:
    """Test category inference from expense descriptions."""

    def test_infer_food_category(self, beancount_adapter: BeancountAdapter) -> None:
        """Test that food-related keywords are correctly categorized."""
        food_descriptions = [
            "Lunch at cafe",
            "Dinner with friends",
            "Breakfast buffet",
            "Coffee shop",
            "Restaurant meal",
            "Quick snack",
        ]

        for description in food_descriptions:
            category = beancount_adapter._infer_category(description)
            assert category == "Food", f"'{description}' should be Food"

    def test_infer_transport_category(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that transport-related keywords are correctly categorized."""
        transport_descriptions = [
            "Taxi to airport",
            "Uber ride",
            "Train ticket",
            "Bus fare",
            "Flight booking",
            "Metro pass",
        ]

        for description in transport_descriptions:
            category = beancount_adapter._infer_category(description)
            assert category == "Transport", f"'{description}' should be Transport"

    def test_infer_hotel_category(self, beancount_adapter: BeancountAdapter) -> None:
        """Test that accommodation-related keywords are correctly categorized."""
        hotel_descriptions = [
            "Hotel reservation",
            "Airbnb stay",
            "Hostel booking",
            "Accommodation payment",
        ]

        for description in hotel_descriptions:
            category = beancount_adapter._infer_category(description)
            assert category == "Hotel", f"'{description}' should be Hotel"

    def test_infer_misc_category_default(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that unrecognized descriptions default to Misc."""
        misc_descriptions = [
            "Shopping",
            "Museum ticket",
            "Random expense",
            "xyz123",
        ]

        for description in misc_descriptions:
            category = beancount_adapter._infer_category(description)
            assert category == "Misc", f"'{description}' should default to Misc"

    def test_infer_category_case_insensitive(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that category inference is case-insensitive."""
        assert beancount_adapter._infer_category("LUNCH") == "Food"
        assert beancount_adapter._infer_category("Lunch") == "Food"
        assert beancount_adapter._infer_category("lunch") == "Food"
        assert beancount_adapter._infer_category("TAXI") == "Transport"


class TestBeancountAdapterLogExpense:
    """Test logging expenses to Beancount ledger."""

    def test_log_expense_writes_transaction(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that log_expense writes a Transaction directive to the ledger."""
        # Add partner first
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Create and log expense
        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("50.00"),
            currency="USD",
            description="Lunch at cafe",
            paid_by=alice,
        )

        expense_id = beancount_adapter.log_expense(expense)

        # Verify expense was logged
        assert expense_id == expense.id

        ledger_content = session_manager.get_ledger_path().read_text()
        assert "Lunch at cafe" in ledger_content
        assert f'expense-id: "{expense.id}"' in ledger_content
        assert "Expenses:Travel:Food" in ledger_content
        assert "50.00 USD" in ledger_content

    def test_log_expense_creates_correct_postings(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that log_expense creates debit and credit postings correctly."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Taxi to airport",
            paid_by=alice,
        )

        beancount_adapter.log_expense(expense)

        # Load and verify transaction
        entries, errors, options = beancount_adapter._load_entries()
        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        expense_txn = None
        for txn in transactions:
            if txn.meta.get("expense-id") == expense.id:
                expense_txn = txn
                break

        assert expense_txn is not None
        assert len(expense_txn.postings) == 2

        # Check expense posting (debit)
        expense_posting = expense_txn.postings[0]
        assert expense_posting.account == "Expenses:Travel:Transport"
        assert expense_posting.units.number == Decimal("100.00")
        assert expense_posting.units.currency == "USD"

        # Check partner posting (credit, balancing - Beancount fills this in)
        partner_posting = expense_txn.postings[1]
        assert partner_posting.account == "Assets:Travel:Partners:Alice"
        # Beancount automatically fills in the balancing amount
        assert partner_posting.units.number == Decimal("-100.00")
        assert partner_posting.units.currency == "USD"

    def test_log_expense_infers_category_correctly(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that log_expense correctly infers and uses expense category."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        test_cases = [
            ("Lunch at restaurant", "Food"),
            ("Taxi ride", "Transport"),
            ("Hotel booking", "Hotel"),
            ("Random expense", "Misc"),
        ]

        for description, expected_category in test_cases:
            expense = Expense(
                date=date(2024, 6, 1),
                amount=Decimal("50.00"),
                currency="USD",
                description=description,
                paid_by=alice,
            )

            beancount_adapter.log_expense(expense)

            ledger_content = session_manager.get_ledger_path().read_text()
            assert f"Expenses:Travel:{expected_category}" in ledger_content, (
                f"Expected category {expected_category} for '{description}'"
            )

    def test_log_multiple_expenses(self, beancount_adapter: BeancountAdapter) -> None:
        """Test logging multiple expenses creates separate transactions."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        expense1 = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("30.00"),
            currency="USD",
            description="Breakfast",
            paid_by=alice,
        )

        expense2 = Expense(
            date=date(2024, 6, 2),
            amount=Decimal("50.00"),
            currency="USD",
            description="Dinner",
            paid_by=bob,
        )

        beancount_adapter.log_expense(expense1)
        beancount_adapter.log_expense(expense2)

        # Verify both expenses exist
        entries, errors, options = beancount_adapter._load_entries()
        expense_transactions = [
            e
            for e in entries
            if isinstance(e, data.Transaction) and "expense-id" in e.meta
        ]

        assert len(expense_transactions) == 2
        expense_ids = {txn.meta["expense-id"] for txn in expense_transactions}
        assert expense_ids == {expense1.id, expense2.id}


class TestBeancountAdapterSplitExpense:
    """Test splitting expenses among partners."""

    def test_split_expense_equal_split(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test splitting an expense equally among partners."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Log original expense
        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Shared dinner",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Split expense equally
        beancount_adapter.split_expense(expense_id, [alice, bob])

        # Verify split transaction
        entries, errors, options = beancount_adapter._load_entries()
        split_txns = [
            e
            for e in entries
            if isinstance(e, data.Transaction) and "split-for" in e.meta
        ]

        assert len(split_txns) == 1
        split_txn = split_txns[0]

        assert split_txn.meta["split-for"] == expense_id
        assert split_txn.narration == "Split: Shared dinner"
        # Should have 2 postings: Alice receives net (+50), Bob owes net (-50)
        assert len(split_txn.postings) == 2

        # Check Alice's net position (paid $100, owes $50, net +$50)
        alice_posting = next(p for p in split_txn.postings if "Alice" in p.account)
        assert alice_posting.units.number == Decimal("50.00")

        # Check Bob's net position (paid $0, owes $50, net -$50)
        bob_posting = next(p for p in split_txn.postings if "Bob" in p.account)
        assert bob_posting.units.number == Decimal("-50.00")

    def test_split_expense_custom_ratios(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test splitting an expense with custom ratios."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        charlie = Partner("Charlie")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)
        beancount_adapter.add_partner(charlie)

        # Log original expense
        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Group meal",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Split with custom ratios: Alice 50%, Bob 30%, Charlie 20%
        beancount_adapter.split_expense(
            expense_id, [alice, bob, charlie], [0.5, 0.3, 0.2]
        )

        # Verify split amounts using net settlement calculation
        # Alice paid $100, owes $50 (50%), net = +$50
        # Bob paid $0, owes $30 (30%), net = -$30
        # Charlie paid $0, owes $20 (20%), net = -$20
        entries, errors, options = beancount_adapter._load_entries()
        split_txn = next(
            e
            for e in entries
            if isinstance(e, data.Transaction) and e.meta.get("split-for") == expense_id
        )

        # Should have 3 postings (all partners have non-zero net amounts)
        assert len(split_txn.postings) == 3

        alice_posting = next(p for p in split_txn.postings if "Alice" in p.account)
        bob_posting = next(p for p in split_txn.postings if "Bob" in p.account)
        charlie_posting = next(p for p in split_txn.postings if "Charlie" in p.account)

        assert alice_posting.units.number == Decimal("50.00")
        assert bob_posting.units.number == Decimal("-30.00")
        assert charlie_posting.units.number == Decimal("-20.00")

    def test_split_expense_raises_for_nonexistent_expense(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that splitting non-existent expense raises ValueError."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        with pytest.raises(ValueError, match="Expense with ID 'nonexistent' not found"):
            beancount_adapter.split_expense("nonexistent", [alice, bob])

    def test_split_expense_raises_for_invalid_ratios(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that invalid ratios raise ValueError."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Test",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Ratios don't sum to 1.0
        with pytest.raises(ValueError, match="Ratios must sum to 1.0"):
            beancount_adapter.split_expense(expense_id, [alice, bob], [0.3, 0.5])

    def test_split_expense_raises_for_mismatched_ratios_length(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that mismatched ratios/partners length raises ValueError."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Test",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        with pytest.raises(
            ValueError, match="Ratios length must match partners length"
        ):
            beancount_adapter.split_expense(expense_id, [alice, bob], [1.0])


class TestBeancountAdapterGetExpenses:
    """Test retrieving expenses from Beancount ledger."""

    def test_get_expenses_returns_all_expenses(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expenses returns all logged expenses."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        expenses = [
            Expense(
                date=date(2024, 6, i + 1),
                amount=Decimal(f"{(i + 1) * 10}.00"),
                currency="USD",
                description=f"Expense {i + 1}",
                paid_by=alice,
            )
            for i in range(3)
        ]

        for expense in expenses:
            beancount_adapter.log_expense(expense)

        retrieved = beancount_adapter.get_expenses()

        assert len(retrieved) == 3
        retrieved_ids = {e.id for e in retrieved}
        expected_ids = {e.id for e in expenses}
        assert retrieved_ids == expected_ids

    def test_get_expenses_filters_by_date_range(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expenses correctly filters by date range."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Create expenses on different dates
        dates = [date(2024, 6, 1), date(2024, 6, 5), date(2024, 6, 10)]
        expenses_by_date = {}
        for i, expense_date in enumerate(dates):
            expense = Expense(
                date=expense_date,
                amount=Decimal("50.00"),
                currency="USD",
                description=f"Expense on {expense_date}",
                paid_by=alice,
            )
            beancount_adapter.log_expense(expense)
            expenses_by_date[expense_date] = expense

        # Filter for middle date range
        filtered = beancount_adapter.get_expenses(
            date_from=date(2024, 6, 3), date_to=date(2024, 6, 8)
        )

        assert len(filtered) == 1
        assert filtered[0].date == date(2024, 6, 5)

    def test_get_expenses_returns_empty_list_for_no_matches(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expenses returns empty list when no expenses exist."""
        retrieved = beancount_adapter.get_expenses()

        assert retrieved == []
        assert isinstance(retrieved, list)

    def test_get_expenses_excludes_split_transactions(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expenses only returns expense transactions, not splits."""
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Log and split expense
        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="Test",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)
        beancount_adapter.split_expense(expense_id, [alice, bob])

        # get_expenses should only return the original expense, not the split
        expenses = beancount_adapter.get_expenses()

        assert len(expenses) == 1
        assert expenses[0].id == expense_id


class TestBeancountAdapterGetExpenseById:
    """Test retrieving a specific expense by ID."""

    def test_get_expense_by_id_returns_correct_expense(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expense_by_id retrieves the correct expense."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("75.00"),
            currency="USD",
            description="Target expense",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        retrieved = beancount_adapter.get_expense_by_id(expense_id)

        assert retrieved is not None
        assert retrieved.id == expense_id
        assert retrieved.amount == Decimal("75.00")
        assert retrieved.description == "Target expense"
        assert retrieved.paid_by == alice

    def test_get_expense_by_id_returns_none_for_nonexistent(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expense_by_id returns None for non-existent expense."""
        retrieved = beancount_adapter.get_expense_by_id("nonexistent")

        assert retrieved is None

    def test_get_expense_by_id_finds_among_multiple(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that get_expense_by_id finds correct expense among multiple."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Log multiple expenses
        expense_ids = []
        for i in range(5):
            expense = Expense(
                date=date(2024, 6, i + 1),
                amount=Decimal(f"{(i + 1) * 10}.00"),
                currency="USD",
                description=f"Expense {i}",
                paid_by=alice,
            )
            expense_ids.append(expense.id)
            beancount_adapter.log_expense(expense)

        # Find specific expense (third one, index 2)
        target = beancount_adapter.get_expense_by_id(expense_ids[2])

        assert target is not None
        assert target.id == expense_ids[2]
        assert target.amount == Decimal("30.00")


class TestBeancountAdapterParseTransaction:
    """Test parsing Transaction directives to Expense entities."""

    def test_parse_transaction_to_expense(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that _parse_transaction_to_expense correctly constructs Expense."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        expense = Expense(
            date=date(2024, 6, 15),
            amount=Decimal("123.45"),
            currency="USD",
            description="Parse test expense",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Retrieve and parse
        retrieved = beancount_adapter.get_expense_by_id(expense_id)

        assert retrieved.id == expense_id
        assert retrieved.date == date(2024, 6, 15)
        assert retrieved.amount == Decimal("123.45")
        assert retrieved.currency == "USD"
        assert retrieved.description == "Parse test expense"
        assert retrieved.paid_by.name == "Alice"

    def test_parse_transaction_raises_for_missing_expense_id(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that parsing transaction without expense-id raises ValueError."""
        # Manually create a transaction without expense-id

        ledger_path = beancount_adapter._get_ledger_path()

        txn = data.Transaction(
            meta={"filename": str(ledger_path), "lineno": 0},
            date=date(2024, 6, 1),
            flag="*",
            payee=None,
            narration="No expense ID",
            tags=set(),
            links=set(),
            postings=[],
        )

        with pytest.raises(ValueError, match="does not have expense-id metadata"):
            beancount_adapter._parse_transaction_to_expense(txn)


class TestBeancountAdapterExpenseIntegration:
    """Integration tests for expense tracking workflow."""

    def test_full_expense_workflow(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test complete workflow: log, retrieve, split expense."""
        # Setup partners
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Log expense
        expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("200.00"),
            currency="USD",
            description="Hotel room",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Retrieve expense
        retrieved = beancount_adapter.get_expense_by_id(expense_id)
        assert retrieved is not None
        assert retrieved.amount == Decimal("200.00")

        # Split expense
        beancount_adapter.split_expense(expense_id, [alice, bob])

        # Verify ledger has both transactions
        entries, errors, options = beancount_adapter._load_entries()
        transactions = [e for e in entries if isinstance(e, data.Transaction)]

        assert len(transactions) == 2  # Original expense + split

        # Verify ledger content
        ledger_content = session_manager.get_ledger_path().read_text()
        assert "Hotel room" in ledger_content
        assert "Split: Hotel room" in ledger_content
        assert "Expenses:Travel:Hotel" in ledger_content

    def test_expense_with_different_currencies(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test handling expenses in different currencies."""
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # USD expense
        usd_expense = Expense(
            date=date(2024, 6, 1),
            amount=Decimal("100.00"),
            currency="USD",
            description="USD payment",
            paid_by=alice,
        )
        usd_id = beancount_adapter.log_expense(usd_expense)

        # EUR expense (note: this might require currency support in Partner accounts)
        eur_expense = Expense(
            date=date(2024, 6, 2),
            amount=Decimal("85.00"),
            currency="EUR",
            description="EUR payment",
            paid_by=alice,
        )
        eur_id = beancount_adapter.log_expense(eur_expense)

        # Retrieve both
        usd = beancount_adapter.get_expense_by_id(usd_id)
        eur = beancount_adapter.get_expense_by_id(eur_id)

        assert usd.currency == "USD"
        assert eur.currency == "EUR"
