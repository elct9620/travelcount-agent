"""Shared fixtures for TravelCount tests.

This module provides common pytest fixtures used across all test modules,
including temporary directories, mock repositories, and test data.
"""

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest

from entities.partner import Partner
from storage.beancount_adapter import BeancountAdapter
from storage.session_manager import SessionManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test file operations.

    Yields:
        Path to temporary directory that is cleaned up after test

    Example:
        >>> def test_example(temp_dir):
        ...     file_path = temp_dir / "test.txt"
        ...     file_path.write_text("test content")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_dir: Path) -> SessionManager:
    """Provide a SessionManager configured with temporary directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        SessionManager instance pointing to temp directory

    Example:
        >>> def test_example(session_manager):
        ...     ledger_path = session_manager.get_ledger_path()
        ...     assert ledger_path.exists() is False
    """
    manager = SessionManager("test-session")
    manager._base_data_dir = temp_dir
    return manager


@pytest.fixture
def initialized_session_manager(session_manager: SessionManager) -> SessionManager:
    """Provide a SessionManager with initialized directory and ledger.

    Args:
        session_manager: SessionManager fixture

    Returns:
        SessionManager with created directory and initialized ledger

    Example:
        >>> def test_example(initialized_session_manager):
        ...     ledger_path = initialized_session_manager.get_ledger_path()
        ...     assert ledger_path.exists() is True
    """
    session_manager.ensure_session_directory()
    session_manager.initialize_ledger()
    return session_manager


@pytest.fixture
def beancount_adapter(initialized_session_manager: SessionManager) -> BeancountAdapter:
    """Provide a BeancountAdapter with initialized session.

    Args:
        initialized_session_manager: SessionManager with initialized ledger

    Returns:
        BeancountAdapter instance ready for partner operations

    Example:
        >>> def test_example(beancount_adapter):
        ...     partner = Partner("Alice")
        ...     beancount_adapter.add_partner(partner)
    """
    return BeancountAdapter(initialized_session_manager)


@pytest.fixture
def mock_partner_repository() -> Mock:
    """Provide a mock PartnerRepository for testing tools.

    Returns:
        Mock object implementing PartnerRepository protocol

    Example:
        >>> def test_example(mock_partner_repository):
        ...     mock_partner_repository.partner_exists.return_value = False
        ...     mock_partner_repository.add_partner(Partner("Alice"))
        ...     mock_partner_repository.add_partner.assert_called_once()
    """
    repository = Mock()
    repository.add_partner = Mock(return_value=None)
    repository.remove_partner = Mock(return_value=None)
    repository.list_partners = Mock(return_value=[])
    repository.partner_exists = Mock(return_value=False)
    return repository


@pytest.fixture
def sample_partner() -> Partner:
    """Provide a sample Partner entity for testing.

    Returns:
        Partner instance with name "Alice"

    Example:
        >>> def test_example(sample_partner):
        ...     assert sample_partner.name == "Alice"
    """
    return Partner("Alice")


@pytest.fixture
def sample_partners() -> list[Partner]:
    """Provide a list of sample Partner entities for testing.

    Returns:
        List of Partner instances with names Alice, Bob, and Charlie

    Example:
        >>> def test_example(sample_partners):
        ...     assert len(sample_partners) == 3
        ...     assert sample_partners[0].name == "Alice"
    """
    return [Partner("Alice"), Partner("Bob"), Partner("Charlie")]


@pytest.fixture
def ledger_with_partners(
    initialized_session_manager: SessionManager,
) -> tuple[SessionManager, list[Partner]]:
    """Provide a session with partners already added to the ledger.

    Args:
        initialized_session_manager: SessionManager with initialized ledger

    Returns:
        Tuple of (SessionManager, list of added Partners)

    Example:
        >>> def test_example(ledger_with_partners):
        ...     manager, partners = ledger_with_partners
        ...     adapter = BeancountAdapter(manager)
        ...     assert adapter.partner_exists("Alice") is True
    """
    adapter = BeancountAdapter(initialized_session_manager)
    partners = [Partner("Alice"), Partner("Bob"), Partner("Charlie")]

    for partner in partners:
        adapter.add_partner(partner)

    return initialized_session_manager, partners


@pytest.fixture
def ledger_content_with_open_directive() -> str:
    """Provide sample Beancount ledger content with an open directive.

    Returns:
        String containing Beancount ledger with one partner account

    Example:
        >>> def test_example(ledger_content_with_open_directive):
        ...     content = ledger_content_with_open_directive
        ...     assert "2024-01-01 open Assets:Travel:Partners:Alice" in content
    """
    return """; TravelCount Session Ledger
; Session ID: test-session
; Created: 2024-01-01

option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
"""


@pytest.fixture
def ledger_content_with_closed_partner() -> str:
    """Provide sample Beancount ledger content with a closed partner.

    Returns:
        String containing Beancount ledger with one opened and closed partner

    Example:
        >>> def test_example(ledger_content_with_closed_partner):
        ...     content = ledger_content_with_closed_partner
        ...     assert "2024-01-02 close Assets:Travel:Partners:Alice" in content
    """
    return """; TravelCount Session Ledger
; Session ID: test-session
; Created: 2024-01-01

option "operating_currency" "USD"

2024-01-01 open Assets:Travel:Partners:Alice USD
2024-01-02 close Assets:Travel:Partners:Alice
"""
