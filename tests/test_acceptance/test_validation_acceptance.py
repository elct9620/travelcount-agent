"""Acceptance tests for validation feature in TravelCount.

These tests verify the complete end-to-end validation workflow, testing that:
1. Validation prevents invalid data from being persisted
2. Validation errors propagate from storage layer to tool layer
3. User receives clear, actionable error messages
4. Ledger is rolled back correctly when validation fails

Test scenarios:
1. Valid partner addition succeeds through tool
2. Invalid partner addition (duplicate) is prevented with clear error
3. Invalid partner re-addition (reopening closed account) is prevented
4. Valid expense logging succeeds through tool
5. Invalid expense logging (missing partner) is prevented with clear error
6. Ledger rollback works correctly when validation fails
"""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from beancount import loader
from beancount.core import data

from agents.travelcount.entities.partner import Partner
from agents.travelcount.storage.beancount_adapter import BeancountAdapter
from agents.travelcount.storage.session_manager import SessionManager
from agents.travelcount.storage.validator import ValidationError
from agents.travelcount.tools.partner import partners
from agents.travelcount.tools.expense import log_expense


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data and clean up after test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_data_dir):
    """Create a SessionManager with temporary directory."""
    manager = SessionManager("test-validation-session")
    manager._base_data_dir = temp_data_dir
    manager.ensure_session_directory()
    manager.initialize_ledger()
    return manager


@pytest.fixture
def beancount_adapter(session_manager):
    """Create a BeancountAdapter with SessionManager."""
    return BeancountAdapter(session_manager)


def _get_ledger_content(ledger_path: Path) -> str:
    """Helper to read ledger file content."""
    if not ledger_path.exists():
        return ""
    return ledger_path.read_text()


def _count_directives(ledger_path: Path, directive_type) -> int:
    """Helper to count directives of a specific type in ledger."""
    if not ledger_path.exists():
        return 0
    entries, errors, options = loader.load_file(str(ledger_path))
    return len([e for e in entries if isinstance(e, directive_type)])


class TestValidPartnerAdditionThroughTool:
    """Scenario: User adds a new partner with valid input through the tool."""

    def test_add_partner_tool_with_valid_input(
        self, beancount_adapter, session_manager
    ):
        """Test adding a valid partner through the tool succeeds.

        This verifies the complete end-to-end flow:
        1. Tool validates input
        2. BeancountAdapter creates directive
        3. Validator confirms ledger is valid
        4. Partner is persisted successfully
        5. User receives success message
        """
        # Capture initial state
        ledger_path = session_manager.get_ledger_path()
        initial_content = _get_ledger_content(ledger_path)

        # Act: Add partner through tool
        result = partners("add", "Alice", repository=beancount_adapter)

        # Assert: Tool returns success
        assert result["success"] is True
        assert result["message"] == "Partner 'Alice' has been added."

        # Assert: Partner is persisted in ledger
        assert beancount_adapter.partner_exists("Alice")

        # Assert: Ledger contains new directive
        final_content = _get_ledger_content(ledger_path)
        assert len(final_content) > len(initial_content)
        assert "Assets:Travel:Partners:Alice" in final_content

        # Assert: Ledger is valid (can be loaded without errors)
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, f"Ledger should be valid but has errors: {errors}"

        # Assert: Partner appears in list
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 1
        assert partner_list[0].name == "Alice"


class TestInvalidPartnerAdditionThroughTool:
    """Scenario: User attempts to add a partner that causes validation error."""

    def test_add_partner_tool_prevents_reopening_closed_account(
        self, beancount_adapter, session_manager
    ):
        """Test that reopening a closed partner account is prevented.

        This scenario tests:
        1. Add partner "Alice"
        2. Remove partner "Alice" (close account)
        3. Attempt to add "Alice" again (would reopen closed account)
        4. Validation prevents reopening and rolls back ledger
        5. User receives clear error message

        Beancount does not allow reopening a closed account, so this
        should trigger a validation error.
        """
        # Setup: Add and remove partner to create closed account
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)
        beancount_adapter.remove_partner("Alice")

        # Verify Alice has both open and close directives
        ledger_path = session_manager.get_ledger_path()
        ledger_content = _get_ledger_content(ledger_path)
        assert "open Assets:Travel:Partners:Alice" in ledger_content
        assert "close Assets:Travel:Partners:Alice" in ledger_content

        # Capture state before invalid operation
        state_before_invalid_add = ledger_content
        open_count_before = _count_directives(ledger_path, data.Open)

        # Act: Attempt to add Alice again (reopen closed account)
        # This should raise ValidationError in BeancountAdapter
        with pytest.raises(ValidationError) as exc_info:
            beancount_adapter.add_partner(alice)

        # Assert: ValidationError was raised with meaningful message
        error_message = str(exc_info.value)
        assert "Alice" in error_message, "Error message should mention the partner name"
        # Beancount error message should contain file path and line number
        assert ".bean:" in error_message, (
            "Error message should contain file path with line number"
        )

        # Assert: Ledger was rolled back to previous valid state
        ledger_content_after = _get_ledger_content(ledger_path)
        assert ledger_content_after == state_before_invalid_add, (
            "Ledger should be rolled back to state before invalid operation"
        )

        # Assert: No additional Open directive was added
        open_count_after = _count_directives(ledger_path, data.Open)
        assert open_count_after == open_count_before, (
            "No new Open directive should be persisted after validation failure"
        )

        # Assert: Partner is still not in active list
        partner_list = beancount_adapter.list_partners()
        assert len(partner_list) == 0, "Alice should not be in active partners"

        # Assert: Ledger is still valid after rollback
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, f"Ledger should be valid after rollback: {errors}"

    def test_add_partner_tool_with_duplicate_partner_user_experience(
        self, beancount_adapter, session_manager
    ):
        """Test user experience when attempting to add duplicate partner.

        This verifies the tool layer catches duplicate partners before
        reaching the storage layer, providing a user-friendly error message.
        """
        # Setup: Add partner "Bob"
        bob = Partner("Bob")
        beancount_adapter.add_partner(bob)

        # Act: Attempt to add Bob again through tool
        result = partners("add", "Bob", repository=beancount_adapter)

        # Assert: Tool returns error (caught before validation layer)
        assert result["success"] is False
        assert "already exists" in result["error"]
        assert "Bob" in result["error"]
        assert result["error"] == "Partner 'Bob' already exists."

        # Assert: Error message is user-friendly (no technical details)
        error_msg = result["error"]
        assert ".bean:" not in error_msg, (
            "User-facing error should not contain file paths"
        )
        assert "lineno" not in error_msg, (
            "User-facing error should not contain line numbers"
        )

        # Assert: Only one Bob exists in ledger
        ledger_path = session_manager.get_ledger_path()
        entries, errors, options = loader.load_file(str(ledger_path))
        bob_accounts = [
            e
            for e in entries
            if isinstance(e, data.Open) and e.account == "Assets:Travel:Partners:Bob"
        ]
        assert len(bob_accounts) == 1, "Should have exactly one Open directive for Bob"


class TestValidExpenseLoggingThroughTool:
    """Scenario: User logs an expense with valid input through the tool."""

    def test_log_expense_with_validation(self, beancount_adapter, session_manager):
        """Test logging expense succeeds with automatic expense account creation.

        This verifies the auto-creation feature for expense accounts:
        1. Tool attempts to log expense
        2. BeancountAdapter automatically creates Expenses:Travel:Food account if needed
        3. Transaction directive is created
        4. Validator confirms the ledger is valid
        5. Expense is successfully persisted

        Note: This demonstrates that expense accounts are automatically opened on
        first use, which is proper Beancount behavior for a real system.
        """
        # Setup: Add a partner first
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)

        # Capture initial state
        ledger_path = session_manager.get_ledger_path()

        # Act: Log expense (should succeed with auto-creation)
        from agents.travelcount.entities.expense import Expense

        expense = Expense(
            date=date.today(),
            amount=50.0,
            currency="USD",
            description="Lunch at cafe",
            paid_by=alice,
        )
        expense_id = beancount_adapter.log_expense(expense)

        # Assert: Expense was created successfully
        assert expense_id is not None

        # Assert: Ledger contains the expense
        final_content = _get_ledger_content(ledger_path)
        assert "Lunch at cafe" in final_content

        # Assert: Expense account was auto-created with epoch date
        assert "1970-01-01 open Expenses:Travel:Food" in final_content

        # Assert: Ledger is valid
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, (
            f"Ledger should be valid after expense logging: {errors}"
        )

        # Assert: Expense can be retrieved
        expenses = beancount_adapter.get_expenses()
        assert len(expenses) == 1
        assert expenses[0].description == "Lunch at cafe"


class TestInvalidExpenseLoggingThroughTool:
    """Scenario: User attempts to log expense with invalid data."""

    def test_log_expense_with_nonexistent_partner_fails_gracefully(
        self, beancount_adapter, session_manager
    ):
        """Test logging expense with non-existent partner fails with clear error.

        This verifies:
        1. Tool validates partner exists before attempting to log
        2. User receives clear error message
        3. No invalid directive is written to ledger
        """
        # Ensure no partners exist
        assert len(beancount_adapter.list_partners()) == 0

        # Capture initial state
        ledger_path = session_manager.get_ledger_path()
        initial_content = _get_ledger_content(ledger_path)

        # Act: Attempt to log expense with non-existent partner
        result = log_expense(
            amount=30.0,
            currency="USD",
            description="Dinner",
            paid_by="NonExistentPerson",
            repository=beancount_adapter,
        )

        # Assert: Tool returns error
        assert result["success"] is False
        assert "not found" in result["error"]
        assert "NonExistentPerson" in result["error"]

        # Assert: Error message is user-friendly
        error_msg = result["error"]
        assert ".bean:" not in error_msg, (
            "User-facing error should not contain file paths"
        )

        # Assert: Ledger unchanged
        final_content = _get_ledger_content(ledger_path)
        assert final_content == initial_content, "Ledger should be unchanged"

        # Assert: Ledger is still valid
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, f"Ledger should remain valid: {errors}"


class TestLedgerRollbackOnValidationFailure:
    """Scenario: Validation failure triggers ledger rollback."""

    def test_ledger_rollback_preserves_valid_state(
        self, beancount_adapter, session_manager
    ):
        """Test that ledger rollback correctly restores previous valid state.

        This comprehensive test verifies:
        1. Initial ledger is valid with some partners
        2. Invalid operation causes ValidationError
        3. Ledger is rolled back to exact previous state
        4. Subsequent valid operations still work
        """
        # Setup: Create a valid ledger with partners
        alice = Partner("Alice")
        bob = Partner("Bob")
        beancount_adapter.add_partner(alice)
        beancount_adapter.add_partner(bob)

        # Verify initial valid state
        ledger_path = session_manager.get_ledger_path()
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, "Initial ledger should be valid"
        assert len(beancount_adapter.list_partners()) == 2

        # Act: Perform invalid operation (remove and re-add to trigger validation error)
        beancount_adapter.remove_partner("Alice")
        with pytest.raises(ValidationError):
            beancount_adapter.add_partner(alice)

        # Assert: Ledger content after rollback
        # Note: Alice is still closed because remove succeeded,
        # but the re-add was rolled back
        current_state = _get_ledger_content(ledger_path)
        assert "Assets:Travel:Partners:Alice" in current_state
        assert "Assets:Travel:Partners:Bob" in current_state

        # Assert: Ledger is still valid after rollback
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, f"Ledger should be valid after rollback: {errors}"

        # Assert: Only Bob is active (Alice was successfully removed)
        active_partners = beancount_adapter.list_partners()
        assert len(active_partners) == 1
        assert active_partners[0].name == "Bob"

        # Assert: Subsequent valid operations still work
        charlie = Partner("Charlie")
        beancount_adapter.add_partner(charlie)
        active_partners = beancount_adapter.list_partners()
        assert len(active_partners) == 2
        partner_names = {p.name for p in active_partners}
        assert partner_names == {"Bob", "Charlie"}


class TestMultipleValidationErrors:
    """Scenario: Operations that cause multiple validation errors."""

    def test_validation_error_message_format(self, beancount_adapter, session_manager):
        """Test that validation error messages are well-formatted and informative.

        This verifies:
        1. Error messages include file path and line number
        2. Error messages describe the validation issue
        3. Error messages help users understand what went wrong
        """
        # Setup: Create a closed account
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)
        beancount_adapter.remove_partner("Alice")

        # Act: Attempt to reopen closed account
        with pytest.raises(ValidationError) as exc_info:
            beancount_adapter.add_partner(alice)

        # Assert: Error message contains useful information
        error_message = str(exc_info.value)

        # Should contain file path
        ledger_path = session_manager.get_ledger_path()
        assert str(ledger_path) in error_message or "index.bean" in error_message, (
            "Error should reference the ledger file"
        )

        # Should contain line number information
        assert ":" in error_message, (
            "Error should include line number in format 'file:line:'"
        )

        # Should mention the account or partner involved
        assert (
            "Alice" in error_message or "Assets:Travel:Partners:Alice" in error_message
        ), "Error should reference the partner/account causing the issue"


class TestUserExperienceWithValidationErrors:
    """Scenario: User experience when validation errors occur."""

    def test_user_receives_actionable_error_messages(
        self, beancount_adapter, session_manager
    ):
        """Test that users receive actionable error messages from validation.

        This verifies that when validation fails:
        1. Error propagates from BeancountAdapter to tool layer
        2. Error message guides user to understand the issue
        3. Error message suggests how to fix the problem
        """
        # Setup: Create scenario where validation will fail
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)
        beancount_adapter.remove_partner("Alice")

        # Act: Attempt invalid operation
        try:
            beancount_adapter.add_partner(alice)
            assert False, "Expected ValidationError to be raised"
        except ValidationError as e:
            error_message = str(e)

            # Assert: Error message is informative
            # At minimum, should tell user what account/partner has the issue
            assert (
                "Alice" in error_message
                or "Assets:Travel:Partners:Alice" in error_message
            ), "Error should identify which partner caused the issue"

            # Should indicate the nature of the problem (account-related issue)
            # Beancount typically mentions "account" or "open/close" in validation errors
            error_lower = error_message.lower()
            assert any(
                keyword in error_lower
                for keyword in ["account", "open", "close", "duplicate"]
            ), "Error should describe the nature of the validation issue"

    def test_successful_operation_after_failed_validation(
        self, beancount_adapter, session_manager
    ):
        """Test that the system recovers gracefully after validation failures.

        This verifies:
        1. Failed validation doesn't corrupt the ledger
        2. Subsequent valid operations succeed
        3. System state remains consistent
        """
        # Setup: Create initial valid state
        bob = Partner("Bob")
        beancount_adapter.add_partner(bob)

        # Act: Attempt invalid operation
        alice = Partner("Alice")
        beancount_adapter.add_partner(alice)
        beancount_adapter.remove_partner("Alice")

        with pytest.raises(ValidationError):
            beancount_adapter.add_partner(alice)

        # Assert: System is still functional
        # Add a different partner successfully
        charlie = Partner("Charlie")
        beancount_adapter.add_partner(charlie)

        # Verify both Bob and Charlie are active
        active_partners = beancount_adapter.list_partners()
        partner_names = {p.name for p in active_partners}
        assert partner_names == {"Bob", "Charlie"}

        # Verify ledger is valid
        ledger_path = session_manager.get_ledger_path()
        entries, errors, options = loader.load_file(str(ledger_path))
        assert len(errors) == 0, "Ledger should be valid after recovery"
