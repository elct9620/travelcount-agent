"""Acceptance tests for partner management scenarios in TravelCount.

These tests verify complete user workflows from the user's perspective, testing
that partner management operations work correctly end-to-end with real components
(SessionManager, BeancountAdapter, and partners tool).

Test scenarios:
1. User adds a new partner named "Alice"
2. User removes an existing partner named "Alice"
3. User lists all partners (with and without partners)
4. User attempts to add a duplicate partner (error handling)
5. User attempts to remove a non-existent partner (error handling)
"""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from beancount import loader

from agents.travelcount.tools.partner import partners
from entities.partner import Partner
from storage.beancount_adapter import BeancountAdapter
from storage.session_manager import SessionManager


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data and clean up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_data_dir):
    """Create a SessionManager with temporary directory."""
    manager = SessionManager("test-session-acceptance")
    manager._base_data_dir = temp_data_dir
    manager.ensure_session_directory()
    manager.initialize_ledger()
    return manager


@pytest.fixture
def beancount_adapter(session_manager):
    """Create a BeancountAdapter with SessionManager."""
    return BeancountAdapter(session_manager)


def _get_open_accounts(ledger_path: Path) -> set[str]:
    """Helper to get all open partner accounts from a ledger file."""
    if not ledger_path.exists():
        return set()

    entries, errors, options = loader.load_file(str(ledger_path))

    opened_accounts = set()
    closed_accounts = set()

    for entry in entries:
        from beancount.core.data import Open, Close

        if isinstance(entry, Open):
            if entry.account.startswith("Assets:Travel:Partners:"):
                opened_accounts.add(entry.account)
        elif isinstance(entry, Close):
            if entry.account.startswith("Assets:Travel:Partners:"):
                closed_accounts.add(entry.account)

    return opened_accounts - closed_accounts


def _get_all_entries_of_type(ledger_path: Path, entry_type):
    """Helper to get all entries of a specific type from ledger."""
    if not ledger_path.exists():
        return []

    entries, errors, options = loader.load_file(str(ledger_path))
    return [e for e in entries if isinstance(e, entry_type)]


class TestScenarioAddNewPartner:
    """Scenario: User adds a partner named "Alice" to the travel session."""

    def test_scenario_add_new_partner(self, beancount_adapter, session_manager):
        """Test adding a new partner through the tool interface.

        Verifies:
        - Partner is persisted in Beancount as Assets:Travel:Partners:Alice
        - Open directive is written with current date
        - Tool returns success message: "Partner 'Alice' has been added."
        """
        # Act: Add partner through tool
        result = partners("add", "Alice", repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True
        assert result["message"] == "Partner 'Alice' has been added."

        # Assert: Partner exists in repository
        assert beancount_adapter.partner_exists("Alice")

        # Assert: Partner appears in list
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 1
        assert partner_list[0].name == "Alice"

        # Assert: Open directive written to ledger
        ledger_path = session_manager.get_ledger_path()
        open_accounts = _get_open_accounts(ledger_path)
        assert "Assets:Travel:Partners:Alice" in open_accounts

        # Assert: Verify open directive details in ledger
        from beancount.core.data import Open

        open_entries = _get_all_entries_of_type(ledger_path, Open)
        alice_open = next((e for e in open_entries if "Alice" in e.account), None)
        assert alice_open is not None
        assert alice_open.account == "Assets:Travel:Partners:Alice"
        assert alice_open.date == date.today()
        assert "USD" in alice_open.currencies

        # Assert: Ledger file has been modified
        ledger_content = ledger_path.read_text()
        assert "Assets:Travel:Partners:Alice" in ledger_content
        # Note: Beancount printer may add spacing, so check for key parts
        assert "open Assets:Travel:Partners:Alice" in ledger_content
        assert "USD" in ledger_content


class TestScenarioRemoveExistingPartner:
    """Scenario: User removes a partner named "Alice" from the travel session."""

    def test_scenario_remove_existing_partner(self, beancount_adapter, session_manager):
        """Test removing an existing partner through the tool interface.

        Setup: Add partner "Alice" first
        Verifies:
        - Close directive is written with current date
        - Tool returns success message: "Partner 'Alice' has been removed."
        - Partner no longer appears in list
        """
        # Setup: Add partner
        beancount_adapter.add_partner(Partner("Alice"))
        assert beancount_adapter.partner_exists("Alice")

        # Act: Remove partner through tool
        result = partners("remove", "Alice", repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True
        assert result["message"] == "Partner 'Alice' has been removed."

        # Assert: Partner no longer exists
        assert not beancount_adapter.partner_exists("Alice")

        # Assert: Partner doesn't appear in list
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 0

        # Assert: Close directive written to ledger
        ledger_path = session_manager.get_ledger_path()
        open_accounts = _get_open_accounts(ledger_path)
        assert "Assets:Travel:Partners:Alice" not in open_accounts

        # Assert: Verify close directive details in ledger
        from beancount.core.data import Close

        close_entries = _get_all_entries_of_type(ledger_path, Close)
        alice_close = next((e for e in close_entries if "Alice" in e.account), None)
        assert alice_close is not None
        assert alice_close.account == "Assets:Travel:Partners:Alice"
        assert alice_close.date == date.today()

        # Assert: Ledger file has both open and close directives
        ledger_content = ledger_path.read_text()
        assert "open Assets:Travel:Partners:Alice" in ledger_content
        assert "close Assets:Travel:Partners:Alice" in ledger_content


class TestScenarioListAllPartners:
    """Scenario: User requests to see all active travel partners."""

    def test_scenario_list_all_partners_with_multiple_partners(self, beancount_adapter):
        """Test listing all partners when multiple exist.

        Setup: Add partners "Alice" and "Bob"
        Verifies:
        - Returns all partners with open accounts
        - Formatted response: "Your travel partners are: Alice, Bob."
        """
        # Setup: Add multiple partners
        beancount_adapter.add_partner(Partner("Alice"))
        beancount_adapter.add_partner(Partner("Bob"))

        # Act: List partners through tool
        result = partners("list", repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True

        # Assert: Response contains both partners
        assert "Your travel partners are:" in result["message"]
        assert "Alice" in result["message"]
        assert "Bob" in result["message"]

        # Assert: Specific message format
        # Note: Partners are sorted alphabetically
        assert result["message"] == "Your travel partners are: Alice, Bob."

        # Assert: Repository returns correct partners
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 2
        partner_names = {p.name for p in partner_list}
        assert partner_names == {"Alice", "Bob"}

    def test_scenario_list_all_partners_empty_case(self, beancount_adapter):
        """Test listing partners when none exist.

        Verifies:
        - Returns appropriate empty message: "You have no travel partners yet."
        """
        # Act: List partners with no partners added
        result = partners("list", repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True

        # Assert: Empty message returned
        assert result["message"] == "You have no travel partners yet."

        # Assert: Repository returns empty list
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 0


class TestScenarioAddDuplicatePartner:
    """Scenario: User attempts to add a partner that already exists."""

    def test_scenario_add_duplicate_partner(self, beancount_adapter, session_manager):
        """Test adding a duplicate partner returns error.

        Setup: Add partner "Alice"
        Verifies:
        - Error message returned: "Partner 'Alice' already exists."
        - No duplicate entry created in ledger
        - Data integrity maintained
        """
        # Setup: Add partner first
        beancount_adapter.add_partner(Partner("Alice"))
        assert beancount_adapter.partner_exists("Alice")

        ledger_path = session_manager.get_ledger_path()
        initial_content = ledger_path.read_text()

        # Act: Try to add duplicate partner through tool
        result = partners("add", "Alice", repository=beancount_adapter)

        # Assert: Tool returns error
        assert result["success"] is False
        assert "already exists" in result["error"]
        assert result["error"] == "Partner 'Alice' already exists."

        # Assert: Partner still exists (unchanged)
        assert beancount_adapter.partner_exists("Alice")

        # Assert: No duplicate entries in ledger
        from beancount.core.data import Open

        open_entries = _get_all_entries_of_type(ledger_path, Open)
        alice_entries = [e for e in open_entries if "Alice" in e.account]
        assert len(alice_entries) == 1

        # Assert: Ledger unchanged (no new directives written)
        final_content = ledger_path.read_text()
        assert initial_content == final_content

        # Assert: Data integrity - only one partner
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 1
        assert partner_list[0].name == "Alice"


class TestScenarioRemoveNonexistentPartner:
    """Scenario: User attempts to remove a partner that doesn't exist."""

    def test_scenario_remove_nonexistent_partner(
        self, beancount_adapter, session_manager
    ):
        """Test removing a non-existent partner returns error.

        Verifies:
        - Error message returned: "Partner 'Bob' does not exist."
        - No changes to ledger
        - Graceful error handling
        """
        # Setup: Ensure no partner exists
        assert not beancount_adapter.partner_exists("Bob")

        ledger_path = session_manager.get_ledger_path()
        initial_content = ledger_path.read_text()

        # Act: Try to remove non-existent partner through tool
        result = partners("remove", "Bob", repository=beancount_adapter)

        # Assert: Tool returns error
        assert result["success"] is False
        assert "does not exist" in result["error"]
        assert result["error"] == "Partner 'Bob' does not exist."

        # Assert: Partner still doesn't exist
        assert not beancount_adapter.partner_exists("Bob")

        # Assert: Ledger unchanged (no new directives written)
        final_content = ledger_path.read_text()
        assert initial_content == final_content

        # Assert: No entries for non-existent partner
        from beancount.core.data import Close

        close_entries = _get_all_entries_of_type(ledger_path, Close)
        bob_entries = [e for e in close_entries if "Bob" in e.account]
        assert len(bob_entries) == 0

        # Assert: Partner list still empty
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 0

    def test_scenario_remove_nonexistent_partner_with_existing_partners(
        self, beancount_adapter
    ):
        """Test removing non-existent partner when other partners exist.

        Verifies:
        - Error message still returned
        - Existing partners unaffected
        """
        # Setup: Add some partners
        beancount_adapter.add_partner(Partner("Alice"))
        beancount_adapter.add_partner(Partner("Charlie"))

        # Act: Try to remove non-existent partner
        result = partners("remove", "Bob", repository=beancount_adapter)

        # Assert: Error returned
        assert result["success"] is False
        assert "Bob" in result["error"]

        # Assert: Existing partners unaffected
        partner_list = beancount_adapter.list_partners()
        partner_names = {p.name for p in partner_list}
        assert partner_names == {"Alice", "Charlie"}
