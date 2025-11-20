"""Partner entity for TravelCount application.

This module defines the Partner domain entity representing a person participating
in shared expense tracking. Follows Clean Architecture principles with self-validating
business logic separated from storage concerns.
"""

import re


class Partner:
    """Represents a partner in travel expense tracking.

    A partner is a person who participates in shared expense tracking sessions.
    This is a domain entity that enforces business rules and validates state.

    Attributes:
        name: The partner's name (validated at construction time)
    """

    def __init__(self, name: str) -> None:
        """Initialize a Partner with validated name.

        Args:
            name: The partner's name to validate and store

        Raises:
            ValueError: If name fails validation
        """
        self.validate_name(name)
        self._name = name

    @property
    def name(self) -> str:
        """Get the partner's name."""
        return self._name

    @staticmethod
    def validate_name(name: str) -> None:
        r"""Validate partner name according to business rules.

        Args:
            name: The name to validate

        Raises:
            ValueError: If name is empty, whitespace-only, contains special
                characters (@, $, :, /, \, ..), or attempts path traversal
        """
        if not name:
            raise ValueError("Partner name cannot be empty")

        if name.isspace():
            raise ValueError("Partner name cannot be whitespace-only")

        # Check for path traversal attempts first (before checking /)
        if ".." in name:
            raise ValueError("Partner name contains path traversal attempt (..)")

        # Check for special characters: @, $, :, /, \
        if any(char in name for char in ["@", "$", ":", "/", "\\"]):
            raise ValueError("Partner name contains special characters: @, $, :, /, \\")

        # Ensure name contains only valid characters:
        # letters, numbers, spaces, hyphens, underscores
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", name):
            raise ValueError(
                "Partner name can only contain letters, numbers, spaces, "
                "hyphens, and underscores"
            )

    def __eq__(self, other: object) -> bool:
        """Check equality based on name.

        Args:
            other: The object to compare with

        Returns:
            True if both are Partner instances with the same name
        """
        if not isinstance(other, Partner):
            return NotImplemented
        return self._name == other._name

    def __hash__(self) -> int:
        """Return hash based on name for use in sets and dicts.

        Returns:
            Hash of the partner's name
        """
        return hash(self._name)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            A string showing the Partner class and name
        """
        return f"Partner(name={self._name!r})"
