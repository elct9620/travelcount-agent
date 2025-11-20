"""Beancount adapter implementing PartnerRepository protocol.

This module provides a concrete implementation of the PartnerRepository protocol
(defined in agents.travelcount.tools.partner) using Beancount as the storage backend.
It translates between Partner domain entities and Beancount account directives,
managing partner data through Open and Close directives in the session-specific
ledger file.

The protocol is defined by the consumer (partner tool) following dependency inversion
principle - the tool defines what it needs, and this adapter provides the implementation.
"""

from datetime import date
from pathlib import Path

from beancount import loader
from beancount.core import data
from beancount.parser import printer

from ..entities.partner import Partner
from .session_manager import SessionManager


class BeancountAdapter:
    """Beancount storage adapter implementing PartnerRepository protocol.

    This adapter translates Partner entities to/from Beancount account directives.
    Partners are stored as Beancount accounts with the pattern:
    Assets:Travel:Partners:[PartnerName]

    The adapter uses:
    - Open directives to add new partners
    - Close directives to remove existing partners
    - Beancount's loader to parse and read existing partners

    Attributes:
        session_manager: SessionManager instance for accessing ledger files
    """

    ACCOUNT_PREFIX = "Assets:Travel:Partners:"
    CURRENCY = "USD"

    def __init__(self, session_manager: SessionManager) -> None:
        """Initialize BeancountAdapter with a SessionManager.

        Args:
            session_manager: SessionManager instance for managing session files
        """
        self._session_manager = session_manager
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self) -> None:
        """Ensure the session directory and ledger file exist."""
        self._session_manager.ensure_session_directory()
        self._session_manager.initialize_ledger()

    def _get_ledger_path(self) -> Path:
        """Get the path to the current session's ledger file.

        Returns:
            Path to the session's index.bean file
        """
        return self._session_manager.get_ledger_path()

    def _partner_to_account_name(self, partner: Partner) -> str:
        """Convert a Partner entity to a Beancount account name.

        Args:
            partner: Partner entity to convert

        Returns:
            Beancount account name (e.g., "Assets:Travel:Partners:Alice")

        Example:
            >>> partner = Partner("Alice")
            >>> adapter._partner_to_account_name(partner)
            'Assets:Travel:Partners:Alice'
        """
        return f"{self.ACCOUNT_PREFIX}{partner.name}"

    def _account_name_to_partner(self, account_name: str) -> Partner:
        """Convert a Beancount account name to a Partner entity.

        Args:
            account_name: Beancount account name to convert

        Returns:
            Partner entity extracted from account name

        Raises:
            ValueError: If account name doesn't have the expected prefix

        Example:
            >>> account = "Assets:Travel:Partners:Alice"
            >>> partner = adapter._account_name_to_partner(account)
            >>> partner.name
            'Alice'
        """
        if not account_name.startswith(self.ACCOUNT_PREFIX):
            raise ValueError(
                f"Account '{account_name}' does not match partner account pattern"
            )

        partner_name = account_name[len(self.ACCOUNT_PREFIX) :]
        return Partner(partner_name)

    def _load_entries(self) -> tuple[list, list, dict]:
        """Load and parse the Beancount ledger file.

        Returns:
            Tuple of (entries, errors, options) from Beancount loader

        Raises:
            FileNotFoundError: If ledger file doesn't exist
        """
        ledger_path = self._get_ledger_path()

        if not ledger_path.exists():
            # Return empty entries if file doesn't exist
            return [], [], {}

        return loader.load_file(str(ledger_path))

    def _get_open_accounts(self) -> set[str]:
        """Get all currently open partner accounts from the ledger.

        Parses the ledger file and returns a set of account names that have
        an Open directive but no corresponding Close directive.

        Returns:
            Set of account names for currently open partner accounts
        """
        entries, errors, options = self._load_entries()

        opened_accounts = set()
        closed_accounts = set()

        for entry in entries:
            if isinstance(entry, data.Open):
                if entry.account.startswith(self.ACCOUNT_PREFIX):
                    opened_accounts.add(entry.account)
            elif isinstance(entry, data.Close):
                if entry.account.startswith(self.ACCOUNT_PREFIX):
                    closed_accounts.add(entry.account)

        # Return accounts that are opened but not closed
        return opened_accounts - closed_accounts

    def _write_directive(self, directive: data.Directive) -> None:
        """Write a Beancount directive to the ledger file.

        Appends the directive to the end of the ledger file using Beancount's
        printer module.

        Args:
            directive: Beancount directive to write (Open or Close)
        """
        ledger_path = self._get_ledger_path()

        with open(ledger_path, "a", encoding="utf-8") as f:
            # Add a newline before the directive for readability
            printer.print_entry(directive, file=f)

    def add_partner(self, partner: Partner) -> None:
        """Add a new partner to the repository.

        Creates an Open directive in the Beancount ledger for the partner.
        The partner must not already exist in the repository.

        Args:
            partner: Partner entity to add with a validated name

        Raises:
            ValueError: If a partner with the same name already exists

        Example:
            >>> from entities.partner import Partner
            >>> partner = Partner("Alice")
            >>> adapter.add_partner(partner)
        """
        # Check if partner already exists
        if self.partner_exists(partner.name):
            raise ValueError(f"Partner '{partner.name}' already exists.")

        # Create account name
        account_name = self._partner_to_account_name(partner)
        ledger_path = self._get_ledger_path()

        # Create Open directive
        open_directive = data.Open(
            meta={"filename": str(ledger_path), "lineno": 0},
            date=date.today(),
            account=account_name,
            currencies=[self.CURRENCY],
            booking=None,
        )

        # Write directive to file
        self._write_directive(open_directive)

    def remove_partner(self, name: str) -> None:
        """Remove an existing partner from the repository.

        Creates a Close directive in the Beancount ledger for the partner.
        The partner must exist in the repository.

        Args:
            name: The name of the partner to remove

        Raises:
            ValueError: If no partner with the given name exists

        Example:
            >>> adapter.remove_partner("Alice")
        """
        # Check if partner exists
        if not self.partner_exists(name):
            raise ValueError(f"Partner '{name}' does not exist.")

        # Create account name
        partner = Partner(name)
        account_name = self._partner_to_account_name(partner)
        ledger_path = self._get_ledger_path()

        # Create Close directive
        close_directive = data.Close(
            meta={"filename": str(ledger_path), "lineno": 0},
            date=date.today(),
            account=account_name,
        )

        # Write directive to file
        self._write_directive(close_directive)

    def list_partners(self) -> list[Partner]:
        """List all active partners in the repository.

        Returns all partners that have an Open directive but no Close directive
        in the Beancount ledger.

        Returns:
            List of Partner entities representing active partners. Returns an
            empty list if no partners exist.

        Example:
            >>> partners = adapter.list_partners()
            >>> for partner in partners:
            ...     print(partner.name)
        """
        open_accounts = self._get_open_accounts()

        partners = []
        for account_name in sorted(open_accounts):
            try:
                partner = self._account_name_to_partner(account_name)
                partners.append(partner)
            except ValueError:
                # Skip accounts that don't match the partner pattern
                # (shouldn't happen but defensive programming)
                continue

        return partners

    def partner_exists(self, name: str) -> bool:
        """Check if a partner exists in the repository.

        Checks whether a partner with the given name currently exists and
        is active (has an Open directive but no Close directive).

        Args:
            name: The name of the partner to check

        Returns:
            True if the partner exists and is active, False otherwise

        Example:
            >>> if adapter.partner_exists("Alice"):
            ...     print("Alice is already a partner")
        """
        try:
            partner = Partner(name)
            account_name = self._partner_to_account_name(partner)
            open_accounts = self._get_open_accounts()
            return account_name in open_accounts
        except ValueError:
            # If Partner name validation fails, partner doesn't exist
            return False
