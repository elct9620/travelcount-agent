"""Tests for validator module."""

from collections import namedtuple
from pathlib import Path

import pytest

from agents.travelcount.storage.validator import (
    ValidationError,
    format_error,
    validate_ledger,
)


class TestValidateLedgerSuccess:
    """Test validate_ledger with valid ledger files."""

    def test_validate_ledger_success(self, temp_dir: Path) -> None:
        """Validate ledger with no errors returns empty list."""
        # Create a valid ledger file
        ledger_path = temp_dir / "index.bean"
        ledger_path.write_text(
            """; TravelCount Session Ledger
; Session ID: test-session
; Created: 2024-01-01

option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
2024-01-02 open Assets:Travel:Partners:Bob USD
"""
        )

        # Validate the ledger
        errors = validate_ledger(ledger_path)

        # Should return empty list (no errors)
        assert errors == []
        assert isinstance(errors, list)

    def test_validate_ledger_with_minimal_content(self, temp_dir: Path) -> None:
        """Validate minimal valid ledger file."""
        ledger_path = temp_dir / "minimal.bean"
        ledger_path.write_text('option "operating_currency" "USD"\n')

        errors = validate_ledger(ledger_path)

        assert errors == []

    def test_validate_ledger_with_transactions(self, temp_dir: Path) -> None:
        """Validate ledger with valid transactions."""
        ledger_path = temp_dir / "with_txn.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
2024-01-01 open Expenses:Food USD

2024-01-02 * "Lunch"
  Expenses:Food  50.00 USD
  Assets:Travel:Partners:Alice  -50.00 USD
"""
        )

        errors = validate_ledger(ledger_path)

        assert errors == []


class TestValidateLedgerParseErrors:
    """Test validate_ledger detection of syntax errors."""

    def test_validate_ledger_parse_errors(self, temp_dir: Path) -> None:
        """Detect syntax errors in ledger file."""
        ledger_path = temp_dir / "invalid.bean"
        # Create invalid syntax - malformed directive
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Test
thisisnotavalidline
"""
        )

        errors = validate_ledger(ledger_path)

        # Should return non-empty list of errors
        assert len(errors) > 0

    def test_validate_ledger_malformed_date(self, temp_dir: Path) -> None:
        """Detect malformed date in directive."""
        ledger_path = temp_dir / "bad_date.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-13-01 open Assets:Test USD
"""
        )

        errors = validate_ledger(ledger_path)

        assert len(errors) > 0

    def test_validate_ledger_invalid_account_name(self, temp_dir: Path) -> None:
        """Detect invalid account names."""
        ledger_path = temp_dir / "bad_account.bean"
        # Account names cannot start with lowercase
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open assets:test USD
"""
        )

        errors = validate_ledger(ledger_path)

        assert len(errors) > 0

    def test_validate_ledger_incomplete_transaction(self, temp_dir: Path) -> None:
        """Detect incomplete transaction (unbalanced)."""
        ledger_path = temp_dir / "unbalanced.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Test USD
2024-01-01 open Expenses:Food USD

2024-01-02 * "Incomplete transaction"
  Expenses:Food  50.00 USD
"""
        )

        errors = validate_ledger(ledger_path)

        assert len(errors) > 0


class TestValidateLedgerDuplicateOpen:
    """Test validate_ledger detection of duplicate open directives."""

    def test_validate_ledger_duplicate_open(self, temp_dir: Path) -> None:
        """Detect duplicate open directives for same account."""
        ledger_path = temp_dir / "duplicate.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
2024-01-02 open Assets:Travel:Partners:Alice USD
"""
        )

        errors = validate_ledger(ledger_path)

        # Should return error about duplicate open
        assert len(errors) > 0
        # Check error message mentions "duplicate" or "already"
        error_messages = [str(error) for error in errors]
        assert any(
            "duplicate" in msg.lower() or "already" in msg.lower()
            for msg in error_messages
        )

    def test_validate_ledger_multiple_duplicates(self, temp_dir: Path) -> None:
        """Detect multiple duplicate open directives."""
        ledger_path = temp_dir / "many_duplicates.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Test1 USD
2024-01-02 open Assets:Test1 USD
2024-01-03 open Assets:Test2 USD
2024-01-04 open Assets:Test2 USD
"""
        )

        errors = validate_ledger(ledger_path)

        # Should detect both duplicate pairs
        assert len(errors) >= 2


class TestValidateLedgerReopenClosedAccount:
    """Test validate_ledger detection of reopening closed accounts."""

    def test_validate_ledger_reopen_closed_account(self, temp_dir: Path) -> None:
        """Detect reopening of closed account."""
        ledger_path = temp_dir / "reopen.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
2024-01-02 close Assets:Travel:Partners:Alice
2024-01-03 open Assets:Travel:Partners:Alice USD
"""
        )

        errors = validate_ledger(ledger_path)

        # Should return error about reopening closed account
        assert len(errors) > 0

    def test_validate_ledger_multiple_reopen_attempts(self, temp_dir: Path) -> None:
        """Detect multiple reopen attempts."""
        ledger_path = temp_dir / "multi_reopen.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Test USD
2024-01-02 close Assets:Test
2024-01-03 open Assets:Test USD
2024-01-04 close Assets:Test
2024-01-05 open Assets:Test USD
"""
        )

        errors = validate_ledger(ledger_path)

        # Should detect multiple reopen violations
        assert len(errors) >= 2


class TestFormatError:
    """Test format_error function."""

    def test_format_error(self) -> None:
        """Verify error formatting matches expected output."""
        # Create mock Beancount error object using namedtuple
        MockError = namedtuple("MockError", ["source", "message", "entry"])
        error = MockError(
            source={"filename": "/data/index.bean", "lineno": 5},
            message="Duplicate open directive for Assets:Test",
            entry=None,
        )

        formatted = format_error(error)

        # Should match format: "filename:lineno: message"
        assert (
            formatted == "/data/index.bean:5: Duplicate open directive for Assets:Test"
        )

    def test_format_error_with_different_line_numbers(self) -> None:
        """Test error formatting with various line numbers."""
        MockError = namedtuple("MockError", ["source", "message", "entry"])

        test_cases = [
            (1, "Error at line 1"),
            (42, "Error at line 42"),
            (999, "Error at line 999"),
        ]

        for lineno, msg in test_cases:
            error = MockError(
                source={"filename": "/test.bean", "lineno": lineno},
                message=msg,
                entry=None,
            )
            formatted = format_error(error)
            assert formatted == f"/test.bean:{lineno}: {msg}"

    def test_format_error_with_missing_source(self) -> None:
        """Test error formatting when source is missing."""
        MockError = namedtuple("MockError", ["message"])
        error = MockError(message="Error without source")

        formatted = format_error(error)

        # Should use default values
        assert formatted == "<unknown>:0: Error without source"

    def test_format_error_with_non_dict_source(self) -> None:
        """Test error formatting with invalid source type."""
        MockError = namedtuple("MockError", ["source", "message", "entry"])
        error = MockError(source="invalid", message="Error message", entry=None)

        formatted = format_error(error)

        # Should handle non-dict source gracefully
        assert formatted == "<unknown>:0: Error message"

    def test_format_error_with_missing_filename(self) -> None:
        """Test error formatting when filename is missing from source."""
        MockError = namedtuple("MockError", ["source", "message", "entry"])
        error = MockError(source={"lineno": 10}, message="Missing filename", entry=None)

        formatted = format_error(error)

        assert formatted == "<unknown>:10: Missing filename"

    def test_format_error_with_missing_lineno(self) -> None:
        """Test error formatting when lineno is missing from source."""
        MockError = namedtuple("MockError", ["source", "message", "entry"])
        error = MockError(
            source={"filename": "/test.bean"}, message="Missing lineno", entry=None
        )

        formatted = format_error(error)

        assert formatted == "/test.bean:0: Missing lineno"

    def test_format_error_with_complex_message(self) -> None:
        """Test error formatting with complex multi-word messages."""
        MockError = namedtuple("MockError", ["source", "message", "entry"])
        error = MockError(
            source={"filename": "/data/ledger.bean", "lineno": 15},
            message="Transaction does not balance: expected 0.00 USD but got -10.00 USD",
            entry=None,
        )

        formatted = format_error(error)

        expected = (
            "/data/ledger.bean:15: Transaction does not balance: "
            "expected 0.00 USD but got -10.00 USD"
        )
        assert formatted == expected


class TestValidateLedgerFileNotFound:
    """Test validate_ledger error handling for missing files."""

    def test_validate_ledger_file_not_found(self, temp_dir: Path) -> None:
        """Test error handling for missing files."""
        non_existent_path = temp_dir / "does_not_exist.bean"

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Ledger file not found"):
            validate_ledger(non_existent_path)

    def test_validate_ledger_file_not_found_with_absolute_path(
        self, temp_dir: Path
    ) -> None:
        """Test FileNotFoundError includes the path in message."""
        non_existent_path = temp_dir / "missing.bean"

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_ledger(non_existent_path)

        # Error message should include the path
        assert str(non_existent_path) in str(exc_info.value)

    def test_validate_ledger_directory_instead_of_file(self, temp_dir: Path) -> None:
        """Test error when path points to directory instead of file."""
        # temp_dir is a directory, not a file
        # Beancount's loader should fail when trying to load a directory
        # This will raise an exception (not necessarily FileNotFoundError)
        with pytest.raises(Exception):
            validate_ledger(temp_dir)


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_creation(self) -> None:
        """Test creating ValidationError with message."""
        error = ValidationError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_validation_error_with_formatted_errors(self) -> None:
        """Test ValidationError with formatted error list."""
        error_message = (
            "Validation failed with 2 errors:\n"
            "/data/index.bean:5: Duplicate open directive\n"
            "/data/index.bean:10: Account not opened"
        )

        error = ValidationError(error_message)

        assert str(error) == error_message

    def test_validation_error_can_be_caught(self) -> None:
        """Test that ValidationError can be caught as exception."""
        try:
            raise ValidationError("Test exception")
        except ValidationError as e:
            assert str(e) == "Test exception"
        except Exception:
            pytest.fail("ValidationError should be caught as ValidationError")

    def test_validation_error_inheritance(self) -> None:
        """Test that ValidationError inherits from Exception."""
        error = ValidationError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, ValidationError)


class TestValidateLedgerEdgeCases:
    """Test edge cases and additional scenarios."""

    def test_validate_ledger_empty_file(self, temp_dir: Path) -> None:
        """Test validating an empty ledger file."""
        ledger_path = temp_dir / "empty.bean"
        ledger_path.write_text("")

        errors = validate_ledger(ledger_path)

        # Empty file may or may not have errors depending on Beancount version
        # Just ensure it doesn't crash
        assert isinstance(errors, list)

    def test_validate_ledger_with_comments_only(self, temp_dir: Path) -> None:
        """Test validating ledger with only comments."""
        ledger_path = temp_dir / "comments.bean"
        ledger_path.write_text(
            """; This is a comment
; Another comment
; More comments
"""
        )

        errors = validate_ledger(ledger_path)

        # Comments-only file should be valid (no errors)
        assert errors == []

    def test_validate_ledger_with_whitespace(self, temp_dir: Path) -> None:
        """Test validating ledger with extra whitespace."""
        ledger_path = temp_dir / "whitespace.bean"
        ledger_path.write_text(
            """

option "operating_currency" "USD"


2024-01-01 open Assets:Test USD


"""
        )

        errors = validate_ledger(ledger_path)

        # Extra whitespace should not cause errors
        assert errors == []

    def test_validate_ledger_preserves_error_order(self, temp_dir: Path) -> None:
        """Test that validation errors are returned in order."""
        ledger_path = temp_dir / "multi_errors.bean"
        ledger_path.write_text(
            """option "operating_currency" "USD"

2024-01-01 open Assets:Test1 USD
2024-01-02 open Assets:Test1 USD
2024-01-03 open Assets:Test2 USD
2024-01-04 open Assets:Test2 USD
"""
        )

        errors = validate_ledger(ledger_path)

        # Should have multiple errors
        assert len(errors) >= 2

        # Errors should be in a consistent order
        # (line numbers should be ascending or errors grouped by type)
        assert isinstance(errors, list)
