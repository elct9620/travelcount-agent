"""Expense entity for TravelCount application.

This module defines the Expense domain entity representing a travel expense entry
in shared expense tracking. Follows Clean Architecture principles with self-validating
business logic separated from storage concerns.
"""

import datetime
import hashlib
import re
from decimal import Decimal

from .partner import Partner


class Expense:
    """Represents a travel expense in expense tracking.

    An expense is a record of money spent during travel by a partner.
    This is a domain entity that enforces business rules and validates state.

    Attributes:
        id: Unique identifier generated from expense details
        date: Date when the expense occurred
        amount: The expense amount (must be positive)
        currency: 3-letter uppercase currency code (e.g., "USD", "EUR")
        description: Brief description of the expense
        paid_by: Partner who paid for the expense
    """

    def __init__(
        self,
        date: datetime.date,
        amount: Decimal,
        currency: str,
        description: str,
        paid_by: Partner,
    ) -> None:
        """Initialize an Expense with validated attributes.

        Args:
            date: Date when the expense occurred
            amount: The expense amount (must be positive)
            currency: 3-letter uppercase currency code
            description: Brief description of the expense
            paid_by: Partner who paid for the expense

        Raises:
            ValueError: If any attribute fails validation
        """
        self.validate_amount(amount)
        self.validate_currency(currency)

        self._date = date
        self._amount = amount
        self._currency = currency
        self._description = description
        self._paid_by = paid_by
        self._id = self.generate_id()

    @property
    def id(self) -> str:
        """Get the expense's unique identifier."""
        return self._id

    @property
    def date(self) -> datetime.date:
        """Get the expense date."""
        return self._date

    @property
    def amount(self) -> Decimal:
        """Get the expense amount."""
        return self._amount

    @property
    def currency(self) -> str:
        """Get the currency code."""
        return self._currency

    @property
    def description(self) -> str:
        """Get the expense description."""
        return self._description

    @property
    def paid_by(self) -> Partner:
        """Get the partner who paid for the expense."""
        return self._paid_by

    @staticmethod
    def validate_amount(amount: Decimal) -> None:
        """Validate expense amount according to business rules.

        Args:
            amount: The amount to validate

        Raises:
            ValueError: If amount is not positive (must be > 0)
        """
        if amount <= 0:
            raise ValueError("Expense amount must be positive")

    @staticmethod
    def validate_currency(currency: str) -> None:
        """Validate currency code according to business rules.

        Args:
            currency: The currency code to validate

        Raises:
            ValueError: If currency is not a 3-letter uppercase code
        """
        if not currency:
            raise ValueError("Currency code cannot be empty")

        if not re.match(r"^[A-Z]{3}$", currency):
            raise ValueError(
                "Currency code must be 3 uppercase letters (e.g., USD, EUR)"
            )

    def generate_id(self) -> str:
        """Generate consistent ID from expense attributes.

        Creates a unique identifier by hashing the expense's key attributes:
        date, amount, currency, description, and paid_by partner name.

        Returns:
            First 8 characters of the hexadecimal hash digest
        """
        # Create hash string from expense attributes
        hash_string = (
            f"{self._date.isoformat()}"
            f"{self._amount}"
            f"{self._currency}"
            f"{self._description}"
            f"{self._paid_by.name}"
        )

        # Generate hash and return first 8 characters
        hash_object = hashlib.sha256(hash_string.encode())
        return hash_object.hexdigest()[:8]

    def __eq__(self, other: object) -> bool:
        """Check equality based on id.

        Args:
            other: The object to compare with

        Returns:
            True if both are Expense instances with the same id
        """
        if not isinstance(other, Expense):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        """Return hash based on id for use in sets and dicts.

        Returns:
            Hash of the expense's id
        """
        return hash(self._id)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            A string showing the Expense class and key attributes
        """
        return (
            f"Expense(id={self._id!r}, date={self._date!r}, "
            f"amount={self._amount!r}, currency={self._currency!r}, "
            f"description={self._description!r}, paid_by={self._paid_by!r})"
        )
