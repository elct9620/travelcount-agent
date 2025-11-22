"""Beancount adapter implementing PartnerRepository and ExpenseRepository protocols.

This module provides a concrete implementation of the PartnerRepository protocol
(defined in agents.travelcount.tools.partner) using Beancount as the storage backend.
It translates between Partner domain entities and Beancount account directives,
managing partner data through Open and Close directives in the session-specific
ledger file.

The adapter also implements ExpenseRepository protocol for expense tracking,
managing expenses as Transaction directives with metadata for tracking and splitting.

The protocol is defined by the consumer (partner tool) following dependency inversion
principle - the tool defines what it needs, and this adapter provides the implementation.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount import loader
from beancount.core import data
from beancount.core.amount import Amount
from beancount.parser import printer

from ..entities.partner import Partner
from .session_manager import SessionManager


class BeancountAdapter:
    """Beancount storage adapter implementing PartnerRepository and ExpenseRepository protocols.

    This adapter translates Partner entities to/from Beancount account directives.
    Partners are stored as Beancount accounts with the pattern:
    Assets:Travel:Partners:[PartnerName]

    Expenses are stored as Transaction directives with:
    - expense-id metadata for tracking
    - Debit to Expenses:Travel:[Category]
    - Credit to Assets:Travel:Partners:[PaidBy]

    The adapter uses:
    - Open directives to add new partners
    - Close directives to remove existing partners
    - Transaction directives for expense logging and splits
    - Beancount's loader to parse and read existing data

    Attributes:
        session_manager: SessionManager instance for accessing ledger files
    """

    ACCOUNT_PREFIX = "Assets:Travel:Partners:"
    EXPENSE_PREFIX = "Expenses:Travel:"
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

    # Expense tracking methods (ExpenseRepository protocol implementation)

    def _infer_category(self, description: str) -> str:
        """Infer expense category from description keywords.

        Searches description for common expense keywords to categorize the expense.
        Returns a Beancount account suffix for the category.

        Args:
            description: Expense description to analyze

        Returns:
            Category string (Food, Transport, Hotel, Misc)

        Example:
            >>> adapter._infer_category("Lunch at cafe")
            'Food'
            >>> adapter._infer_category("Taxi to airport")
            'Transport'
        """
        description_lower = description.lower()

        # Food keywords
        food_keywords = [
            "lunch",
            "dinner",
            "breakfast",
            "meal",
            "restaurant",
            "cafe",
            "coffee",
            "food",
            "snack",
        ]
        if any(keyword in description_lower for keyword in food_keywords):
            return "Food"

        # Transport keywords
        transport_keywords = [
            "taxi",
            "uber",
            "lyft",
            "bus",
            "train",
            "flight",
            "transport",
            "metro",
            "subway",
            "airport",
        ]
        if any(keyword in description_lower for keyword in transport_keywords):
            return "Transport"

        # Hotel keywords
        hotel_keywords = ["hotel", "accommodation", "airbnb", "hostel", "lodge"]
        if any(keyword in description_lower for keyword in hotel_keywords):
            return "Hotel"

        # Default to Misc
        return "Misc"

    def _parse_transaction_to_expense(self, transaction: data.Transaction):
        """Convert a Beancount Transaction directive to an Expense entity.

        Parses a transaction directive with expense-id metadata and constructs
        an Expense entity from its postings.

        Args:
            transaction: Transaction directive to parse

        Returns:
            Expense entity parsed from transaction

        Raises:
            ValueError: If transaction doesn't have expense-id metadata
            ValueError: If transaction structure doesn't match expected format
            ValueError: If parsed expense ID doesn't match stored expense-id
        """
        # Import here to avoid circular dependency
        from ..entities.expense import Expense

        # Verify transaction has expense-id metadata
        if "expense-id" not in transaction.meta:
            raise ValueError("Transaction does not have expense-id metadata")

        stored_expense_id = transaction.meta["expense-id"]

        # Find the expense and partner postings
        expense_posting = None
        partner_posting = None

        for posting in transaction.postings:
            if posting.account.startswith(self.EXPENSE_PREFIX):
                expense_posting = posting
            elif posting.account.startswith(self.ACCOUNT_PREFIX):
                partner_posting = posting

        if not expense_posting or not partner_posting:
            raise ValueError("Transaction does not have expected expense structure")

        # Extract expense details
        amount = expense_posting.units.number
        currency = expense_posting.units.currency
        description = transaction.narration
        expense_date = transaction.date

        # Extract partner who paid
        partner_name = partner_posting.account[len(self.ACCOUNT_PREFIX) :]
        paid_by = Partner(partner_name)

        # Create Expense entity (ID will be auto-generated)
        expense = Expense(
            date=expense_date,
            amount=amount,
            currency=currency,
            description=description,
            paid_by=paid_by,
        )

        # Verify the generated ID matches the stored ID
        if expense.id != stored_expense_id:
            raise ValueError(
                f"Generated expense ID '{expense.id}' does not match "
                f"stored expense-id '{stored_expense_id}'"
            )

        return expense

    def log_expense(self, expense, default_partner=None) -> str:
        """Log an expense to the ledger.

        Creates a Transaction directive with the expense details and appends it
        to the ledger file. The transaction includes:
        - expense-id metadata for tracking
        - Debit posting to Expenses:Travel:[Category]
        - Credit posting to Assets:Travel:Partners:[PaidBy]

        Args:
            expense: Expense entity to log
            default_partner: Optional default partner (unused, for protocol compatibility)

        Returns:
            The expense ID

        Example:
            >>> from entities.expense import Expense
            >>> expense = Expense(...)
            >>> expense_id = adapter.log_expense(expense)
        """
        # Import here to avoid circular dependency

        # Infer category from description
        category = self._infer_category(expense.description)
        expense_account = f"{self.EXPENSE_PREFIX}{category}"
        partner_account = self._partner_to_account_name(expense.paid_by)

        ledger_path = self._get_ledger_path()

        # Create Transaction directive
        transaction = data.Transaction(
            meta={
                "filename": str(ledger_path),
                "lineno": 0,
                "expense-id": expense.id,
            },
            date=expense.date,
            flag="*",
            payee=None,
            narration=expense.description,
            tags=set(),
            links=set(),
            postings=[
                # Debit: Expenses account
                data.Posting(
                    account=expense_account,
                    units=Amount(Decimal(str(expense.amount)), expense.currency),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
                # Credit: Partner account (balancing posting, no amount)
                data.Posting(
                    account=partner_account,
                    units=None,  # Beancount will infer the balancing amount
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )

        # Write transaction to ledger
        self._write_directive(transaction)

        return expense.id

    def split_expense(
        self, expense_id: str, partners: list, ratios: list[float] | None = None
    ) -> None:
        """Split an expense among partners.

        Creates a Transaction directive with net settlement amounts showing who owes
        whom. The payer receives the difference between what they paid and their share,
        while other partners owe their respective shares.

        Args:
            expense_id: ID of the expense to split
            partners: List of Partner entities to split among
            ratios: Optional list of split ratios (must sum to 1.0). If None,
                   splits equally among all partners.

        Raises:
            ValueError: If expense not found
            ValueError: If ratios don't sum to 1.0
            ValueError: If ratios length doesn't match partners length

        Example:
            >>> adapter.split_expense("abc123", [alice, bob], [0.6, 0.4])
            # Alice paid $100, split 60-40 results in:
            # Alice: +$40 (receives), Bob: -$40 (owes)
        """
        # Retrieve original expense
        original_expense = self.get_expense_by_id(expense_id)
        if not original_expense:
            raise ValueError(f"Expense with ID '{expense_id}' not found")

        # Calculate split amounts
        if ratios is None:
            # Equal split
            ratios = [1.0 / len(partners)] * len(partners)
        else:
            # Validate ratios
            if len(ratios) != len(partners):
                raise ValueError("Ratios length must match partners length")
            if not abs(sum(ratios) - 1.0) < 0.0001:  # Allow for floating point errors
                raise ValueError(f"Ratios must sum to 1.0, got {sum(ratios)}")

        # Calculate net positions for each partner
        ledger_path = self._get_ledger_path()
        postings = []
        total_amount = Decimal(str(original_expense.amount))

        for partner, ratio in zip(partners, ratios):
            partner_account = self._partner_to_account_name(partner)
            share_amount = total_amount * Decimal(str(ratio))

            # Calculate net position:
            # - If this partner is the payer: net = amount_paid - share = positive (receives)
            # - If this partner is not the payer: net = 0 - share = negative (owes)
            if partner.name == original_expense.paid_by.name:
                net_amount = total_amount - share_amount
            else:
                net_amount = -share_amount

            # Only create posting if net amount is non-zero
            if net_amount != Decimal("0"):
                partner_amount = Amount(net_amount, original_expense.currency)
                postings.append(
                    data.Posting(
                        account=partner_account,
                        units=partner_amount,
                        cost=None,
                        price=None,
                        flag=None,
                        meta={},
                    )
                )

        # Create Transaction directive
        transaction = data.Transaction(
            meta={
                "filename": str(ledger_path),
                "lineno": 0,
                "split-for": expense_id,
            },
            date=original_expense.date,
            flag="*",
            payee=None,
            narration=f"Split: {original_expense.description}",
            tags=set(),
            links=set(),
            postings=postings,
        )

        # Write transaction to ledger
        self._write_directive(transaction)

    def get_expenses(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> list:
        """Retrieve expenses within optional date range.

        Loads all Transaction directives with expense-id metadata and optionally
        filters by date range.

        Args:
            date_from: Optional start date (inclusive)
            date_to: Optional end date (inclusive)

        Returns:
            List of Expense entities matching the criteria

        Example:
            >>> expenses = adapter.get_expenses()
            >>> recent = adapter.get_expenses(date_from=date(2024, 6, 1))
        """
        entries, errors, options = self._load_entries()

        expenses = []

        for entry in entries:
            # Filter for Transaction directives with expense-id metadata
            if not isinstance(entry, data.Transaction):
                continue
            if "expense-id" not in entry.meta:
                continue

            # Apply date range filter
            if date_from and entry.date < date_from:
                continue
            if date_to and entry.date > date_to:
                continue

            # Parse transaction to Expense entity
            try:
                expense = self._parse_transaction_to_expense(entry)
                expenses.append(expense)
            except (ValueError, KeyError):
                # Skip transactions that can't be parsed as expenses
                continue

        return expenses

    def get_expense_by_id(self, expense_id: str):
        """Retrieve a specific expense by ID.

        Searches for a Transaction directive with matching expense-id metadata.

        Args:
            expense_id: The expense ID to search for

        Returns:
            Expense entity if found, None otherwise

        Example:
            >>> expense = adapter.get_expense_by_id("abc123")
        """
        entries, errors, options = self._load_entries()

        for entry in entries:
            # Filter for Transaction directives with matching expense-id
            if not isinstance(entry, data.Transaction):
                continue
            if entry.meta.get("expense-id") != expense_id:
                continue

            # Parse and return the expense
            try:
                return self._parse_transaction_to_expense(entry)
            except (ValueError, KeyError):
                # If parsing fails, continue searching
                continue

        # Expense not found
        return None
