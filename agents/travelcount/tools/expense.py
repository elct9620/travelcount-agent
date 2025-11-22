"""Expense management tool for TravelCount ADK agent.

This module provides Function Tools for managing travel expenses through
the ADK agent. It handles expense operations (log, split, retrieve) with
comprehensive input validation and error handling for LLM integration.

The tool uses dependency injection to accept an ExpenseRepository implementation,
enabling loose coupling and easy testing with mock repositories.
"""

import datetime
from typing import Optional, Protocol

from ..entities.expense import Expense
from ..entities.partner import Partner


class ExpenseRepository(Protocol):
    """Protocol defining the contract for expense management operations.

    Using Protocol enables dependency inversion - the tool defines what it needs,
    and any implementation of this protocol can be injected. This makes the tool
    decoupled from storage implementation details.

    Methods:
        log_expense: Log a new expense to the travel session.
        split_expense: Split an expense among travel partners.
        get_expenses: Retrieve expenses within optional date range.
        get_expense_by_id: Retrieve a specific expense by ID.
        list_partners: Get all active partners in the travel session.
    """

    def log_expense(
        self, expense: Expense, default_partner: Partner | None = None
    ) -> str:
        """Log a new expense to the travel session.

        Args:
            expense: The Expense entity to log.
            default_partner: Default partner if expense.paid_by is None.

        Returns:
            The unique expense ID.

        Raises:
            ValueError: If validation fails or partner not found.
        """
        ...

    def split_expense(
        self,
        expense_id: str,
        partners: list[Partner],
        ratios: list[float] | None = None,
    ) -> None:
        """Split an expense among travel partners.

        Args:
            expense_id: The unique ID of the expense to split.
            partners: List of Partner entities to split among.
            ratios: Optional list of split ratios (must sum to 1.0).

        Raises:
            ValueError: If expense not found or ratios invalid.
        """
        ...

    def get_expenses(
        self,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> list[Expense]:
        """Retrieve expenses within optional date range.

        Args:
            date_from: Start date of range (inclusive). None for no start limit.
            date_to: End date of range (inclusive). None for no end limit.

        Returns:
            List of Expense entities matching the criteria.
        """
        ...

    def get_expense_by_id(self, expense_id: str) -> Expense | None:
        """Retrieve a specific expense by ID.

        Args:
            expense_id: The unique ID of the expense.

        Returns:
            The Expense entity if found, None otherwise.
        """
        ...

    def list_partners(self) -> list[Partner]:
        """Get all active partners in the travel session.

        Returns:
            A list of Partner entities currently active in the session.
        """
        ...

    def get_splits(
        self,
        date_from: datetime.date | None = None,
        date_to: datetime.date | None = None,
    ) -> dict[str, dict[str, any]]:
        """Retrieve split transactions within optional date range.

        Args:
            date_from: Start date of range (inclusive). None for no start limit.
            date_to: End date of range (inclusive). None for no end limit.

        Returns:
            Dictionary mapping expense_id to partner shares.
        """
        ...


def log_expense(
    amount: float,
    currency: str,
    description: str,
    paid_by: Optional[str] = None,
    repository: Optional[ExpenseRepository] = None,
) -> dict:
    """Log a travel expense.

    This tool records a new expense with automatic expense ID generation.
    If paid_by is not specified, it defaults to the first partner in the session.

    Args:
        amount: The expense amount (must be positive).
        currency: Currency code (3 uppercase letters, e.g., "USD").
        description: Brief description of the expense.
        paid_by: Name of the partner who paid. Defaults to first partner if None.
        repository: The ExpenseRepository implementation to use. Expected to be
                   injected by the ADK runtime. If None, returns an error.

    Returns:
        dict: A dictionary with operation results:
            - Success: {"success": True, "message": "...", "expense_id": "..."}
            - Error: {"success": False, "error": "..."}

    Examples:
        Log an expense:
            >>> result = log_expense(50.0, "USD", "Lunch", "Alice", repository=adapter)
            >>> result
            {"success": True, "message": "Expense logged: ...", "expense_id": "..."}
    """
    # Validate repository is provided
    if repository is None:
        return {
            "success": False,
            "error": "Repository not provided. Please try again later.",
        }

    return _handle_log_expense(amount, currency, description, paid_by, repository)


def split_expense(
    expense_id: str,
    partners: list[str],
    ratios: Optional[list[float]] = None,
    repository: Optional[ExpenseRepository] = None,
) -> dict:
    """Split an expense among travel partners.

    This tool splits an existing expense among specified partners with optional
    custom ratios. If ratios are not provided, the expense is split equally.

    Args:
        expense_id: The unique ID of the expense to split.
        partners: List of partner names to split the expense among.
        ratios: Optional list of split ratios. Must sum to 1.0 if provided.
               If None, expense is split equally among partners.
        repository: The ExpenseRepository implementation to use. Expected to be
                   injected by the ADK runtime. If None, returns an error.

    Returns:
        dict: A dictionary with operation results:
            - Success: {"success": True, "message": "..."}
            - Error: {"success": False, "error": "..."}

    Examples:
        Split equally:
            >>> result = split_expense("abc123", ["Alice", "Bob"], repository=adapter)
            >>> result
            {"success": True, "message": "Expense split among 2 partners."}

        Split with custom ratios:
            >>> result = split_expense("abc123", ["Alice", "Bob"], [0.6, 0.4], repository=adapter)
            >>> result
            {"success": True, "message": "Expense split among 2 partners."}
    """
    # Validate repository is provided
    if repository is None:
        return {
            "success": False,
            "error": "Repository not provided. Please try again later.",
        }

    return _handle_split_expense(expense_id, partners, ratios, repository)


def get_expenses(
    range: str = "all",
    aggregate: bool = True,
    repository: Optional[ExpenseRepository] = None,
) -> dict:
    """Retrieve logged expenses for the current session.

    This tool retrieves expenses within a specified date range and optionally
    aggregates them to show net amounts per partner.

    Args:
        range: Date range filter. Options:
              - "all": No date filter
              - "YYYY-MM-DD": Single date
              - "YYYY-MM-DD to YYYY-MM-DD": Date range
        aggregate: If True, calculate net amounts per partner. If False,
                  return individual expense details.
        repository: The ExpenseRepository implementation to use. Expected to be
                   injected by the ADK runtime. If None, returns an error.

    Returns:
        dict: A dictionary with operation results:
            - Success: {"success": True, "expenses": [...]}
            - Error: {"success": False, "error": "..."}

    Examples:
        Get all expenses:
            >>> result = get_expenses("all", repository=adapter)
            >>> result
            {"success": True, "expenses": [...]}

        Get expenses for a date:
            >>> result = get_expenses("2025-01-15", repository=adapter)
            >>> result
            {"success": True, "expenses": [...]}
    """
    # Validate repository is provided
    if repository is None:
        return {
            "success": False,
            "error": "Repository not provided. Please try again later.",
        }

    return _handle_get_expenses(range, aggregate, repository)


def _handle_log_expense(
    amount: float,
    currency: str,
    description: str,
    paid_by: str | None,
    repository: ExpenseRepository,
) -> dict:
    """Handle the log_expense operation.

    Args:
        amount: The expense amount.
        currency: Currency code.
        description: Brief description.
        paid_by: Partner who paid or None.
        repository: The ExpenseRepository implementation.

    Returns:
        dict: Success or error response.
    """
    try:
        # Validate amount is positive
        if amount <= 0:
            return {
                "success": False,
                "error": "Amount must be positive.",
            }

        # Validate currency format
        if not _is_valid_currency(currency):
            return {
                "success": False,
                "error": "Currency must be 3 uppercase letters (e.g., USD, EUR, JPY).",
            }

        # Determine who paid
        payer_partner = None
        if paid_by is None:
            # Get first partner as default
            partners_list = repository.list_partners()
            if not partners_list:
                return {
                    "success": False,
                    "error": "No partners in session. Please add a partner first.",
                }
            payer_partner = partners_list[0]
        else:
            # Find partner by name
            partners_list = repository.list_partners()
            matching_partners = [p for p in partners_list if p.name == paid_by]
            if not matching_partners:
                return {
                    "success": False,
                    "error": f"Partner '{paid_by}' not found.",
                }
            payer_partner = matching_partners[0]

        # Create expense entity with today's date
        expense = Expense(
            date=datetime.date.today(),
            amount=amount,
            currency=currency,
            description=description,
            paid_by=payer_partner,
        )

        # Log the expense
        expense_id = repository.log_expense(expense, payer_partner)

        return {
            "success": True,
            "message": f"Expense logged: {amount} {currency} for '{description}' paid by {payer_partner.name}.",
            "expense_id": expense_id,
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


def _handle_split_expense(
    expense_id: str,
    partners: list[str],
    ratios: list[float] | None,
    repository: ExpenseRepository,
) -> dict:
    """Handle the split_expense operation.

    Args:
        expense_id: The expense ID.
        partners: List of partner names.
        ratios: Optional split ratios.
        repository: The ExpenseRepository implementation.

    Returns:
        dict: Success or error response.
    """
    try:
        # Validate expense exists
        expense = repository.get_expense_by_id(expense_id)
        if expense is None:
            return {
                "success": False,
                "error": f"Expense '{expense_id}' not found.",
            }

        # Validate partners list is not empty
        if not partners:
            return {
                "success": False,
                "error": "Partner list cannot be empty.",
            }

        # Validate ratios if provided
        if ratios is not None:
            if len(ratios) != len(partners):
                return {
                    "success": False,
                    "error": f"Ratios length ({len(ratios)}) must match partners length ({len(partners)}).",
                }

            # Check ratios sum to approximately 1.0 (allow 0.0001 tolerance)
            ratio_sum = sum(ratios)
            if abs(ratio_sum - 1.0) > 0.0001:
                return {
                    "success": False,
                    "error": f"Ratios must sum to 1.0 (100%), got {ratio_sum:.4f}.",
                }

        # Validate all partner names exist and convert to Partner entities
        all_partners = repository.list_partners()
        partner_entities = []
        for partner_name in partners:
            matching_partners = [p for p in all_partners if p.name == partner_name]
            if not matching_partners:
                return {
                    "success": False,
                    "error": f"Partner '{partner_name}' not found.",
                }
            partner_entities.append(matching_partners[0])

        # Split the expense
        repository.split_expense(expense_id, partner_entities, ratios)

        return {
            "success": True,
            "message": f"Expense split among {len(partners)} partners.",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


def _handle_get_expenses(
    range_str: str, aggregate: bool, repository: ExpenseRepository
) -> dict:
    """Handle the get_expenses operation.

    Args:
        range_str: Date range specification.
        aggregate: Whether to aggregate expenses.
        repository: The ExpenseRepository implementation.

    Returns:
        dict: Success response with expenses or error response.
    """
    try:
        # Parse date range
        date_from, date_to = _parse_date_range(range_str)

        # Retrieve expenses and splits
        expenses = repository.get_expenses(date_from, date_to)
        splits = repository.get_splits(date_from, date_to)

        # Format expenses
        if aggregate:
            # Calculate total expense per partner
            expense_data = _aggregate_expenses(expenses, splits)
        else:
            # Return individual expense items showing each partner's share
            expense_data = _format_individual_shares(expenses, splits)

        return {
            "success": True,
            "expenses": expense_data,
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


def _is_valid_currency(currency: str) -> bool:
    """Check if currency code is valid format.

    Args:
        currency: Currency code to validate.

    Returns:
        True if valid (3 uppercase letters), False otherwise.
    """
    return len(currency) == 3 and currency.isupper() and currency.isalpha()


def _parse_date_range(
    range_str: str,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse date range string into from/to dates.

    Args:
        range_str: Range specification ("all", "YYYY-MM-DD", or "YYYY-MM-DD to YYYY-MM-DD").

    Returns:
        Tuple of (date_from, date_to). None values mean no limit.

    Raises:
        ValueError: If date format is invalid.
    """
    if range_str == "all":
        return None, None

    if " to " in range_str:
        # Date range
        parts = range_str.split(" to ")
        if len(parts) != 2:
            raise ValueError(f"Invalid date range format: '{range_str}'")

        date_from = datetime.date.fromisoformat(parts[0].strip())
        date_to = datetime.date.fromisoformat(parts[1].strip())

        if date_from > date_to:
            raise ValueError(
                f"Start date must be before or equal to end date: {range_str}"
            )

        return date_from, date_to

    # Single date
    single_date = datetime.date.fromisoformat(range_str)
    return single_date, single_date


def _aggregate_expenses(
    expenses: list[Expense], splits: dict[str, dict[str, any]]
) -> list[dict]:
    """Aggregate expenses to calculate total expense per partner.

    Args:
        expenses: List of Expense entities.
        splits: Dictionary mapping expense_id to partner net settlements.
                Positive = receives from others (payer), Negative = owes to payer

    Returns:
        List of dicts with partner names and their total expense amounts.
        Format: [{"partner": "Alice", "total_expense": 85.00, "currency": "USD"}, ...]
    """
    partner_totals: dict[str, dict] = {}

    for expense in expenses:
        # Get split information for this expense
        expense_splits = splits.get(expense.id, {})

        # If no split exists, the entire expense is the payer's
        if not expense_splits:
            partner_name = expense.paid_by.name
            if partner_name not in partner_totals:
                partner_totals[partner_name] = {
                    "partner": partner_name,
                    "total_expense": 0.0,
                    "currency": expense.currency,
                }
            partner_totals[partner_name]["total_expense"] += float(expense.amount)
        else:
            # Calculate each partner's share from net settlements
            for partner_name, net_settlement in expense_splits.items():
                if partner_name not in partner_totals:
                    partner_totals[partner_name] = {
                        "partner": partner_name,
                        "total_expense": 0.0,
                        "currency": expense.currency,
                    }

                # Calculate share:
                # - If payer (positive settlement): share = amount_paid - settlement_received
                # - If non-payer (negative settlement): share = abs(settlement_owed)
                if partner_name == expense.paid_by.name:
                    # Payer: share = what they paid - what they receive back
                    share = float(expense.amount) - float(net_settlement)
                else:
                    # Non-payer: share = what they owe (absolute value)
                    share = abs(float(net_settlement))

                partner_totals[partner_name]["total_expense"] += share

    return list(partner_totals.values())


def _format_individual_shares(
    expenses: list[Expense], splits: dict[str, dict[str, any]]
) -> list[dict]:
    """Format expenses as individual items showing each partner's share.

    Args:
        expenses: List of Expense entities.
        splits: Dictionary mapping expense_id to partner net settlements.
                Positive = receives from others (payer), Negative = owes to payer

    Returns:
        List of dicts with individual expense shares per partner.
        Format: [{"description": "Hotel Stay", "shared_by": "Alice", "amount": 50.00}, ...]
    """
    result = []

    for expense in expenses:
        # Get split information for this expense
        expense_splits = splits.get(expense.id, {})

        # If no split exists, the expense belongs entirely to the payer
        if not expense_splits:
            result.append(
                {
                    "description": expense.description,
                    "shared_by": expense.paid_by.name,
                    "amount": float(expense.amount),
                }
            )
        else:
            # Create an entry for each partner showing their share
            for partner_name, net_settlement in expense_splits.items():
                # Calculate share:
                # - If payer (positive settlement): share = amount_paid - settlement_received
                # - If non-payer (negative settlement): share = abs(settlement_owed)
                if partner_name == expense.paid_by.name:
                    share = float(expense.amount) - float(net_settlement)
                else:
                    share = abs(float(net_settlement))

                result.append(
                    {
                        "description": expense.description,
                        "shared_by": partner_name,
                        "amount": share,
                    }
                )

    return result
