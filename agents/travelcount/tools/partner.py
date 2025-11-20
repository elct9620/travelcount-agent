"""Partner management tool for TravelCount ADK agent.

This module provides a Function Tool for managing travel partners through
the ADK agent. It handles partner operations (add, remove, list) with
comprehensive input validation and error handling for LLM integration.

The tool uses dependency injection to accept a PartnerRepository implementation,
enabling loose coupling and easy testing with mock repositories.
"""

from typing import Optional, Protocol

from entities.partner import Partner


class PartnerRepository(Protocol):
    """Protocol defining the contract for partner management operations.

    Using Protocol enables dependency inversion - the tool defines what it needs,
    and any implementation of this protocol can be injected. This makes the tool
    decoupled from storage implementation details.

    Methods:
        add_partner: Add a new partner to the travel session.
        remove_partner: Remove an existing partner from the travel session.
        list_partners: Get all active partners in the travel session.
        partner_exists: Check if a partner exists in the travel session.
    """

    def add_partner(self, partner: Partner) -> None:
        """Add a new partner to the travel session.

        Args:
            partner: The Partner entity to add.

        Raises:
            ValueError: If the partner already exists.
        """
        ...

    def remove_partner(self, name: str) -> None:
        """Remove an existing partner from the travel session.

        Args:
            name: The name of the partner to remove.

        Raises:
            ValueError: If the partner does not exist.
        """
        ...

    def list_partners(self) -> list[Partner]:
        """Get all active partners in the travel session.

        Returns:
            A list of Partner entities currently active in the session.
        """
        ...

    def partner_exists(self, name: str) -> bool:
        """Check if a partner exists in the travel session.

        Args:
            name: The name of the partner to check.

        Returns:
            True if the partner exists, False otherwise.
        """
        ...


def partners(
    operation: str,
    name: Optional[str] = None,
    repository: Optional[PartnerRepository] = None,
) -> dict:
    """Manage travel partners in a TravelCount session.

    This tool provides a unified interface for partner management operations
    with comprehensive input validation and error handling. It delegates
    business logic to the PartnerRepository implementation while handling
    all parameter validation and response formatting.

    Args:
        operation: The operation to perform. Must be "add", "remove", or "list".
        name: The partner's name. Required for "add" and "remove" operations.
               Optional for "list" operation.
        repository: The PartnerRepository implementation to use. Expected to be
                   injected by the ADK runtime. If None, returns an error.

    Returns:
        dict: A dictionary with operation results:
            - Success: {"success": True, "message": "<description>"}
            - Error: {"success": False, "error": "<description>"}

    Examples:
        Add a partner:
            >>> result = partners("add", "Alice", repository=adapter)
            >>> result
            {"success": True, "message": "Partner 'Alice' has been added."}

        Remove a partner:
            >>> result = partners("remove", "Bob", repository=adapter)
            >>> result
            {"success": True, "message": "Partner 'Bob' has been removed."}

        List partners:
            >>> result = partners("list", repository=adapter)
            >>> result
            {"success": True, "message": "Your travel partners are: Alice, Bob."}
    """
    # Validate repository is provided
    if repository is None:
        return {
            "success": False,
            "error": "Repository not provided. Please try again later.",
        }

    # Validate operation parameter
    valid_operations = {"add", "remove", "list"}
    if operation not in valid_operations:
        return {
            "success": False,
            "error": f"Invalid operation '{operation}'. Must be one of: add, remove, list.",
        }

    # Validate name parameter for add/remove operations
    if operation in {"add", "remove"} and not name:
        return {
            "success": False,
            "error": f"Partner name is required for '{operation}' operation.",
        }

    # Handle "add" operation
    if operation == "add":
        return _handle_add_partner(name, repository)

    # Handle "remove" operation
    if operation == "remove":
        return _handle_remove_partner(name, repository)

    # Handle "list" operation
    if operation == "list":
        return _handle_list_partners(repository)

    # This should never be reached due to earlier validation
    return {
        "success": False,
        "error": "An unexpected error occurred. Please try again.",
    }


def _handle_add_partner(name: str, repository: PartnerRepository) -> dict:
    """Handle the "add" operation for adding a new partner.

    Args:
        name: The partner's name to add.
        repository: The PartnerRepository implementation.

    Returns:
        dict: Success or error response.
    """
    try:
        # Validate partner name (raises ValueError if invalid)
        Partner.validate_name(name)

        # Check if partner already exists
        if repository.partner_exists(name):
            return {
                "success": False,
                "error": f"Partner '{name}' already exists.",
            }

        # Create and add the partner
        partner = Partner(name)
        repository.add_partner(partner)

        return {
            "success": True,
            "message": f"Partner '{name}' has been added.",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid partner name: {str(e)}",
        }


def _handle_remove_partner(name: str, repository: PartnerRepository) -> dict:
    """Handle the "remove" operation for removing an existing partner.

    Args:
        name: The partner's name to remove.
        repository: The PartnerRepository implementation.

    Returns:
        dict: Success or error response.
    """
    try:
        # Check if partner exists
        if not repository.partner_exists(name):
            return {
                "success": False,
                "error": f"Partner '{name}' does not exist.",
            }

        # Remove the partner
        repository.remove_partner(name)

        return {
            "success": True,
            "message": f"Partner '{name}' has been removed.",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Failed to remove partner: {str(e)}",
        }


def _handle_list_partners(repository: PartnerRepository) -> dict:
    """Handle the "list" operation for listing all partners.

    Args:
        repository: The PartnerRepository implementation.

    Returns:
        dict: Success response with formatted partner list.
    """
    try:
        partners_list = repository.list_partners()

        if not partners_list:
            return {
                "success": True,
                "message": "You have no travel partners yet.",
            }

        # Format partners as comma-separated string
        partner_names = ", ".join(partner.name for partner in partners_list)
        return {
            "success": True,
            "message": f"Your travel partners are: {partner_names}.",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Failed to list partners: {str(e)}",
        }
