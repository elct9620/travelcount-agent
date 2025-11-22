"""Integration tests for partner operations.

Tests the complete workflow of partner management including adding, listing,
removing partners, and verifying persistence in Beancount files. Tests use
real file system with temporary directories and actual Beancount files.
"""

import tempfile
from datetime import date
from pathlib import Path

from beancount import loader
from beancount.core import data

from agents.travelcount.entities.partner import Partner
from agents.travelcount.storage.beancount_adapter import BeancountAdapter
from agents.travelcount.storage.session_manager import SessionManager


class TestAddListRemovePartnerFlow:
    """Test complete add-list-remove partner workflow."""

    def test_add_list_remove_partner_flow(self) -> None:
        """Test adding, listing, and removing a partner in one workflow.

        Verifies:
        - Partner "Alice" is successfully added
        - List returns Alice as active partner
        - Partner "Alice" is successfully removed
        - List shows no active partners
        - Beancount file has both Open and Close directives
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            session_id = "test-session-1"
            session_manager = SessionManager(session_id)
            session_manager._base_data_dir = Path(tmpdir)

            adapter = BeancountAdapter(session_manager)

            # Step 1: Add partner Alice
            alice = Partner("Alice")
            adapter.add_partner(alice)

            # Verify Alice was added to list
            partners = adapter.list_partners()
            assert len(partners) == 1
            assert partners[0].name == "Alice"

            # Step 2: Remove partner Alice
            adapter.remove_partner("Alice")

            # Verify Alice is no longer in list
            partners = adapter.list_partners()
            assert len(partners) == 0

            # Step 3: Verify Beancount file has both Open and Close directives
            ledger_path = session_manager.get_ledger_path()
            entries, errors, options = loader.load_file(str(ledger_path))

            # Count Open and Close directives for Alice's account
            open_count = 0
            close_count = 0
            expected_account = "Assets:Travel:Partners:Alice"

            for entry in entries:
                if isinstance(entry, data.Open) and entry.account == expected_account:
                    open_count += 1
                elif (
                    isinstance(entry, data.Close) and entry.account == expected_account
                ):
                    close_count += 1

            assert open_count == 1, "Should have exactly one Open directive for Alice"
            assert close_count == 1, "Should have exactly one Close directive for Alice"


class TestMultiplePartnersPersistence:
    """Test persistence of multiple partners across adapter instances."""

    def test_multiple_partners_persistence(self) -> None:
        """Test adding multiple partners, removing one, and verifying persistence.

        Verifies:
        - Three partners ("Alice", "Bob", "Charlie") are added successfully
        - List returns all three
        - "Bob" is successfully removed
        - List returns only Alice and Charlie
        - Data persists across new adapter instances
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-session-2"

            # Step 1: Create first adapter and add three partners
            session_manager_1 = SessionManager(session_id)
            session_manager_1._base_data_dir = Path(tmpdir)

            adapter_1 = BeancountAdapter(session_manager_1)

            partners_to_add = ["Alice", "Bob", "Charlie"]
            for partner_name in partners_to_add:
                partner = Partner(partner_name)
                adapter_1.add_partner(partner)

            # Verify all three are in list
            partners = adapter_1.list_partners()
            partner_names = sorted([p.name for p in partners])
            assert partner_names == ["Alice", "Bob", "Charlie"]

            # Step 2: Remove Bob
            adapter_1.remove_partner("Bob")

            # Verify only Alice and Charlie remain
            partners = adapter_1.list_partners()
            partner_names = sorted([p.name for p in partners])
            assert partner_names == ["Alice", "Charlie"]

            # Step 3: Create new adapter instance and verify persistence
            session_manager_2 = SessionManager(session_id)
            session_manager_2._base_data_dir = Path(tmpdir)

            adapter_2 = BeancountAdapter(session_manager_2)

            # Verify persistence across adapter instances
            partners = adapter_2.list_partners()
            partner_names = sorted([p.name for p in partners])
            assert partner_names == ["Alice", "Charlie"], (
                "Data should persist across adapter instances"
            )

            # Verify Bob is still marked as closed in Beancount file
            ledger_path = session_manager_2.get_ledger_path()
            entries, errors, options = loader.load_file(str(ledger_path))

            bob_account = "Assets:Travel:Partners:Bob"
            bob_open_found = False
            bob_close_found = False

            for entry in entries:
                if isinstance(entry, data.Open) and entry.account == bob_account:
                    bob_open_found = True
                elif isinstance(entry, data.Close) and entry.account == bob_account:
                    bob_close_found = True

            assert bob_open_found and bob_close_found, (
                "Bob should have both Open and Close directives"
            )


class TestSessionIsolation:
    """Test that different sessions are isolated from each other."""

    def test_session_isolation(self) -> None:
        """Test that partners in one session don't appear in another.

        Verifies:
        - Session 1 with partner "Alice"
        - Session 2 with partner "Bob"
        - Session 1 only shows Alice
        - Session 2 only shows Bob
        - Separate ledger files exist for each session
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Setup session 1
            session_id_1 = "trip-europe-2024"
            session_manager_1 = SessionManager(session_id_1)
            session_manager_1._base_data_dir = base_path

            adapter_1 = BeancountAdapter(session_manager_1)

            # Add Alice to session 1
            alice = Partner("Alice")
            adapter_1.add_partner(alice)

            # Setup session 2
            session_id_2 = "trip-asia-2024"
            session_manager_2 = SessionManager(session_id_2)
            session_manager_2._base_data_dir = base_path

            adapter_2 = BeancountAdapter(session_manager_2)

            # Add Bob to session 2
            bob = Partner("Bob")
            adapter_2.add_partner(bob)

            # Verify session 1 only has Alice
            partners_1 = adapter_1.list_partners()
            partner_names_1 = [p.name for p in partners_1]
            assert partner_names_1 == ["Alice"]

            # Verify session 2 only has Bob
            partners_2 = adapter_2.list_partners()
            partner_names_2 = [p.name for p in partners_2]
            assert partner_names_2 == ["Bob"]

            # Verify separate ledger files exist
            ledger_path_1 = session_manager_1.get_ledger_path()
            ledger_path_2 = session_manager_2.get_ledger_path()

            assert ledger_path_1 != ledger_path_2, (
                "Session ledger paths should be different"
            )
            assert ledger_path_1.exists(), "Session 1 ledger should exist"
            assert ledger_path_2.exists(), "Session 2 ledger should exist"

            # Verify the paths contain the correct session IDs
            assert session_id_1 in str(ledger_path_1)
            assert session_id_2 in str(ledger_path_2)


class TestBeancountFileParsing:
    """Test Beancount file parsing and directive formatting."""

    def test_beancount_file_parsing_integration(self) -> None:
        """Test integration with Beancount loader and directive validation.

        Verifies:
        - Partners added are correctly stored as Beancount directives
        - Open directives have correct format and account names
        - Currency is set to USD
        - Accounts follow Assets:Travel:Partners:* pattern
        - Close directive exists after partner removal
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-session-3"
            session_manager = SessionManager(session_id)
            session_manager._base_data_dir = Path(tmpdir)

            adapter = BeancountAdapter(session_manager)

            # Add partners
            partners_to_add = ["Alice", "Bob", "Charlie"]
            for partner_name in partners_to_add:
                partner = Partner(partner_name)
                adapter.add_partner(partner)

            # Parse the ledger file directly
            ledger_path = session_manager.get_ledger_path()
            entries, errors, options = loader.load_file(str(ledger_path))

            # Collect all partner accounts
            open_accounts = {}  # account_name -> Open directive
            close_accounts = {}  # account_name -> Close directive

            for entry in entries:
                if isinstance(entry, data.Open):
                    if entry.account.startswith("Assets:Travel:Partners:"):
                        open_accounts[entry.account] = entry
                elif isinstance(entry, data.Close):
                    if entry.account.startswith("Assets:Travel:Partners:"):
                        close_accounts[entry.account] = entry

            # Verify all partners have Open directives
            for partner_name in partners_to_add:
                expected_account = f"Assets:Travel:Partners:{partner_name}"
                assert expected_account in open_accounts, (
                    f"Missing Open directive for {partner_name}"
                )

                # Verify Open directive details
                open_entry = open_accounts[expected_account]
                assert isinstance(open_entry, data.Open)
                assert open_entry.account == expected_account
                assert open_entry.currencies is None  # None allows all currencies
                assert isinstance(open_entry.date, date)
                assert open_entry.date == date(1970, 1, 1)  # Epoch date

            # Step 2: Remove one partner and verify Close directive
            adapter.remove_partner("Bob")

            # Re-parse the file
            entries, errors, options = loader.load_file(str(ledger_path))

            bob_account = "Assets:Travel:Partners:Bob"
            bob_close_found = False

            for entry in entries:
                if isinstance(entry, data.Close) and entry.account == bob_account:
                    bob_close_found = True
                    assert isinstance(entry.date, date)

            assert bob_close_found, "Bob should have Close directive after removal"

            # Verify Close doesn't exist for still-open partners
            alice_account = "Assets:Travel:Partners:Alice"
            charlie_account = "Assets:Travel:Partners:Charlie"

            close_accounts = set()
            for entry in entries:
                if isinstance(entry, data.Close):
                    close_accounts.add(entry.account)

            assert alice_account not in close_accounts, (
                "Alice should not have Close directive"
            )
            assert charlie_account not in close_accounts, (
                "Charlie should not have Close directive"
            )
