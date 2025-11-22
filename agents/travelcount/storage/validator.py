"""Validator module for Beancount ledger validation.

This module provides validation functionality for Beancount ledger files,
ensuring data integrity before persisting changes. It wraps Beancount's
validation API to detect parse errors and validation errors, formatting
them into user-friendly error messages.

The validator is used by BeancountAdapter to validate the ledger after
each write operation, ensuring the ledger remains in a valid state at
all times.
"""

from pathlib import Path

from beancount import loader
from beancount.ops import validation


class ValidationError(Exception):
    """Custom exception raised when Beancount ledger validation fails.

    This exception is raised by BeancountAdapter when the ledger file
    contains validation errors. It contains a formatted error message
    with all validation issues found during validation.

    Attributes:
        message: Formatted error message containing all validation issues
    """

    def __init__(self, message: str) -> None:
        """Initialize ValidationError with a formatted error message.

        Args:
            message: Formatted error message describing validation failures
        """
        super().__init__(message)


def format_error(error) -> str:
    """Format a Beancount error object into a readable error message.

    Formats Beancount error objects (ValidationError tuples) into
    user-friendly error messages following the bean-check command
    output format. The format includes the file path, line number,
    and error description.

    Args:
        error: Beancount error object (typically a ValidationError tuple)
               with structure: (source, message, entry)
               where source is a dict with 'filename' and 'lineno' keys

    Returns:
        Formatted error string in the format:
        "/path/to/file.bean:line_number: Error message"

    Example:
        >>> error = ValidationError(
        ...     source={'filename': '/data/index.bean', 'lineno': 5},
        ...     message='Duplicate open directive for Assets:Test',
        ...     entry=...
        ... )
        >>> format_error(error)
        '/data/index.bean:5: Duplicate open directive for Assets:Test'
    """
    # Extract error details from the error object
    # Beancount errors have structure: ValidationError(source, message, entry)
    source = error.source if hasattr(error, "source") else {}
    message = error.message if hasattr(error, "message") else str(error)

    # Get filename and line number from source
    filename = (
        source.get("filename", "<unknown>") if isinstance(source, dict) else "<unknown>"
    )
    lineno = source.get("lineno", 0) if isinstance(source, dict) else 0

    # Format in bean-check style: filename:lineno: message
    return f"{filename}:{lineno}: {message}"


def validate_ledger(ledger_path: Path) -> list:
    """Validate a Beancount ledger file and return all errors found.

    Loads the ledger file using beancount.loader.load_file() to detect
    parse errors, then runs beancount.ops.validation.validate() to check
    for validation errors. All errors are aggregated and returned.

    The function checks for:
    - Parse errors (syntax errors, invalid directives)
    - Validation errors (duplicate accounts, unopened accounts, etc.)

    Args:
        ledger_path: Path to the Beancount ledger file to validate

    Returns:
        List of all validation errors found (both parse and validation errors).
        Returns empty list if validation succeeds.

    Raises:
        FileNotFoundError: If ledger_path does not exist

    Example:
        >>> from pathlib import Path
        >>> ledger_path = Path("data/session-123/index.bean")
        >>> errors = validate_ledger(ledger_path)
        >>> if errors:
        ...     print(f"Found {len(errors)} validation errors")
        ... else:
        ...     print("Ledger is valid")
    """
    # Check if file exists
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger file not found: {ledger_path}")

    # Load the ledger file and collect parse errors
    entries, parse_errors, options_map = loader.load_file(str(ledger_path))

    # Run validation checks to collect validation errors
    validation_errors = validation.validate(entries, options_map)

    # Aggregate all errors (parse errors + validation errors)
    all_errors = list(parse_errors) + list(validation_errors)

    return all_errors
