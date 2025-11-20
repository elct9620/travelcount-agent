"""Tests for Partner entity."""

import pytest

from agents.travelcount.entities.partner import Partner


class TestPartnerConstruction:
    """Test Partner entity construction and validation."""

    def test_create_partner_with_valid_name(self) -> None:
        """Test creating a partner with a simple valid name."""
        partner = Partner("Alice")
        assert partner.name == "Alice"

    def test_create_partner_with_name_containing_space(self) -> None:
        """Test creating a partner with a name containing spaces."""
        partner = Partner("Bob Chen")
        assert partner.name == "Bob Chen"

    def test_create_partner_with_name_containing_hyphen(self) -> None:
        """Test creating a partner with a name containing hyphen."""
        partner = Partner("Mary-Jane")
        assert partner.name == "Mary-Jane"

    def test_create_partner_with_name_containing_underscore(self) -> None:
        """Test creating a partner with a name containing underscore."""
        partner = Partner("Alice_Smith")
        assert partner.name == "Alice_Smith"

    def test_create_partner_with_name_containing_numbers(self) -> None:
        """Test creating a partner with a name containing numbers."""
        partner = Partner("Agent007")
        assert partner.name == "Agent007"

    def test_create_partner_with_complex_valid_name(self) -> None:
        """Test creating a partner with a complex but valid name."""
        partner = Partner("John-Paul Smith_Jr 123")
        assert partner.name == "John-Paul Smith_Jr 123"


class TestPartnerValidation:
    """Test Partner name validation rules."""

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Partner name cannot be empty"):
            Partner("")

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Partner name cannot be whitespace-only"):
            Partner("   ")

    def test_name_with_at_symbol_raises_error(self) -> None:
        """Test that name with @ symbol raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains special characters"
        ):
            Partner("alice@email")

    def test_name_with_dollar_sign_raises_error(self) -> None:
        """Test that name with $ symbol raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains special characters"
        ):
            Partner("bob$money")

    def test_name_with_colon_raises_error(self) -> None:
        """Test that name with : symbol raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains special characters"
        ):
            Partner("alice:bob")

    def test_name_with_forward_slash_raises_error(self) -> None:
        """Test that name with / symbol raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains special characters"
        ):
            Partner("alice/bob")

    def test_name_with_backslash_raises_error(self) -> None:
        """Test that name with \\ symbol raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains special characters"
        ):
            Partner("alice\\bob")

    def test_name_with_path_traversal_raises_error(self) -> None:
        """Test that name with .. (path traversal) raises ValueError."""
        with pytest.raises(
            ValueError, match="Partner name contains path traversal attempt"
        ):
            Partner("../alice")

    def test_name_with_period_in_middle_is_valid(self) -> None:
        """Test that a single period in name is not allowed."""
        with pytest.raises(ValueError):
            Partner("alice.bob")

    def test_name_with_parenthesis_raises_error(self) -> None:
        """Test that name with special characters like parenthesis raises ValueError."""
        with pytest.raises(ValueError):
            Partner("alice (bob)")

    def test_name_with_punctuation_raises_error(self) -> None:
        """Test that name with punctuation marks raises ValueError."""
        with pytest.raises(ValueError):
            Partner("alice,bob")


class TestPartnerEquality:
    """Test Partner equality comparison."""

    def test_same_name_partners_are_equal(self) -> None:
        """Test that two partners with the same name are equal."""
        partner1 = Partner("Alice")
        partner2 = Partner("Alice")
        assert partner1 == partner2

    def test_different_name_partners_are_not_equal(self) -> None:
        """Test that two partners with different names are not equal."""
        partner1 = Partner("Alice")
        partner2 = Partner("Bob")
        assert partner1 != partner2

    def test_partner_not_equal_to_non_partner_object(self) -> None:
        """Test that partner is not equal to non-Partner objects."""
        partner = Partner("Alice")
        assert partner != "Alice"
        assert partner != 123
        assert partner is not None
        assert partner != {}

    def test_partner_not_equal_to_non_partner_returns_not_implemented(self) -> None:
        """Test that comparing with non-Partner returns NotImplemented correctly."""
        partner = Partner("Alice")
        result = partner.__eq__("Alice")
        assert result == NotImplemented


class TestPartnerHashing:
    """Test Partner hashing for use in sets and dicts."""

    def test_partner_is_hashable(self) -> None:
        """Test that Partner instances are hashable."""
        partner = Partner("Alice")
        hash_value = hash(partner)
        assert isinstance(hash_value, int)

    def test_same_name_partners_have_same_hash(self) -> None:
        """Test that partners with same name have same hash."""
        partner1 = Partner("Alice")
        partner2 = Partner("Alice")
        assert hash(partner1) == hash(partner2)

    def test_partner_can_be_used_in_set(self) -> None:
        """Test that Partner instances can be used in sets."""
        partner1 = Partner("Alice")
        partner2 = Partner("Bob")
        partner3 = Partner("Alice")

        partner_set = {partner1, partner2, partner3}
        assert len(partner_set) == 2

    def test_partner_can_be_used_as_dict_key(self) -> None:
        """Test that Partner instances can be used as dictionary keys."""
        partner1 = Partner("Alice")
        partner2 = Partner("Bob")

        partner_dict = {partner1: "Alice's data", partner2: "Bob's data"}
        assert partner_dict[Partner("Alice")] == "Alice's data"
        assert partner_dict[Partner("Bob")] == "Bob's data"


class TestPartnerRepr:
    """Test Partner string representation."""

    def test_partner_repr_format(self) -> None:
        """Test that __repr__ returns expected format."""
        partner = Partner("Alice")
        assert repr(partner) == "Partner(name='Alice')"

    def test_partner_repr_with_spaces(self) -> None:
        """Test __repr__ with name containing spaces."""
        partner = Partner("Bob Chen")
        assert repr(partner) == "Partner(name='Bob Chen')"

    def test_partner_repr_is_useful_for_debugging(self) -> None:
        """Test that repr output contains relevant debugging info."""
        partner = Partner("Alice")
        repr_str = repr(partner)
        assert "Partner" in repr_str
        assert "Alice" in repr_str
