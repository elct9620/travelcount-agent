"""Entities package for TravelCount application.

This package contains domain entities that represent core business concepts
in the TravelCount expense tracking system. All entities follow Clean Architecture
principles and are independent from storage and framework layers.
"""

from entities.partner import Partner

__all__ = ["Partner"]
