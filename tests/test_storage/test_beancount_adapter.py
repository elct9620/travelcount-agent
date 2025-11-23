"""Tests for BeancountAdapter implementing PartnerRepository protocol.

This module tests the Beancount storage adapter's ability to translate
Partner entities to/from Beancount account directives, ensuring proper
persistence, retrieval, and error handling.
"""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from beancount.core import data
from agents.travelcount.entities.partner import Partner
from agents.travelcount.storage.beancount_adapter import BeancountAdapter
from agents.travelcount.storage.session_manager import SessionManager


class TestBeancountAdapterInitialization:
    """Test BeancountAdapter initialization and setup."""

    def test_adapter_creation_initializes_ledger(
        self, session_manager: SessionManager
    ) -> None:
        """Test that creating adapter ensures ledger file exists."""
        ledger_path = session_manager.get_ledger_path()
        assert not ledger_path.exists()

        BeancountAdapter(session_manager)

        assert ledger_path.exists()
        assert ledger_path.is_file()

    def test_adapter_requires_session_manager(self) -> None:
        """Test that adapter requires a SessionManager instance."""
        # This test verifies the type annotation is enforced at runtime
        # In Python, we can't prevent None at runtime without validation
        # but we test that it's passed correctly
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager("test-session")
            manager._base_data_dir = Path(tmpdir)
            adapter = BeancountAdapter(manager)
            assert adapter._session_manager == manager


class TestBeancountAdapterAddPartner:
    """Test adding partners to Beancount ledger."""

    def test_add_partner_writes_open_directive(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that add_partner writes an Open directive to the ledger."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        ledger_content = session_manager.get_ledger_path().read_text()
        assert "open Assets:Travel:Partners:Alice" in ledger_content
        assert "USD" in ledger_content

    def test_add_partner_uses_current_date(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that add_partner uses today's date for the Open directive."""
        partner = Partner("Alice")
        today = date.today()

        beancount_adapter.add_partner(partner)

        ledger_content = session_manager.get_ledger_path().read_text()
        expected_date = today.strftime("%Y-%m-%d")
        assert expected_date in ledger_content

    def test_add_partner_raises_error_for_duplicate(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that adding a duplicate partner raises ValueError."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        with pytest.raises(ValueError, match="Partner 'Alice' already exists"):
            beancount_adapter.add_partner(partner)

    def test_add_partner_creates_correct_account_name(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that partner name is correctly translated to account name."""
        partner = Partner("Bob Chen")
        beancount_adapter.add_partner(partner)

        ledger_content = session_manager.get_ledger_path().read_text()
        # Spaces in partner names are converted to hyphens for Beancount compatibility
        assert "Assets:Travel:Partners:Bob-Chen" in ledger_content

    def test_add_multiple_partners(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test adding multiple partners creates separate directives."""
        partners = [Partner("Alice"), Partner("Bob"), Partner("Charlie")]

        for partner in partners:
            beancount_adapter.add_partner(partner)

        ledger_content = session_manager.get_ledger_path().read_text()
        assert "Assets:Travel:Partners:Alice" in ledger_content
        assert "Assets:Travel:Partners:Bob" in ledger_content
        assert "Assets:Travel:Partners:Charlie" in ledger_content


class TestBeancountAdapterRemovePartner:
    """Test removing partners from Beancount ledger."""

    def test_remove_partner_writes_close_directive(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that remove_partner writes a Close directive to the ledger."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        beancount_adapter.remove_partner("Alice")

        ledger_content = session_manager.get_ledger_path().read_text()
        assert "close Assets:Travel:Partners:Alice" in ledger_content

    def test_remove_partner_raises_error_for_nonexistent(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that removing non-existent partner raises ValueError."""
        with pytest.raises(ValueError, match="Partner 'Bob' does not exist"):
            beancount_adapter.remove_partner("Bob")

    def test_remove_partner_uses_current_date(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that remove_partner uses today's date for the Close directive."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        today = date.today()
        beancount_adapter.remove_partner("Alice")

        ledger_content = session_manager.get_ledger_path().read_text()
        expected_date = today.strftime("%Y-%m-%d")
        # The close directive should have today's date
        assert f"{expected_date} close" in ledger_content

    def test_remove_partner_does_not_delete_open_directive(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that removing a partner preserves the original Open directive."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        beancount_adapter.remove_partner("Alice")

        ledger_content = session_manager.get_ledger_path().read_text()
        # Both open and close directives should exist
        assert "open Assets:Travel:Partners:Alice" in ledger_content
        assert "close Assets:Travel:Partners:Alice" in ledger_content

    def test_remove_partner_with_nonzero_balance_raises_error(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that removing a partner with non-zero balance raises ValueError."""
        from agents.travelcount.entities.expense import Expense

        # Add partner and log an expense
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        expense = Expense(
            date=date.today(),
            amount=100.0,
            currency="USD",
            description="Test expense",
            paid_by=partner,
        )
        beancount_adapter.log_expense(expense)

        # Attempt to remove partner with non-zero balance
        with pytest.raises(
            ValueError,
            match="Cannot remove partner 'Alice' because the account has a non-zero balance",
        ):
            beancount_adapter.remove_partner("Alice")

    def test_remove_partner_with_zero_balance_succeeds(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that removing a partner with zero balance succeeds."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        # Remove partner without any transactions (zero balance)
        beancount_adapter.remove_partner("Alice")

        # Verify close directive was written
        ledger_content = session_manager.get_ledger_path().read_text()
        assert "close Assets:Travel:Partners:Alice" in ledger_content

        # Verify partner is no longer active
        assert not beancount_adapter.partner_exists("Alice")


class TestBeancountAdapterListPartners:
    """Test listing partners from Beancount ledger."""

    def test_list_partners_returns_all_active_partners(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that list_partners returns all partners with open accounts."""
        partners = [Partner("Alice"), Partner("Bob"), Partner("Charlie")]

        for partner in partners:
            beancount_adapter.add_partner(partner)

        result = beancount_adapter.list_partners()

        assert len(result) == 3
        assert Partner("Alice") in result
        assert Partner("Bob") in result
        assert Partner("Charlie") in result

    def test_list_partners_excludes_closed_partners(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that list_partners excludes partners with closed accounts."""
        beancount_adapter.add_partner(Partner("Alice"))
        beancount_adapter.add_partner(Partner("Bob"))
        beancount_adapter.add_partner(Partner("Charlie"))

        # Close Bob's account
        beancount_adapter.remove_partner("Bob")

        result = beancount_adapter.list_partners()

        assert len(result) == 2
        assert Partner("Alice") in result
        assert Partner("Charlie") in result
        assert Partner("Bob") not in result

    def test_list_partners_returns_empty_list_for_no_partners(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that list_partners returns empty list when no partners exist."""
        result = beancount_adapter.list_partners()

        assert result == []
        assert isinstance(result, list)

    def test_list_partners_returns_sorted_partners(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that list_partners returns partners in sorted order."""
        # Add partners in non-alphabetical order
        beancount_adapter.add_partner(Partner("Charlie"))
        beancount_adapter.add_partner(Partner("Alice"))
        beancount_adapter.add_partner(Partner("Bob"))

        result = beancount_adapter.list_partners()

        # Partners should be sorted alphabetically
        partner_names = [p.name for p in result]
        assert partner_names == ["Alice", "Bob", "Charlie"]


class TestBeancountAdapterPartnerExists:
    """Test checking partner existence in Beancount ledger."""

    def test_partner_exists_returns_true_for_existing_partner(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that partner_exists returns True for an added partner."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)

        assert beancount_adapter.partner_exists("Alice") is True

    def test_partner_exists_returns_false_for_nonexistent_partner(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that partner_exists returns False for non-existent partner."""
        assert beancount_adapter.partner_exists("Bob") is False

    def test_partner_exists_returns_false_after_removal(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that partner_exists returns False after partner is removed."""
        partner = Partner("Alice")
        beancount_adapter.add_partner(partner)
        beancount_adapter.remove_partner("Alice")

        assert beancount_adapter.partner_exists("Alice") is False

    def test_partner_exists_handles_invalid_name(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that partner_exists returns False for invalid partner names."""
        # Invalid names should return False (not raise exception)
        assert beancount_adapter.partner_exists("") is False
        assert beancount_adapter.partner_exists("alice@email") is False
        assert beancount_adapter.partner_exists("../traversal") is False


class TestBeancountAdapterAccountTranslation:
    """Test translation between Partner entities and Beancount account names."""

    def test_partner_to_account_name_translation(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test conversion from Partner entity to Beancount account name."""
        partner = Partner("Alice")
        account_name = beancount_adapter._partner_to_account_name(partner)

        assert account_name == "Assets:Travel:Partners:Alice"

    def test_account_name_to_partner_translation(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test conversion from Beancount account name to Partner entity."""
        account_name = "Assets:Travel:Partners:Alice"
        partner = beancount_adapter._account_name_to_partner(account_name)

        assert partner.name == "Alice"
        assert isinstance(partner, Partner)

    def test_account_name_to_partner_raises_error_for_invalid_prefix(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that invalid account names raise ValueError."""
        invalid_account = "Expenses:Travel:Alice"

        with pytest.raises(ValueError, match="does not match partner account pattern"):
            beancount_adapter._account_name_to_partner(invalid_account)

    def test_bidirectional_translation_consistency(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that translating back and forth maintains consistency."""
        original_partner = Partner("Alice")

        # Partner -> Account -> Partner
        account_name = beancount_adapter._partner_to_account_name(original_partner)
        recovered_partner = beancount_adapter._account_name_to_partner(account_name)

        assert recovered_partner == original_partner
        assert recovered_partner.name == original_partner.name


class TestBeancountAdapterFileIntegration:
    """Test Beancount file parsing and integration."""

    def test_beancount_file_parsing_integration(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that the adapter correctly parses Beancount files."""
        # Add partners
        beancount_adapter.add_partner(Partner("Alice"))
        beancount_adapter.add_partner(Partner("Bob"))

        # Parse the ledger file using Beancount loader
        entries, errors, options = beancount_adapter._load_entries()

        # Should have no parsing errors
        assert len(errors) == 0

        # Should have Open directives for both partners
        open_entries = [e for e in entries if isinstance(e, data.Open)]
        partner_accounts = [
            e.account
            for e in open_entries
            if e.account.startswith("Assets:Travel:Partners:")
        ]

        assert len(partner_accounts) == 2
        assert "Assets:Travel:Partners:Alice" in partner_accounts
        assert "Assets:Travel:Partners:Bob" in partner_accounts

    def test_adapter_handles_empty_ledger(
        self, beancount_adapter: BeancountAdapter
    ) -> None:
        """Test that adapter handles empty ledger correctly."""
        partners = beancount_adapter.list_partners()
        assert partners == []

    def test_adapter_handles_ledger_with_non_partner_accounts(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that adapter filters out non-partner accounts."""
        # Add a partner
        beancount_adapter.add_partner(Partner("Alice"))

        # Manually add a non-partner account to the ledger
        ledger_path = session_manager.get_ledger_path()
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write("\n2024-01-01 open Expenses:Food USD\n")

        # List should only return partner accounts
        partners = beancount_adapter.list_partners()
        assert len(partners) == 1
        assert partners[0].name == "Alice"

    def test_adapter_preserves_existing_ledger_content(
        self, beancount_adapter: BeancountAdapter, session_manager: SessionManager
    ) -> None:
        """Test that adapter preserves existing ledger content when adding."""
        # Add first partner
        beancount_adapter.add_partner(Partner("Alice"))

        # Add second partner
        beancount_adapter.add_partner(Partner("Bob"))
        second_content = session_manager.get_ledger_path().read_text()

        # First partner's directive should still be present
        assert "Assets:Travel:Partners:Alice" in second_content
        # Second partner's directive should be added
        assert "Assets:Travel:Partners:Bob" in second_content
        # Original header should be preserved
        assert "TravelCount Session Ledger" in second_content
