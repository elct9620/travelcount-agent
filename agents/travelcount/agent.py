"""TravelCount agent configuration."""

from typing import Optional

from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext

from .tools.partner import partners as partners_tool
from .tools.expense import log_expense as log_expense_tool
from .tools.expense import split_expense as split_expense_tool
from .tools.expense import get_expenses as get_expenses_tool
from .storage.beancount_adapter import BeancountAdapter
from .storage.session_manager import SessionManager


def partners(
    operation: str,
    name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Manage travel partners in a TravelCount session.

    This wrapper injects the session-specific repository based on ADK context.

    Args:
        operation: The operation to perform ("add", "remove", or "list")
        name: The name of the partner (required for add/remove)
        tool_context: ADK tool context (automatically injected)

    Returns:
        dict: Result with success status and message/error
    """
    # Get session ID from tool_context
    if not tool_context or not tool_context.session:
        return {
            "success": False,
            "error": "Session context is not available. Please try again.",
        }

    session_id = tool_context.session.id

    # Create session-specific adapter
    session_manager = SessionManager(session_id)
    adapter = BeancountAdapter(session_manager)

    # Call the original tool with the injected repository
    return partners_tool(
        operation=operation,
        name=name,
        repository=adapter,
    )


def log_expense(
    amount: float,
    currency: str,
    description: str,
    paid_by: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Log a travel expense for the current session.

    This wrapper injects the session-specific repository based on ADK context.

    Args:
        amount: The expense amount (must be positive)
        currency: Currency code (e.g., "USD", "EUR")
        description: Brief description of the expense
        paid_by: Name of the partner who paid (defaults to first partner)
        tool_context: ADK tool context (automatically injected)

    Returns:
        dict: Result with success status, message/error, and expense_id
    """
    # Get session ID from tool_context
    if not tool_context or not tool_context.session:
        return {
            "success": False,
            "error": "Session context is not available. Please try again.",
        }

    session_id = tool_context.session.id

    # Create session-specific adapter
    session_manager = SessionManager(session_id)
    adapter = BeancountAdapter(session_manager)

    # Call the original tool with the injected repository
    return log_expense_tool(
        amount=amount,
        currency=currency,
        description=description,
        paid_by=paid_by,
        repository=adapter,
    )


def split_expense(
    expense_id: str,
    partners: list[str],
    ratios: Optional[list[float]] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Split an expense among travel partners.

    This wrapper injects the session-specific repository based on ADK context.

    Args:
        expense_id: ID of the expense to split
        partners: List of partner names to split among
        ratios: Optional list of ratios (must sum to 1.0), defaults to equal split
        tool_context: ADK tool context (automatically injected)

    Returns:
        dict: Result with success status and message/error
    """
    # Get session ID from tool_context
    if not tool_context or not tool_context.session:
        return {
            "success": False,
            "error": "Session context is not available. Please try again.",
        }

    session_id = tool_context.session.id

    # Create session-specific adapter
    session_manager = SessionManager(session_id)
    adapter = BeancountAdapter(session_manager)

    # Call the original tool with the injected repository
    return split_expense_tool(
        expense_id=expense_id,
        partners=partners,
        ratios=ratios,
        repository=adapter,
    )


def get_expenses(
    range: str = "all",
    aggregate: bool = True,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """
    Retrieve logged expenses for the current session.

    This wrapper injects the session-specific repository based on ADK context.

    Args:
        range: Date range filter ("all", "YYYY-MM-DD", or "YYYY-MM-DD to YYYY-MM-DD")
        aggregate: Whether to aggregate expenses by partner
        tool_context: ADK tool context (automatically injected)

    Returns:
        dict: Result with success status and expenses list
    """
    # Get session ID from tool_context
    if not tool_context or not tool_context.session:
        return {
            "success": False,
            "error": "Session context is not available. Please try again.",
        }

    session_id = tool_context.session.id

    # Create session-specific adapter
    session_manager = SessionManager(session_id)
    adapter = BeancountAdapter(session_manager)

    # Call the original tool with the injected repository
    return get_expenses_tool(
        range=range,
        aggregate=aggregate,
        repository=adapter,
    )


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for managing travel expenses with friends.",
    instruction=(
        "You help users track and manage travel expenses by session. "
        "You can manage travel partners who participate in shared expenses, "
        "log individual expenses, split expenses among partners, and retrieve "
        "expense records. Be friendly, concise, and helpful."
    ),
    tools=[partners, log_expense, split_expense, get_expenses],
)
