"""Tests for partner management tool.

This module tests the partner tool's ability to handle LLM interactions,
validate inputs, delegate to repository implementations, and format responses
for the ADK agent system.
"""

from unittest.mock import Mock


from agents.travelcount.entities.partner import Partner
from agents.travelcount.tools.partner import partners


class TestPartnersToolValidation:
    """Test input validation for the partners tool."""

    def test_partners_invalid_operation(self, mock_partner_repository: Mock) -> None:
        """Test that invalid operation returns error."""
        result = partners("invalid", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Invalid operation" in result["error"]
        assert "add, remove, list" in result["error"]

    def test_partners_missing_name_for_add(self, mock_partner_repository: Mock) -> None:
        """Test that add operation without name returns error."""
        result = partners("add", name=None, repository=mock_partner_repository)

        assert result["success"] is False
        assert "Partner name is required" in result["error"]
        assert "'add' operation" in result["error"]

    def test_partners_missing_name_for_remove(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that remove operation without name returns error."""
        result = partners("remove", name=None, repository=mock_partner_repository)

        assert result["success"] is False
        assert "Partner name is required" in result["error"]
        assert "'remove' operation" in result["error"]

    def test_partners_missing_repository(self) -> None:
        """Test that missing repository returns error."""
        result = partners("list", repository=None)

        assert result["success"] is False
        assert "Repository not provided" in result["error"]

    def test_partners_list_operation_allows_missing_name(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that list operation doesn't require name parameter."""
        mock_partner_repository.list_partners.return_value = []

        result = partners("list", name=None, repository=mock_partner_repository)

        assert result["success"] is True


class TestPartnersToolAddOperation:
    """Test add operation for the partners tool."""

    def test_partners_add_operation_success(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test successful partner addition."""
        mock_partner_repository.partner_exists.return_value = False

        result = partners("add", "Alice", repository=mock_partner_repository)

        assert result["success"] is True
        assert result["message"] == "Partner 'Alice' has been added."
        mock_partner_repository.add_partner.assert_called_once()

        # Verify the Partner entity was created correctly
        call_args = mock_partner_repository.add_partner.call_args
        partner_arg = call_args[0][0]
        assert isinstance(partner_arg, Partner)
        assert partner_arg.name == "Alice"

    def test_partners_add_handles_duplicate_error(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that adding duplicate partner returns error."""
        mock_partner_repository.partner_exists.return_value = True

        result = partners("add", "Alice", repository=mock_partner_repository)

        assert result["success"] is False
        assert "already exists" in result["error"]
        assert "Alice" in result["error"]
        # Should not call add_partner if partner exists
        mock_partner_repository.add_partner.assert_not_called()

    def test_partners_add_validates_name(self, mock_partner_repository: Mock) -> None:
        """Test that add operation validates partner name."""
        mock_partner_repository.partner_exists.return_value = False

        # Try to add partner with invalid name
        result = partners("add", "alice@email", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Invalid partner name" in result["error"]
        # Should not call add_partner for invalid name
        mock_partner_repository.add_partner.assert_not_called()

    def test_partners_add_with_empty_name(self, mock_partner_repository: Mock) -> None:
        """Test that add operation rejects empty names."""
        result = partners("add", "", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Partner name is required" in result["error"]

    def test_partners_add_with_complex_valid_name(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test adding partner with complex but valid name."""
        mock_partner_repository.partner_exists.return_value = False

        result = partners(
            "add", "John-Paul Smith_Jr", repository=mock_partner_repository
        )

        assert result["success"] is True
        assert "John-Paul Smith_Jr" in result["message"]


class TestPartnersToolRemoveOperation:
    """Test remove operation for the partners tool."""

    def test_partners_remove_operation_success(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test successful partner removal."""
        mock_partner_repository.partner_exists.return_value = True

        result = partners("remove", "Alice", repository=mock_partner_repository)

        assert result["success"] is True
        assert result["message"] == "Partner 'Alice' has been removed."
        mock_partner_repository.remove_partner.assert_called_once_with("Alice")

    def test_partners_remove_handles_nonexistent_error(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that removing non-existent partner returns error."""
        mock_partner_repository.partner_exists.return_value = False

        result = partners("remove", "Bob", repository=mock_partner_repository)

        assert result["success"] is False
        assert "does not exist" in result["error"]
        assert "Bob" in result["error"]
        # Should not call remove_partner if partner doesn't exist
        mock_partner_repository.remove_partner.assert_not_called()

    def test_partners_remove_handles_repository_exception(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that repository exceptions are handled gracefully."""
        mock_partner_repository.partner_exists.return_value = True
        mock_partner_repository.remove_partner.side_effect = ValueError(
            "Unexpected error"
        )

        result = partners("remove", "Alice", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Failed to remove partner" in result["error"]


class TestPartnersToolListOperation:
    """Test list operation for the partners tool."""

    def test_partners_list_operation_success(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test successful partner listing."""
        partners_list = [Partner("Alice"), Partner("Bob"), Partner("Charlie")]
        mock_partner_repository.list_partners.return_value = partners_list

        result = partners("list", repository=mock_partner_repository)

        assert result["success"] is True
        assert "Alice, Bob, Charlie" in result["message"]
        assert "Your travel partners are:" in result["message"]
        mock_partner_repository.list_partners.assert_called_once()

    def test_partners_list_operation_empty(self, mock_partner_repository: Mock) -> None:
        """Test listing when no partners exist."""
        mock_partner_repository.list_partners.return_value = []

        result = partners("list", repository=mock_partner_repository)

        assert result["success"] is True
        assert result["message"] == "You have no travel partners yet."

    def test_partners_list_operation_single_partner(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test listing with single partner."""
        partners_list = [Partner("Alice")]
        mock_partner_repository.list_partners.return_value = partners_list

        result = partners("list", repository=mock_partner_repository)

        assert result["success"] is True
        assert "Alice" in result["message"]
        assert "Your travel partners are:" in result["message"]

    def test_partners_list_handles_repository_exception(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that repository exceptions are handled gracefully."""
        mock_partner_repository.list_partners.side_effect = ValueError(
            "Unexpected error"
        )

        result = partners("list", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Failed to list partners" in result["error"]


class TestPartnersToolDependencyInjection:
    """Test dependency injection pattern for the partners tool."""

    def test_partners_tool_uses_dependency_injection(self) -> None:
        """Test that tool accepts repository via dependency injection."""
        # Create a custom mock repository
        custom_repo = Mock()
        custom_repo.list_partners.return_value = [Partner("TestUser")]

        result = partners("list", repository=custom_repo)

        assert result["success"] is True
        assert "TestUser" in result["message"]
        # Verify our custom repository was called
        custom_repo.list_partners.assert_called_once()

    def test_partners_tool_with_different_repository_implementations(self) -> None:
        """Test that tool works with different repository implementations."""
        # Mock repository 1
        repo1 = Mock()
        repo1.list_partners.return_value = [Partner("Alice")]

        # Mock repository 2
        repo2 = Mock()
        repo2.list_partners.return_value = [Partner("Bob"), Partner("Charlie")]

        result1 = partners("list", repository=repo1)
        result2 = partners("list", repository=repo2)

        assert "Alice" in result1["message"]
        assert "Bob, Charlie" in result2["message"]


class TestPartnersToolResponseFormat:
    """Test response formatting for LLM integration."""

    def test_partners_success_response_format(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that success responses have correct format."""
        mock_partner_repository.partner_exists.return_value = False

        result = partners("add", "Alice", repository=mock_partner_repository)

        # Success response should have success=True and message
        assert "success" in result
        assert result["success"] is True
        assert "message" in result
        assert isinstance(result["message"], str)
        assert "error" not in result

    def test_partners_error_response_format(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that error responses have correct format."""
        result = partners("invalid_op", repository=mock_partner_repository)

        # Error response should have success=False and error
        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert "message" not in result

    def test_partners_response_is_dict(self, mock_partner_repository: Mock) -> None:
        """Test that all responses are dictionaries."""
        test_cases = [
            ("add", "Alice"),
            ("remove", "Bob"),
            ("list", None),
            ("invalid", None),
        ]

        mock_partner_repository.partner_exists.return_value = False
        mock_partner_repository.list_partners.return_value = []

        for operation, name in test_cases:
            result = partners(operation, name, repository=mock_partner_repository)
            assert isinstance(result, dict)


class TestPartnersToolEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_partners_add_with_whitespace_name(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that whitespace-only names are rejected."""
        result = partners("add", "   ", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Invalid partner name" in result["error"]

    def test_partners_operation_is_case_sensitive(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that operation names are case-sensitive."""
        result = partners("ADD", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Invalid operation" in result["error"]

    def test_partners_with_unicode_name(self, mock_partner_repository: Mock) -> None:
        """Test that unicode characters in names are rejected."""
        # Unicode characters should fail validation (only ASCII allowed)
        result = partners("add", "Alice张", repository=mock_partner_repository)

        assert result["success"] is False
        assert "Invalid partner name" in result["error"]

    def test_partners_list_with_name_parameter_is_ignored(
        self, mock_partner_repository: Mock
    ) -> None:
        """Test that list operation ignores name parameter."""
        mock_partner_repository.list_partners.return_value = [Partner("Bob")]

        # Name parameter is provided but should be ignored for list
        result = partners("list", "Alice", repository=mock_partner_repository)

        assert result["success"] is True
        # Should list Bob, not filter by Alice
        assert "Bob" in result["message"]
