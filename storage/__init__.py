"""Storage module for TravelCount application.

This package contains adapters for persisting expense tracking data.
It follows Clean Architecture principles with dependency inversion - storage
adapters implement protocol interfaces defined by their consumers (tools).
"""

from storage.beancount_adapter import BeancountAdapter
from storage.session_manager import SessionManager

__all__ = ["BeancountAdapter", "SessionManager"]
