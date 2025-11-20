"""TravelCount agent configuration."""

from typing import Optional

from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext

from .tools.partner import partners as partners_tool
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


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for managing travel expenses with friends.",
    instruction=(
        "You help users track and manage travel expenses by session. "
        "You can manage travel partners who participate in shared expenses. "
        "Be friendly, concise, and helpful."
    ),
    tools=[partners],
)
